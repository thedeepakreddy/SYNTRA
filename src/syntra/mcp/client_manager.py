"""MCP Client Manager coordinating connections, tool discovery, and execution across transports."""

import asyncio
import logging
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client
from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult

from syntra.domain.entities import ActionClassification, MCPTransportType
from syntra.mcp.registry import MCPRegistry
from syntra.mcp.types import (
    ConnectionStatus,
    MCPConnection,
    MCPServerDefinition,
    MCPToolDefinition,
)

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Base exception for client manager failures."""


class MCPConnectionError(MCPClientError):
    """Raised when an MCP connection fails to initialize or drops unexpectedly."""


class MCPTimeoutError(MCPClientError):
    """Raised when a tool invocation exceeds its allocated timeout."""


class MCPProtocolError(MCPClientError):
    """Raised when an MCP server returns invalid, malformed, or protocol-violating responses."""


class MCPClientManager:
    """Manages connection lifecycles, discovery, and execution across stdio, HTTP, and internal servers."""

    def __init__(self, registry: MCPRegistry) -> None:
        self.registry = registry
        # Connection status tracking: server_name -> MCPConnection
        self._connections: dict[str, MCPConnection] = {}
        # In-process server registry: server_name -> MCPServer
        self._in_process_servers: dict[str, MCPServer] = {}

    def register_in_process_server(self, name: str, server: MCPServer) -> None:
        """Register an in-process MCPServer instance for zero-IPC dispatch."""
        self._in_process_servers[name] = server

    def register_server(self, server_def: MCPServerDefinition) -> MCPServerDefinition:
        """Register an approved server definition in the registry and initialize connection tracking."""
        registered = self.registry.register_server(server_def)
        self._connections[registered.name] = MCPConnection(
            server_name=registered.name,
            transport=registered.transport,
            status=ConnectionStatus.DISCONNECTED,
        )
        return registered

    def get_connection_status(self, server_name: str) -> MCPConnection:
        """Fetch current connection status for a server."""
        conn = self._connections.get(server_name)
        if not conn:
            conn = MCPConnection(
                server_name=server_name,
                transport=MCPTransportType.STDIO,
                status=ConnectionStatus.DISCONNECTED,
            )
            self._connections[server_name] = conn
        return conn

    async def initialize_connection(self, server_name: str) -> MCPConnection:
        """Initialize and verify connectivity with the target MCP server."""
        server_def = self.registry.get_server(server_name)
        conn = self.get_connection_status(server_name)
        conn.status = ConnectionStatus.CONNECTING

        try:
            # Check in-process server
            if server_name in self._in_process_servers:
                conn.status = ConnectionStatus.CONNECTED
                conn.last_error = None
                return conn

            # Check stdio or streamable_http server via actual protocol ping / initialization
            if server_def.transport == MCPTransportType.STDIO:
                params = StdioServerParameters(
                    command=server_def.command_or_url,
                    args=server_def.args,
                    env=server_def.env or None,
                )
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        init_res = await session.initialize()
                        logger.info(
                            "Connected to stdio MCP Server '%s' (SDK version: %s)",
                            server_name,
                            init_res.protocol_version,
                        )
            elif server_def.transport in (
                MCPTransportType.STREAMABLE_HTTP,
                MCPTransportType.SSE,
                MCPTransportType.HTTP,
            ):
                async with streamable_http_client(url=server_def.command_or_url) as (read, write):
                    async with ClientSession(read, write) as session:
                        init_res = await session.initialize()
                        logger.info(
                            "Connected to HTTP MCP Server '%s' (SDK version: %s)",
                            server_name,
                            init_res.protocol_version,
                        )

            conn.status = ConnectionStatus.CONNECTED
            conn.last_error = None
            return conn

        except Exception as exc:
            conn.status = ConnectionStatus.FAILED
            conn.last_error = str(exc)
            raise MCPConnectionError(f"Failed to connect to MCP server '{server_name}': {exc}") from exc

    async def discover_tools(self, server_name: str) -> list[MCPToolDefinition]:
        """Perform discovery on an MCP server, snapshotting tool schemas and updating the catalog."""
        server_def = self.registry.get_server(server_name)
        discovered: list[MCPToolDefinition] = []

        try:
            # 1. In-process MCPServer instance
            if server_name in self._in_process_servers:
                srv = self._in_process_servers[server_name]
                tools_list = await srv.list_tools()
                for tool in tools_list:
                    # Classify action based on tool name heuristics or annotations
                    action_class = ActionClassification.READ_ONLY
                    if any(w in tool.name for w in ("write", "create", "delete", "replace", "exec")):
                        action_class = ActionClassification.SANDBOX_WRITE
                    if any(w in tool.name for w in ("submit", "push", "publish", "deploy")):
                        action_class = ActionClassification.EXTERNAL_WRITE

                    self.registry.snapshot_tool_schema(
                        server_name=server_name,
                        tool_name=tool.name,
                        input_schema=tool.input_schema or {},
                        description=tool.description,
                        action_classification=action_class,
                    )
                    discovered.append(
                        MCPToolDefinition(
                            name=tool.name,
                            server_name=server_name,
                            description=tool.description,
                            input_schema=tool.input_schema or {},
                            action_classification=action_class,
                        )
                    )
                return discovered

            # 2. Stdio transport
            if server_def.transport == MCPTransportType.STDIO:
                params = StdioServerParameters(
                    command=server_def.command_or_url,
                    args=server_def.args,
                    env=server_def.env or None,
                )
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        res = await session.list_tools()
                        for tool in res.tools:
                            action_class = ActionClassification.READ_ONLY
                            if any(w in tool.name for w in ("write", "create", "delete", "replace", "exec")):
                                action_class = ActionClassification.SANDBOX_WRITE
                            if any(w in tool.name for w in ("submit", "push", "publish", "deploy")):
                                action_class = ActionClassification.EXTERNAL_WRITE

                            self.registry.snapshot_tool_schema(
                                server_name=server_name,
                                tool_name=tool.name,
                                input_schema=tool.input_schema or {},
                                description=tool.description,
                                action_classification=action_class,
                            )
                            discovered.append(
                                MCPToolDefinition(
                                    name=tool.name,
                                    server_name=server_name,
                                    description=tool.description,
                                    input_schema=tool.input_schema or {},
                                    action_classification=action_class,
                                )
                            )
                return discovered

            # 3. HTTP transport
            if server_def.transport in (MCPTransportType.STREAMABLE_HTTP, MCPTransportType.SSE, MCPTransportType.HTTP):
                async with streamable_http_client(url=server_def.command_or_url) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        res = await session.list_tools()
                        for tool in res.tools:
                            action_class = ActionClassification.READ_ONLY
                            self.registry.snapshot_tool_schema(
                                server_name=server_name,
                                tool_name=tool.name,
                                input_schema=tool.input_schema or {},
                                description=tool.description,
                                action_classification=action_class,
                            )
                            discovered.append(
                                MCPToolDefinition(
                                    name=tool.name,
                                    server_name=server_name,
                                    description=tool.description,
                                    input_schema=tool.input_schema or {},
                                    action_classification=action_class,
                                )
                            )
                return discovered

            return []

        except Exception as exc:
            conn = self.get_connection_status(server_name)
            conn.status = ConnectionStatus.FAILED
            conn.last_error = str(exc)
            raise MCPConnectionError(f"Tool discovery failed for server '{server_name}': {exc}") from exc

    def get_tool_schema(self, server_name: str, tool_name: str) -> dict[str, Any]:
        """Fetch the pinned input schema for a registered tool."""
        snapshot = self.registry.get_tool_schema(server_name, tool_name)
        return snapshot.input_schema

    async def invoke_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        """Execute a tool call against the server with timeout and error wrapping.

        Returns raw JSON dict with format: {"content": [...], "is_error": bool, "raw_output": str}
        """
        server_def = self.registry.get_server(server_name)

        def _format_result(call_res: Any) -> dict[str, Any]:
            if not isinstance(call_res, CallToolResult):
                return {
                    "content": [{"type": "text", "text": str(call_res)}],
                    "is_error": False,
                    "raw_output": str(call_res),
                }
            content_list = []
            raw_text_parts = []
            for item in call_res.content:
                if hasattr(item, "text"):
                    content_list.append({"type": "text", "text": item.text})
                    raw_text_parts.append(item.text)
                else:
                    content_list.append({"type": "unknown", "data": str(item)})
            return {
                "content": content_list,
                "is_error": bool(call_res.is_error),
                "raw_output": "\n".join(raw_text_parts),
            }

        async def _execute() -> dict[str, Any]:
            # 1. In-process server dispatch
            if server_name in self._in_process_servers:
                srv = self._in_process_servers[server_name]
                call_res = await srv.call_tool(tool_name, arguments)
                return _format_result(call_res)

            # 2. Stdio transport
            if server_def.transport == MCPTransportType.STDIO:
                params = StdioServerParameters(
                    command=server_def.command_or_url,
                    args=server_def.args,
                    env=server_def.env or None,
                )
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        call_res = await session.call_tool(tool_name, arguments)
                        return _format_result(call_res)

            # 3. Streamable HTTP transport
            if server_def.transport in (MCPTransportType.STREAMABLE_HTTP, MCPTransportType.SSE, MCPTransportType.HTTP):
                async with streamable_http_client(url=server_def.command_or_url) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        call_res = await session.call_tool(tool_name, arguments)
                        return _format_result(call_res)

            raise MCPProtocolError(f"Unsupported transport '{server_def.transport}' for server '{server_name}'")

        try:
            return await asyncio.wait_for(_execute(), timeout=timeout_seconds)
        except asyncio.TimeoutError as exc:
            raise MCPTimeoutError(
                f"Execution of tool '{server_name}.{tool_name}' timed out after {timeout_seconds}s."
            ) from exc
        except Exception as exc:
            conn = self.get_connection_status(server_name)
            conn.last_error = str(exc)
            raise

    async def close_connection(self, server_name: str) -> None:
        """Close any open connections or subprocess resources associated with an MCP server."""
        conn = self._connections.get(server_name)
        if conn:
            conn.status = ConnectionStatus.CLOSED
            logger.info("Closed connection to MCP server '%s'", server_name)

    async def recover_connection(self, server_name: str) -> MCPConnection:
        """Recover a dropped or failed connection by resetting state and re-verifying handshake."""
        await self.close_connection(server_name)
        conn = self.get_connection_status(server_name)
        conn.reconnect_attempts += 1
        return await self.initialize_connection(server_name)
