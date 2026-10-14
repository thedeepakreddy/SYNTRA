"""Pydantic schemas for the SYNTRA REST and WebSocket API."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
from syntra.core.config import AutonomyMode


class CreateSessionRequest(BaseModel):
    """Request payload to create a new engineering session."""
    objective: str = Field(..., description="Software engineering objective or task description")
    autonomy_mode: AutonomyMode = Field(default=AutonomyMode.SEMI_AUTONOMOUS, description="Target autonomy level")
    workspace_dir: str | None = Field(default=None, description="Optional custom workspace directory")


class SessionResponse(BaseModel):
    """Session representation returned to clients."""
    session_id: str
    objective: str
    status: str
    autonomy_mode: str
    created_at: str


class RunTaskRequest(BaseModel):
    """Request payload to initiate autonomous swarm execution."""
    objective: str | None = Field(default=None, description="Optional objective override")
    max_iterations: int = Field(default=3, description="Maximum self-healing review cycles")
    autonomy_mode: AutonomyMode | None = Field(default=None, description="Autonomy mode override")


class CheckpointResponse(BaseModel):
    """Checkpoint details model."""
    checkpoint_id: str
    session_id: str
    agent_id: str
    agent_role: str
    action_type: str
    risk_level: str
    description: str
    status: str
    proposed_diff: str | None = None
    proposed_command: str | None = None
    target_path: str | None = None
    human_feedback: str | None = None
    created_at: str


class CheckpointResolveRequest(BaseModel):
    """Payload to approve, reject, or modify a checkpoint."""
    decision: str = Field(..., description="'approve', 'reject', or 'modify'")
    feedback: str | None = Field(default=None, description="Mandatory when decision is 'reject'")
    modified_payload: dict[str, Any] | None = Field(default=None, description="Optional modified data when decision is 'modify'")


class WorkspaceFileResponse(BaseModel):
    """File content representation."""
    path: str
    content: str
    size_bytes: int


class SystemHealthResponse(BaseModel):
    """System health and telemetry status."""
    status: str = "healthy"
    version: str = "0.1.0"
    gemini_configured: bool
    autonomy_mode: str
    telemetry: dict[str, Any]


class ComponentHealth(BaseModel):
    """Health status of an individual infrastructure component."""
    status: str
    latency_ms: float | None = None
    details: str | None = None


class SystemReadinessResponse(BaseModel):
    """Comprehensive readiness probe for all backend subsystems."""
    status: str
    version: str = "0.1.0"
    timestamp: str
    components: dict[str, ComponentHealth]
