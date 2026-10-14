"""Task inspection endpoints for SYNTRA Control Plane."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from syntra.api.auth.dependencies import get_uow, require_viewer_or_above
from syntra.api.auth.models import AuthenticatedUser
from syntra.api.v1.schemas import TaskResponse
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_viewer_or_above)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
) -> TaskResponse:
    """Retrieve individual task details, state, and dependencies."""
    task = await uow.tasks.get_by_id_for_org(task_id, user.org_id)
    dependencies = await uow.tasks.get_dependencies_for_task(task_id)

    return TaskResponse(
        id=task.id,
        plan_id=task.task_plan_id,
        title=task.title,
        description=task.description,
        assigned_role=task.assigned_role,
        priority=task.priority,
        state=task.state,
        dependencies=dependencies,
        version=task.version,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
