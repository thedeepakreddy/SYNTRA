"""Data models and enums for Hybrid Autonomy checkpoints."""

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Risk severity associated with a proposed agent action."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CheckpointStatus(str, Enum):
    """Lifecycle status of a checkpoint."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    CANCELLED = "cancelled"


class CheckpointActionType(str, Enum):
    """Types of actions that may trigger a checkpoint."""
    FILE_WRITE = "file_write"
    FILE_PATCH = "file_patch"
    COMMAND_EXECUTION = "command_execution"
    ROLE_HANDOFF = "role_handoff"
    PLAN_APPROVAL = "plan_approval"
    GIT_PUSH = "git_push"


class Checkpoint(BaseModel):
    """A human-in-the-loop checkpoint gate."""

    checkpoint_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    agent_id: str
    agent_role: str
    action_type: CheckpointActionType
    description: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    status: CheckpointStatus = CheckpointStatus.PENDING

    # Contextual artifacts
    proposed_diff: str | None = None
    proposed_command: str | None = None
    target_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Resolution details
    human_feedback: str | None = None
    modified_payload: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None

    def approve(self, feedback: str | None = None) -> None:
        """Approve the pending checkpoint."""
        self.status = CheckpointStatus.APPROVED
        self.human_feedback = feedback
        self.resolved_at = datetime.now(UTC)

    def reject(self, feedback: str) -> None:
        """Reject the pending checkpoint with mandatory corrective guidance."""
        self.status = CheckpointStatus.REJECTED
        self.human_feedback = feedback
        self.resolved_at = datetime.now(UTC)

    def modify(self, modified_payload: dict[str, Any], feedback: str | None = None) -> None:
        """Approve with modifications."""
        self.status = CheckpointStatus.MODIFIED
        self.modified_payload = modified_payload
        self.human_feedback = feedback
        self.resolved_at = datetime.now(UTC)
