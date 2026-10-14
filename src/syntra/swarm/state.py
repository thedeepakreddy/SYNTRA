"""Swarm shared blackboard state and execution status."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from pydantic import BaseModel, Field


from syntra.core.config import AutonomyMode


class SwarmTask(BaseModel):
    """An individual engineering task within the swarm plan."""
    id: str
    title: str
    description: str
    assigned_role: str
    dependencies: list[str] = Field(default_factory=list)
    status: str = "pending"  # pending, in_progress, completed, failed
    result: str | None = None


class SwarmState(BaseModel):
    """The central state / blackboard across all agents in a swarm run."""

    session_id: str
    objective: str
    autonomy_mode: AutonomyMode = AutonomyMode.SEMI_AUTONOMOUS
    current_node: str = "start"
    stage: str = "init"
    iteration: int = 0
    max_iterations: int = 5

    # Core artifacts produced across agent pipeline
    architecture_design: str | None = None
    tasks: list[SwarmTask] = Field(default_factory=list)
    current_task_id: str | None = None
    implemented_files: list[str] = Field(default_factory=list)
    test_results: dict[str, Any] = Field(default_factory=dict)
    review_approved: bool = False
    review_comments: list[str] = Field(default_factory=list)
    security_passed: bool = True
    security_findings: list[dict[str, Any]] = Field(default_factory=list)

    # General blackboard for arbitrary agent scratch data
    blackboard: dict[str, Any] = Field(default_factory=dict)

    is_completed: bool = False
    error: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def update_stage(self, new_stage: str, node: str) -> None:
        """Advance swarm lifecycle stage."""
        self.stage = new_stage
        self.current_node = node
        self.updated_at = datetime.now(UTC)
