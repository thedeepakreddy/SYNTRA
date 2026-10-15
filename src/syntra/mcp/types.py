"""Strongly typed Pydantic v2 schemas and models for SYNTRA MCP Infrastructure."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from syntra.domain.entities import (
    ActionClassification,
    AuthPolicyType,
    MCPTransportType,
    TrustClassification,
    VerificationStatus,
)


class ConnectionStatus(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    FAILED = "FAILED"
    CLOSED = "CLOSED"


class MCPServerDefinition(BaseModel):
    """Configuration and registration definition for an approved MCP server."""

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., description="Unique canonical name of the MCP server")
    transport: MCPTransportType = Field(default=MCPTransportType.STDIO, description="Transport type")
    trust_classification: TrustClassification = Field(
        default=TrustClassification.LOCAL_TRUSTED, description="Trust boundary classification"
    )
    command_or_url: str = Field(..., description="Executable path/command or remote URL endpoint")
    args: list[str] = Field(default_factory=list, description="Subprocess arguments for stdio transport")
    env: dict[str, str] = Field(default_factory=dict, description="Scoped environment variables")
    auth_policy: AuthPolicyType = Field(default=AuthPolicyType.NONE, description="Authentication policy")
    auth_token: str | None = Field(default=None, description="Secret token or credential (redacted from agent)")
    allowed_capabilities: list[str] = Field(
        default_factory=list, description="Explicitly allowed tool patterns or skill groups"
    )
    is_enabled: bool = Field(default=True, description="Whether server is active in allowlist")
    version: str = Field(default="1.0.0", description="Server semantic version")
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.VERIFIED, description="Last verification status"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MCPServerVersion(BaseModel):
    """Metadata regarding a verified MCP server version and protocol capabilities."""

    id: UUID = Field(default_factory=uuid4)
    server_id: UUID
    version: str = "1.0.0"
    protocol_version: str = "2024-11-05"
    server_info: dict[str, Any] = Field(default_factory=dict)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MCPConnection(BaseModel):
    """Live or historical connection state to an MCP server."""

    connection_id: UUID = Field(default_factory=uuid4)
    server_name: str
    transport: MCPTransportType
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    last_connected_at: datetime | None = None
    last_error: str | None = None
    reconnect_attempts: int = 0


class MCPToolDefinition(BaseModel):
    """Discovered tool definition with Pydantic JSON schema."""

    name: str = Field(..., description="Canonical tool name, e.g. syntra.get_task")
    server_name: str = Field(..., description="Owning server identifier")
    description: str | None = Field(default=None, description="Human/LLM tool description")
    input_schema: dict[str, Any] = Field(default_factory=dict, description="JSON Schema for tool arguments")
    action_classification: ActionClassification = Field(
        default=ActionClassification.READ_ONLY, description="Capability classification"
    )


class MCPToolSchemaVersion(BaseModel):
    """Cryptographic schema snapshot pinning a tool definition against drift."""

    id: UUID = Field(default_factory=uuid4)
    server_name: str
    tool_name: str
    version: str = "1.0.0"
    description: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)
    schema_hash: str = Field(..., description="SHA-256 fingerprint of canonical input_schema JSON")
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MCPInvocationRequest(BaseModel):
    """Authoritative tool invocation request dispatched through the Tool Gateway."""

    invocation_id: UUID = Field(default_factory=uuid4)
    org_id: UUID
    user_id: UUID | None = None
    caller_role: str = Field(..., description="Engineering persona executing the call")
    mission_id: UUID | None = None
    task_id: UUID | None = None
    server_name: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    workspace_path: str | None = None
    approval_token: str | None = None
    approval_digest: str | None = None
    approval_id: UUID | None = None
    timeout_seconds: float = Field(default=30.0, ge=1.0, le=300.0)


class MCPInvocationResult(BaseModel):
    """Typed execution outcome and evidence returned by the Tool Gateway."""

    invocation_id: UUID
    status: Literal["SUCCESS", "ERROR", "BLOCKED_BY_POLICY", "TIMEOUT"]
    content: list[dict[str, Any]] = Field(default_factory=list)
    raw_output: str | None = None
    is_error: bool = False
    error_code: int | None = None
    error_message: str | None = None
    duration_ms: int = 0
    result_hash: str | None = None
    tokens_consumed: int = 0
    cost_usd: str = "0.0000"


class MCPAuditRecord(BaseModel):
    """Audit log payload staged to PostgreSQL/SQLite events for non-repudiation."""

    invocation_id: UUID
    org_id: UUID
    mission_id: UUID | None = None
    task_id: UUID | None = None
    server_name: str
    tool_name: str
    caller_role: str
    arguments_scrubbed: dict[str, Any]
    status: str
    error_message: str | None = None
    result_hash: str | None = None
    duration_ms: int
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
