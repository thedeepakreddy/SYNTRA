"""Mission management, planning stubs, tasks, events, artifacts, and usage ledger endpoints."""

import hashlib
import json
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse

from syntra.api.auth.dependencies import (
    get_uow,
    require_developer_or_above,
    require_viewer_or_above,
)
from syntra.api.auth.models import AuthenticatedUser
from syntra.api.v1.schemas import (
    ArtifactResponse,
    CreateMissionRequest,
    CursorPage,
    EventResponse,
    MissionResponse,
    MissionUsageSummaryResponse,
    PlanningCapabilityResponse,
    PlanResponse,
    TaskResponse,
    UsageRecordResponse,
)
from syntra.core.config import AutonomyMode
from syntra.domain.exceptions import DuplicateIdempotencyKeyError
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/missions", tags=["Missions"])


def _hash_payload(data: dict[str, Any]) -> str:
    serialized = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


@router.post("", response_model=MissionResponse, status_code=status.HTTP_201_CREATED)
async def create_mission(
    req: CreateMissionRequest,
    user: Annotated[AuthenticatedUser, Depends(require_developer_or_above)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Response:
    """Create a new mission with dedicated budget and resource governance."""
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

    # 1. Verify project exists in caller's tenant
    await uow.projects.get_by_id_for_org(req.project_id, user.org_id)

    mission_id = uuid4()
    mission = await uow.missions.create(
        mission_id=mission_id,
        org_id=user.org_id,
        project_id=req.project_id,
        objective=req.objective,
        autonomy_mode=req.autonomy_mode.value,
    )

    # 2. Initialize bound budget
    await uow.budgets.create(
        org_id=user.org_id,
        mission_id=mission_id,
        max_tokens=req.budget_max_tokens,
        max_cost_usd=req.budget_max_cost_usd,
        max_concurrency=req.max_concurrency,
        max_task_attempts=req.max_task_attempts,
        max_mission_duration_seconds=req.max_duration_seconds,
    )

    # 3. Publish outbox event
    uow.publish_event(
        event_type="mission.created",
        payload={
            "mission_id": str(mission.id),
            "org_id": str(mission.org_id),
            "project_id": str(mission.project_id),
            "autonomy_mode": mission.autonomy_mode,
        },
    )

    resp_data = MissionResponse(
        id=mission.id,
        org_id=mission.org_id,
        project_id=mission.project_id,
        title=req.title,
        objective=mission.objective,
        state=mission.state,
        autonomy_mode=AutonomyMode(mission.autonomy_mode),
        version=mission.version,
        created_at=mission.created_at,
        updated_at=mission.updated_at,
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


@router.get("/{mission_id}", response_model=MissionResponse)
async def get_mission(
    mission_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_viewer_or_above)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
) -> MissionResponse:
    """Fetch mission state and metadata."""
    mission = await uow.missions.get_by_id_for_org(mission_id, user.org_id)
    return MissionResponse(
        id=mission.id,
        org_id=mission.org_id,
        project_id=mission.project_id,
        title=None,
        objective=mission.objective,
        state=mission.state,
        autonomy_mode=AutonomyMode(mission.autonomy_mode),
        version=mission.version,
        created_at=mission.created_at,
        updated_at=mission.updated_at,
    )


@router.post(
    "/{mission_id}/plan", response_model=PlanningCapabilityResponse, status_code=status.HTTP_501_NOT_IMPLEMENTED
)
async def trigger_plan(
    mission_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_developer_or_above)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
) -> Response:
    """Trigger autonomous multi-agent planning. Returns typed capability response for Phase 3."""
    mission = await uow.missions.get_by_id_for_org(mission_id, user.org_id)
    resp = PlanningCapabilityResponse(
        mission_id=mission.id,
        project_id=mission.project_id,
    )
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=resp.model_dump(mode="json"),
    )


