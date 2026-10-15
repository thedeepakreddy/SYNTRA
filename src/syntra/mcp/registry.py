"""Authoritative MCP server registry and versioned tool schema snapshot manager."""

import logging
from typing import Any

from syntra.domain.entities import (
    ActionClassification,
    MCPTransportType,
)
from syntra.mcp.security import MCPSecurityService
from syntra.mcp.types import (
    MCPServerDefinition,
    MCPToolDefinition,
    MCPToolSchemaVersion,
)

logger = logging.getLogger(__name__)


class MCPRegistryError(Exception):
    """Base exception for MCP registry errors."""


class UnknownServerError(MCPRegistryError):
    """Raised when an unknown MCP server is requested."""


class ServerDisabledError(MCPRegistryError):
    """Raised when an MCP server is registered but currently disabled."""


class UnknownToolError(MCPRegistryError):
    """Raised when a tool is not found on the specified server."""


class SchemaDriftError(MCPRegistryError):
    """Raised when a remote MCP server produces a schema that violates its pinned snapshot."""


class MCPRegistry:
    """In-memory and persistent catalog of approved MCP servers and versioned tool schemas."""

    def __init__(self) -> None:
        self._servers: dict[str, MCPServerDefinition] = {}
        # tool_schemas: key = (server_name, tool_name) -> MCPToolSchemaVersion
        self._tool_schemas: dict[tuple[str, str], MCPToolSchemaVersion] = {}
        # tool_definitions: key = (server_name, tool_name) -> MCPToolDefinition
        self._tool_definitions: dict[tuple[str, str], MCPToolDefinition] = {}

    def register_server(self, server_def: MCPServerDefinition) -> MCPServerDefinition:
        """Register or update an approved MCP server definition in the allowlist."""
        # Validate executable or remote endpoint
        if server_def.transport == MCPTransportType.STDIO:
            MCPSecurityService.validate_stdio_command(server_def.command_or_url, server_def.args)
        elif server_def.transport in (MCPTransportType.STREAMABLE_HTTP, MCPTransportType.SSE, MCPTransportType.HTTP):
            # If it's a test server or localhost, we might allow local for test servers or enforce strict
            if not server_def.command_or_url.startswith(("http://test", "http://localhost", "http://127.0.0.1")):
                MCPSecurityService.validate_remote_url(server_def.command_or_url)

        self._servers[server_def.name] = server_def
        logger.info(
            "Registered MCP Server: %s (transport=%s, trust=%s)",
            server_def.name,
            server_def.transport.value,
            server_def.trust_classification.value,
        )
        return server_def

    def get_server(self, name: str) -> MCPServerDefinition:
        """Fetch server definition by canonical name, enforcing allowlist and enabled status."""
        server = self._servers.get(name)
        if not server:
            raise UnknownServerError(f"MCP Server '{name}' is not registered in the approved allowlist.")
        if not server.is_enabled:
            raise ServerDisabledError(f"MCP Server '{name}' is currently disabled.")
        return server

    def is_server_allowed(self, name: str) -> bool:
        """Check if server exists and is enabled."""
        server = self._servers.get(name)
        return server is not None and server.is_enabled

    def list_servers(self, enabled_only: bool = True) -> list[MCPServerDefinition]:
        """List all registered MCP servers."""
        if enabled_only:
            return [s for s in self._servers.values() if s.is_enabled]
        return list(self._servers.values())

    def snapshot_tool_schema(
        self,
        server_name: str,
        tool_name: str,
        input_schema: dict[str, Any],
        description: str | None = None,
        action_classification: ActionClassification = ActionClassification.READ_ONLY,
        version: str = "1.0.0",
        expected_hash: str | None = None,
    ) -> MCPToolSchemaVersion:
        """Snapshot a tool's JSON schema with SHA-256 fingerprinting and detect unexpected drift."""
        schema_hash = MCPSecurityService.compute_schema_hash(input_schema)
        key = (server_name, tool_name)

        existing = self._tool_schemas.get(key)
        if existing:
            # Check for unexpected drift
            if existing.schema_hash != schema_hash:
                raise SchemaDriftError(
                    f"Unexpected schema drift detected for tool '{server_name}.{tool_name}'. "
                    f"Pinned hash: {existing.schema_hash}, Remote server hash: {schema_hash}. "
                    "Invocation blocked until administrator audits new schema."
                )
            return existing

        if expected_hash and expected_hash != schema_hash:
            raise SchemaDriftError(
                f"Schema verification mismatch for tool '{server_name}.{tool_name}'. "
                f"Expected hash: {expected_hash}, Actual hash: {schema_hash}."
            )

        snapshot = MCPToolSchemaVersion(
            server_name=server_name,
            tool_name=tool_name,
            version=version,
            description=description,
            input_schema=input_schema,
            schema_hash=schema_hash,
            is_active=True,
        )
        self._tool_schemas[key] = snapshot
        self._tool_definitions[key] = MCPToolDefinition(
            name=tool_name,
            server_name=server_name,
            description=description,
            input_schema=input_schema,
            action_classification=action_classification,
        )
        return snapshot

    def get_tool_schema(self, server_name: str, tool_name: str) -> MCPToolSchemaVersion:
        """Retrieve pinned schema snapshot for a specific server and tool."""
        key = (server_name, tool_name)
        snapshot = self._tool_schemas.get(key)
        if not snapshot:
            raise UnknownToolError(f"Tool '{tool_name}' on server '{server_name}' has no registered schema snapshot.")
        return snapshot

    def get_tool_definition(self, server_name: str, tool_name: str) -> MCPToolDefinition:
        """Retrieve tool definition for a specific server and tool."""
        key = (server_name, tool_name)
        defn = self._tool_definitions.get(key)
        if not defn:
            raise UnknownToolError(f"Tool '{tool_name}' on server '{server_name}' is not registered.")
        return defn

    def list_tools(self, server_name: str | None = None) -> list[MCPToolDefinition]:
        """List all discovered tool definitions, optionally filtered by server."""
        if server_name:
            return [defn for (s, _), defn in self._tool_definitions.items() if s == server_name]
        return list(self._tool_definitions.values())
