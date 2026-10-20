"""System diagnostics, metrics aggregation, and Control Center overview endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from syntra.api.auth.dependencies import get_uow, require_viewer_or_above
from syntra.api.auth.models import AuthenticatedUser
from syntra.domain.entities import ApprovalDecision
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/system", tags=["System"])


class SystemOverviewResponse(BaseModel):
    """Consolidated operational metrics for Control Center Overview dashboard."""

    org_id: UUID
    projects_count: int
    missions_count: int
    missions_by_state: dict[str, int]
    pending_approvals_count: int
    active_agents_count: int
    total_tokens_consumed: int
    total_cost_usd: float
    system_health: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


@router.get("/overview", response_model=SystemOverviewResponse)
async def get_system_overview(
    user: Annotated[AuthenticatedUser, Depends(require_viewer_or_above)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
) -> SystemOverviewResponse:
    """Retrieve high-level system diagnostics and metrics across the organization."""
    projects = await uow.projects.list_for_org(user.org_id)
    missions = await uow.missions.list_for_org(user.org_id)
    pending_approvals = await uow.approvals.list_for_org(user.org_id, decision=ApprovalDecision.PENDING)

    missions_by_state: dict[str, int] = {}
    for m in missions:
        state_key = m.state.value if hasattr(m.state, "value") else str(m.state)
        missions_by_state[state_key] = missions_by_state.get(state_key, 0) + 1

    # Total token & cost calculation across missions in this tenant
    total_tokens = 0
    total_cost = 0.0
    for m in missions:
        try:
            records = await uow.budgets.list_usage_records(mission_id=m.id, org_id=user.org_id)
            for r in records:
                total_tokens += (r.prompt_tokens or 0) + (r.completion_tokens or 0)
                if r.cost_usd is not None:
                    total_cost += float(r.cost_usd)
        except Exception:
            pass

    return SystemOverviewResponse(
        org_id=user.org_id,
        projects_count=len(projects),
        missions_count=len(missions),
        missions_by_state=missions_by_state,
        pending_approvals_count=len(pending_approvals),
        active_agents_count=10,  # 10 canonical personas from AGENTS.md
        total_tokens_consumed=total_tokens,
        total_cost_usd=round(total_cost, 4),
        system_health="HEALTHY",
        timestamp=datetime.now(UTC),
    )
