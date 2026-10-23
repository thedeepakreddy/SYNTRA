"""Project management endpoints for SYNTRA Control Plane."""

import hashlib
import json
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Response, status
from fastapi.responses import JSONResponse

from syntra.api.auth.dependencies import (
    get_uow,
    require_developer_or_above,
    require_viewer_or_above,
)
from syntra.api.auth.models import AuthenticatedUser
from syntra.api.v1.schemas import CreateProjectRequest, MissionResponse, ProjectResponse
from syntra.core.config import AutonomyMode
from syntra.domain.entities import MissionState, TaskState
from syntra.domain.exceptions import DuplicateIdempotencyKeyError
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/projects", tags=["Projects"])


def _hash_payload(data: dict[str, Any]) -> str:
    serialized = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    req: CreateProjectRequest,
    user: Annotated[AuthenticatedUser, Depends(require_developer_or_above)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Response:
    """Register a new software engineering project under caller's tenant."""
    payload_dict = req.model_dump()
    req_hash = _hash_payload(payload_dict)

    if idempotency_key:
        cached = await uow.idempotency.get(idempotency_key, user.org_id)
        if cached:
            if cached.payload_hash and cached.payload_hash != req_hash:
                raise DuplicateIdempotencyKeyError(
                    f"Idempotency key '{idempotency_key}' already used with different payload."
                )
            return JSONResponse(status_code=cached.response_code, content=cached.response_body)

    project_id = uuid4()
    slug = req.slug or req.name.lower().replace(" ", "-")[:50]

    project = await uow.projects.create(
        project_id=project_id,
        org_id=user.org_id,
        name=req.name,
        slug=slug,
        description=req.description,
    )

    resp_data = ProjectResponse(
        id=project.id,
        org_id=project.org_id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        default_branch=req.default_branch,
        created_at=project.created_at,
        updated_at=project.updated_at,
    ).model_dump(mode="json")

    if idempotency_key:
        await uow.idempotency.record(
            key=idempotency_key,
            org_id=user.org_id,
            response_code=status.HTTP_201_CREATED,
            response_body=resp_data,
            payload_hash=req_hash,
        )

    await uow.commit()
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=resp_data)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_viewer_or_above)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
) -> ProjectResponse:
    """Retrieve project metadata for tenant."""
    project = await uow.projects.get_by_id_for_org(project_id, user.org_id)
    return ProjectResponse(
        id=project.id,
        org_id=project.org_id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        default_branch="main",
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    user: Annotated[AuthenticatedUser, Depends(require_viewer_or_above)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    limit: int = 50,
) -> list[ProjectResponse]:
    """List all projects belonging to the caller's organization."""
    projects = await uow.projects.list_for_org(user.org_id, limit=limit)
    return [
        ProjectResponse(
            id=p.id,
            org_id=p.org_id,
            name=p.name,
            slug=p.slug,
            description=p.description,
            default_branch="main",
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in projects
    ]


@router.post("/{project_id}/rebuild", response_model=MissionResponse)
async def rebuild_project(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    user: Annotated[AuthenticatedUser, Depends(require_developer_or_above)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
) -> MissionResponse:
    """Purge build cache and rebuild the project's engineering deliverables."""
    import logging
    import shutil
    from pathlib import Path

    from syntra.agents.fullstack_generator import (
        generate_backend_package,
        generate_marvelous_frontend_spa,
    )
    from syntra.api.v1.routes.missions import _execute_mission_stages

    logger = logging.getLogger(__name__)
    project = await uow.projects.get_by_id_for_org(project_id, user.org_id)
    missions = await uow.missions.list_for_org(user.org_id, project_id=project_id, limit=5)

    if missions:
        target_mission = missions[0]
    else:
        target_mission = await uow.missions.create(
            mission_id=uuid4(),
            org_id=user.org_id,
            project_id=project_id,
            objective=f"Build and verify complete production fullstack solution for {project.name}",
            autonomy_mode=AutonomyMode.SEMI_AUTONOMOUS.value,
        )

    # 1. Purge on-disk build cache for this mission
    app_dir = Path("frontend/public/generated_apps") / str(target_mission.id)
    if app_dir.exists():
        try:
            shutil.rmtree(app_dir, ignore_errors=True)
        except Exception as e:
            logger.warning("Could not purge app directory %s: %s", app_dir, e)

    # 2. Reset tasks to PENDING
    plan = await uow.tasks.get_plan_for_mission(target_mission.id, user.org_id)
    if plan:
        existing_tasks, _, _ = await uow.tasks.list_for_mission(target_mission.id, user.org_id, limit=100)
        for t in existing_tasks:
            t.state = TaskState.PENDING
            t.attempt_count = 0

    # 3. Transition mission to RUNNING
    updated = await uow.missions.update_state(target_mission.id, user.org_id, MissionState.RUNNING)

    # 4. Synthesize fresh backend & frontend immediately
    try:
        app_dir.mkdir(parents=True, exist_ok=True)
        backend_dir = app_dir / "backend"
        backend_dir.mkdir(parents=True, exist_ok=True)

        backend_files = generate_backend_package(target_mission.objective, [])
        for fname, fcontent in backend_files.items():
            (backend_dir / fname).write_text(fcontent, encoding="utf-8")

        fresh_html = generate_marvelous_frontend_spa(target_mission.objective, [])
        (app_dir / "index.html").write_text(fresh_html, encoding="utf-8")

        latest_dir = Path("frontend/public/generated_apps/latest")
        latest_dir.mkdir(parents=True, exist_ok=True)
        (latest_dir / "index.html").write_text(fresh_html, encoding="utf-8")
        latest_backend = latest_dir / "backend"
        latest_backend.mkdir(parents=True, exist_ok=True)
        for fname, fcontent in backend_files.items():
            (latest_backend / fname).write_text(fcontent, encoding="utf-8")
    except Exception as synth_err:
        logger.warning("Immediate synthesis during project rebuild encountered error: %s", synth_err)

    # 5. Record event & enqueue background execution
    await uow.outbox.record_event(
        org_id=user.org_id,
        event_type="project.rebuilt",
        payload={
            "project_id": str(project_id),
            "mission_id": str(target_mission.id),
            "project_name": project.name,
        },
        mission_id=target_mission.id,
    )
    await uow.commit()

    background_tasks.add_task(_execute_mission_stages, target_mission.id, user.org_id)

    return MissionResponse(
        id=updated.id,
        org_id=updated.org_id,
        project_id=updated.project_id,
        title=None,
        objective=updated.objective,
        state=updated.state,
        autonomy_mode=AutonomyMode(updated.autonomy_mode),
        version=updated.version,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )
