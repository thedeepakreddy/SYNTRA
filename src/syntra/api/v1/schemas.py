"""Pydantic v2 schemas for SYNTRA Control Plane API v1."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from syntra.core.config import AutonomyMode
from syntra.domain.entities import (
    ApprovalActionType,
    ApprovalDecision,
    ArtifactType,
    MissionState,
    TaskState,
)

T = TypeVar("T")


class CursorPage(BaseModel, Generic[T]):
    """Cursor-paginated container for collection endpoints."""

    items: list[T]
    next_cursor: str | None = None
    has_more: bool = False
    limit: int = 50


# =====================================================================
# Projects
# =====================================================================


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = Field(None, max_length=500)
    default_branch: str = "main"


class ProjectResponse(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    slug: str
    description: str | None = None
    default_branch: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =====================================================================
# Missions & Budgets
# =====================================================================


class CreateMissionRequest(BaseModel):
    project_id: UUID
    title: str | None = Field(default=None, max_length=200)
    objective: str = Field(..., min_length=1, max_length=5000)
    autonomy_mode: AutonomyMode = AutonomyMode.SEMI_AUTONOMOUS
    budget_max_cost_usd: Decimal = Field(default=Decimal("100.00"), ge=Decimal("0.00"))
    budget_max_tokens: int = Field(default=1_000_000, ge=1)
    max_concurrency: int = Field(default=4, ge=1, le=16)
    max_task_attempts: int = Field(default=3, ge=1, le=10)
    max_duration_seconds: int = Field(default=86400, ge=60)

    @field_validator("title", mode="before")
    @classmethod
    def clean_title(cls, v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            cleaned = v.strip()
            return cleaned if cleaned else None
        return str(v)


class MissionResponse(BaseModel):
    id: UUID
    org_id: UUID
    project_id: UUID
    title: str | None = None
    objective: str
    state: MissionState
    autonomy_mode: AutonomyMode
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetResponse(BaseModel):
    id: UUID
    mission_id: UUID
    max_tokens: int
    consumed_tokens: int
    reserved_tokens: int
    max_cost_usd: Decimal
    consumed_cost_usd: Decimal
    reserved_cost_usd: Decimal
    max_concurrency: int
    max_task_attempts: int
    max_mission_duration_seconds: int

    model_config = ConfigDict(from_attributes=True)


class PlanningCapabilityResponse(BaseModel):
    """Response returned when planning agent execution is requested before Phase 4."""

    status: str = "CAPABILITY_SCHEDULED"
    capability: str = "autonomous_planning_agent_dag"
    phase: str = "PHASE_3_API_CONTROL_PLANE"
    target_phase: str = "PHASE_4_AGENT_EXECUTION_FABRIC"
    message: str = (
        "Mission plan request accepted and validated. Autonomous agent execution "
        "(Product Manager, Software Architect, Engineering Manager DAG synthesis) "
        "is scheduled for Phase 4. The API schema and control boundary are active."
    )
    mission_id: UUID
    project_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# =====================================================================
# Tasks
# =====================================================================


class TaskResponse(BaseModel):
    id: UUID
    plan_id: UUID
    title: str
    description: str
    assigned_role: str
    priority: int = 0
    state: TaskState
    dependencies: list[UUID] = Field(default_factory=list)
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlanResponse(BaseModel):
    id: UUID
    mission_id: UUID
    status: str
    version: int
    tasks: list[TaskResponse] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =====================================================================
# Approvals
# =====================================================================


class ApprovalResponse(BaseModel):
    id: UUID
    mission_id: UUID
    org_id: UUID
    action_type: ApprovalActionType
    target_resource: str
    mission_version: int
    decision: ApprovalDecision
    action_digest: str
    expires_at: datetime
    resolved_at: datetime | None = None
    resolved_by: UUID | None = None
    reason: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApprovalDecisionRequest(BaseModel):
    decision: ApprovalDecision
    action_digest: str = Field(..., description="Canonical HMAC-SHA256 digest proving approval of unmodified state")
    reason: str | None = Field(None, max_length=1000)


# =====================================================================
# Events & Artifacts & Usage
# =====================================================================


class EventResponse(BaseModel):
    id: UUID
    mission_id: UUID | None = None
    event_type: str
    payload: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArtifactResponse(BaseModel):
    id: UUID
    mission_id: UUID
    artifact_type: ArtifactType
    path: str
    content_hash: str
    size_bytes: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UsageRecordResponse(BaseModel):
    id: UUID
    mission_id: UUID
    model_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MissionUsageSummaryResponse(BaseModel):
    mission_id: UUID
    total_tokens: int
    total_cost_usd: Decimal
    records: list[UsageRecordResponse] = Field(default_factory=list)
