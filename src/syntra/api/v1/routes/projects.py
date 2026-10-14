"""Project management endpoints for SYNTRA Control Plane."""

import hashlib
import json
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Response, status
from fastapi.responses import JSONResponse

from syntra.api.auth.dependencies import (
    get_uow,
    require_developer_or_above,
    require_viewer_or_above,
)
from syntra.api.auth.models import AuthenticatedUser
from syntra.api.v1.schemas import CreateProjectRequest, ProjectResponse
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
