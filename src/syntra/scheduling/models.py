"""Pydantic v2 contracts and data models for task scheduling, dispatch, and reconciliation."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from syntra.domain.entities import AttemptState


class EngineeringTaskSpecification(BaseModel):
    """Exact engineering scope serialized into the existing authoritative task description."""

    model_config = ConfigDict(extra="forbid")
    phase10_task: bool = True
    objective: str = Field(min_length=5)
    acceptance_criteria: list[str] = Field(min_length=1)
    required_skills: list[str] = Field(min_length=1)
    required_capabilities: list[str] = Field(min_length=1)
    verification_commands: list[str] = Field(min_length=1, max_length=10)
    estimated_tokens: int = Field(default=100000, ge=8192, le=1000000)
    estimated_cost_usd: Decimal = Field(default=Decimal("0.25"), gt=0, le=10)
    security_sensitive: bool = True
    max_rework: int = Field(default=1, ge=0, le=3)


class TaskReadinessReport(BaseModel):
    """Evaluation result for whether a specific task is eligible for scheduling."""

    model_config = ConfigDict(frozen=True)

    task_id: UUID
    is_ready: bool
    missing_prerequisites: list[UUID] = Field(default_factory=list)
    missing_artifacts: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)


class TaskPriorityScore(BaseModel):
    """Deterministic multi-factor priority score for ordering eligible tasks."""

    model_config = ConfigDict(frozen=True)

    task_id: UUID
    explicit_priority: int = 0
    downstream_dependency_count: int = 0
    estimated_tokens: int = 0
    created_at: datetime
    identifier: str

    @property
    def sort_key(self) -> tuple[int, int, int, str]:
        """Descending sort key: highest priority, highest downstream count, lowest tokens, stable id."""
        return (
            self.explicit_priority,
            self.downstream_dependency_count,
            -self.estimated_tokens,
            self.identifier,
        )


class TaskDispatchPayload(BaseModel):
    """Payload serialized into transactional outbox and Redis Streams for worker consumption."""

    model_config = ConfigDict(frozen=True)

    dispatch_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    mission_id: UUID
    org_id: UUID
    attempt_number: int
    assigned_role: str
    fencing_token: int
    lease_expires_at: datetime
    specification: str
    plan_version: int = 1
    task_attempt_id: UUID | None = None
    required_capabilities: list[str] = Field(default_factory=list)
    requested_skills: list[str] = Field(default_factory=list)
    budget_reserved_tokens: int = 0
    budget_reserved_cost_usd: Decimal = Field(default_factory=lambda: Decimal("0.0000"))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TaskExecutionResult(BaseModel):
    """Authoritative result submitted by a worker for outcome resolution."""

    model_config = ConfigDict(frozen=True)

    task_id: UUID
    attempt_number: int
    worker_id: str
    fencing_token: int
    status: AttemptState
    exit_code: int = 0
    output_summary: str = ""
    unified_diff: str | None = None
    base_commit: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    produced_artifact_ids: list[UUID] = Field(default_factory=list)
    execution_evidence: list[dict[str, object]] = Field(default_factory=list)
    actual_prompt_tokens: int = 0
    actual_completion_tokens: int = 0
    actual_cost_usd: Decimal = Field(default_factory=lambda: Decimal("0.000000"))
    cost_classification: Literal["ESTIMATED_FROM_USAGE", "CONSERVATIVE_UNVERIFIED"] = "ESTIMATED_FROM_USAGE"
    error_message: str | None = None
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkerRegistration(BaseModel):
    """Worker presence and capability record."""

    model_config = ConfigDict(frozen=True)

    worker_id: str
    supported_roles: list[str] = Field(default_factory=list)
    concurrency_capacity: int = 1
    last_heartbeat_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReconciliationSummary(BaseModel):
    """Outcome report from a scheduler reconciliation sweep."""

    model_config = ConfigDict(frozen=True)

    swept_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expired_leases_count: int = 0
    recovered_attempts_count: int = 0
    abandoned_tasks_failed: int = 0
    outbox_events_relayed: int = 0
    blocked_dependents_count: int = 0
    details: list[str] = Field(default_factory=list)
