"""Pydantic v2 contracts and data models for task scheduling, dispatch, and reconciliation."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from syntra.domain.entities import AttemptState


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
    produced_artifact_ids: list[UUID] = Field(default_factory=list)
    actual_prompt_tokens: int = 0
    actual_completion_tokens: int = 0
    actual_cost_usd: Decimal = Field(default_factory=lambda: Decimal("0.000000"))
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