@router.get("/{mission_id}/plan", response_model=PlanResponse)
async def get_plan(
    mission_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_viewer_or_above)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
) -> PlanResponse:
    """Inspect the generated task plan and DAG tasks."""
    plan = await uow.tasks.get_plan_for_mission(mission_id, user.org_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No task plan found for mission {mission_id}.",
        )

    tasks_raw, _, _ = await uow.tasks.list_for_mission(mission_id, user.org_id, limit=200)
    tasks: list[TaskResponse] = []
    for t in tasks_raw:
        deps = await uow.tasks.get_dependencies_for_task(t.id)
        tasks.append(
            TaskResponse(
                id=t.id,
                plan_id=t.task_plan_id,
                title=t.title,
                description=t.description,
                assigned_role=t.assigned_role,
                priority=t.priority,
                state=t.state,
                dependencies=deps,
                version=t.version,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
        )

    return PlanResponse(
        id=plan.id,
        mission_id=plan.mission_id,
        status=plan.status.value if hasattr(plan.status, "value") else str(plan.status),
        version=plan.plan_version,
        tasks=tasks,
        created_at=plan.created_at,
    )


@router.get("/{mission_id}/tasks", response_model=CursorPage[TaskResponse])
async def list_mission_tasks(
    mission_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_viewer_or_above)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = None,
) -> CursorPage[TaskResponse]:
    """List tasks in the mission DAG with dependency links."""
    tasks_raw, next_cursor, has_more = await uow.tasks.list_for_mission(
        mission_id=mission_id,
        org_id=user.org_id,
        limit=limit,
        cursor=cursor,
    )

    items: list[TaskResponse] = []
    for t in tasks_raw:
        deps = await uow.tasks.get_dependencies_for_task(t.id)
        items.append(
            TaskResponse(
                id=t.id,
                plan_id=t.task_plan_id,
                title=t.title,
                description=t.description,
                assigned_role=t.assigned_role,
                priority=t.priority,
                state=t.state,
                dependencies=deps,
                version=t.version,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
        )

    return CursorPage[TaskResponse](
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
        limit=limit,
    )


@router.get("/{mission_id}/events", response_model=CursorPage[EventResponse])
async def list_mission_events(
    mission_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_viewer_or_above)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = None,
) -> CursorPage[EventResponse]:
    """Query audit and execution events for a mission with cursor pagination."""
    events_raw, next_cursor, has_more = await uow.outbox.list_events_for_mission(
        mission_id=mission_id,
        org_id=user.org_id,
        limit=limit,
        cursor=cursor,
    )

    items = [
        EventResponse(
            id=e.id,
            mission_id=e.mission_id,
            event_type=e.event_type,
            payload=e.payload,
            created_at=e.created_at,
        )
        for e in events_raw
    ]

    return CursorPage[EventResponse](
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
        limit=limit,
    )


@router.get("/{mission_id}/artifacts", response_model=CursorPage[ArtifactResponse])
async def list_mission_artifacts(
    mission_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_viewer_or_above)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = None,
) -> CursorPage[ArtifactResponse]:
    """List produced artifacts (diffs, reports, plans) for a mission."""
    rows, next_cursor, has_more = await uow.artifacts.list_for_mission(
        mission_id=mission_id,
        org_id=user.org_id,
        limit=limit,
        cursor=cursor,
    )

    items: list[ArtifactResponse] = []
    for art, ver in rows:
        items.append(
            ArtifactResponse(
                id=art.id,
                mission_id=art.mission_id,
                artifact_type=art.type,
                path=ver.storage_path if ver else f"/artifacts/{art.id}",
                content_hash=ver.sha256_checksum if ver else "",
                size_bytes=ver.size_bytes if ver else 0,
                created_at=art.created_at,
            )
        )

    return CursorPage[ArtifactResponse](
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
        limit=limit,
    )


@router.get("/{mission_id}/usage", response_model=MissionUsageSummaryResponse)
async def get_mission_usage(
    mission_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_viewer_or_above)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
) -> MissionUsageSummaryResponse:
    """Fetch token consumption and USD cost financial ledger for a mission."""
    # Verify mission access
    await uow.missions.get_by_id_for_org(mission_id, user.org_id)
    budget = await uow.budgets.get_for_mission(mission_id)
    records_raw = await uow.budgets.list_usage_records(mission_id, user.org_id)
    records_tokens = sum((r.prompt_tokens + r.completion_tokens for r in records_raw), 0)
    records_cost: Decimal = sum((r.cost_usd for r in records_raw), Decimal("0.0000"))

    total_tokens = budget.consumed_tokens if (budget and budget.consumed_tokens > 0) else records_tokens
    total_cost: Decimal = (
        budget.consumed_cost_usd if (budget and budget.consumed_cost_usd > Decimal("0.0000")) else records_cost
    )

    records = [
        UsageRecordResponse(
            id=r.id,
            mission_id=r.mission_id,
            model_name=r.model_name,
            input_tokens=r.prompt_tokens,
            output_tokens=r.completion_tokens,
            total_tokens=r.prompt_tokens + r.completion_tokens,
            cost_usd=r.cost_usd,
            created_at=r.created_at,
        )
        for r in records_raw
    ]

    return MissionUsageSummaryResponse(
        mission_id=mission_id,
        total_tokens=total_tokens,
        total_cost_usd=total_cost,
        records=records,
    )
