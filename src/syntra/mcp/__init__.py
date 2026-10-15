"""Model Context Protocol (MCP) subsystem for SYNTRA."""

from syntra.mcp.adapters.tools import (
    ScopedFilesystemTools,
    ScopedGitTools,
    create_workspace_mcp_server,
    resolve_safe_path,
)
from syntra.mcp.client_manager import (
    MCPClientError,
    MCPClientManager,
    MCPConnectionError,
    MCPProtocolError,
    MCPTimeoutError,
)
from syntra.mcp.gateway import ToolGateway
from syntra.mcp.policy import (
    BudgetExceededError,
    CapabilityPolicyEngine,
    CrossTenantAccessError,
    ExpiredGrantError,
    HumanApprovalRequiredError,
    PolicyDecision,
    PolicyGrantRecord,
    PolicyViolationError,
    ScopeViolationError,
    UnauthorizedRoleError,
)
from syntra.mcp.registry import (
    MCPRegistry,
    MCPRegistryError,
    SchemaDriftError,
    ServerDisabledError,
    UnknownServerError,
    UnknownToolError,
)
from syntra.mcp.security import (
    MCPSecurityService,
    ProcessSecurityError,
    SecurityValidationError,
    SSRFViolationError,
)
from syntra.mcp.server import MCPServer
from syntra.mcp.syntra_server import create_syntra_mcp_server
from syntra.mcp.types import (
    ConnectionStatus,
    MCPAuditRecord,
    MCPConnection,
    MCPInvocationRequest,
    MCPInvocationResult,
    MCPServerDefinition,
    MCPServerVersion,
    MCPToolDefinition,
    MCPToolSchemaVersion,
)

__all__ = [
    "MCPServer",
    "MCPClientManager",
    "ToolGateway",
    "CapabilityPolicyEngine",
    "MCPRegistry",
    "MCPSecurityService",
    "create_syntra_mcp_server",
    "create_workspace_mcp_server",
    "ScopedFilesystemTools",
    "ScopedGitTools",
    "resolve_safe_path",
    "MCPServerDefinition",
    "MCPServerVersion",
    "MCPConnection",
    "MCPToolDefinition",
    "MCPToolSchemaVersion",
    "MCPInvocationRequest",
    "MCPInvocationResult",
    "MCPAuditRecord",
    "ConnectionStatus",
    "MCPClientError",
    "MCPConnectionError",
    "MCPTimeoutError",
    "MCPProtocolError",
    "PolicyViolationError",
    "UnauthorizedRoleError",
    "ExpiredGrantError",
    "ScopeViolationError",
    "HumanApprovalRequiredError",
    "CrossTenantAccessError",
    "BudgetExceededError",
    "PolicyGrantRecord",
    "PolicyDecision",
    "MCPRegistryError",
    "UnknownServerError",
    "ServerDisabledError",
    "UnknownToolError",
    "SchemaDriftError",
    "SecurityValidationError",
    "SSRFViolationError",
    "ProcessSecurityError",
]
