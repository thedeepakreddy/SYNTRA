"""Model Context Protocol (MCP) server implementation with JSON-RPC 2.0 stdio transport."""

import asyncio
import json
import logging
import sys
from typing import Any
from devswarm.agents.tools import ToolRegistry, create_standard_workspace_tools
from devswarm.sandbox.runner import SandboxRunner
from devswarm.sandbox.workspace import WorkspaceManager

logger = logging.getLogger(__name__)

MCP_PROTOCOL_VERSION = "2024-11-05"


class MCPServer:
    """Implements standard Model Context Protocol (MCP) JSON-RPC 2.0 handler."""

    def __init__(self, tools: ToolRegistry, server_name: str = "devswarm-mcp", version: str = "0.1.0") -> None:
        self.tools = tools
        self.server_name = server_name
        self.version = version

    async def handle_request(self, request_data: dict[str, Any]) -> dict[str, Any] | None:
        """Process a single JSON-RPC request and return response."""
        req_id = request_data.get("id")
        method = request_data.get("method")
        params = request_data.get("params", {})

        # Handle notifications (requests without id)
        if req_id is None and method == "notifications/initialized":
            return None

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {
                            "listChanged": False,
                        }
                    },
                    "serverInfo": {
                        "name": self.server_name,
                        "version": self.version,
                    },
                },
            }

        elif method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        elif method == "tools/list":
            mcp_tools = self.tools.export_mcp_tools()
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": mcp_tools},
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if not tool_name:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": "Missing 'name' parameter for tools/call"},
                }

            tool = self.tools.get(tool_name)
            if not tool:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"},
                }

            try:
                raw_output = await self.tools.execute(tool_name, arguments)
                output_str = raw_output if isinstance(raw_output, str) else json.dumps(raw_output, indent=2)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": output_str}
                        ],
                        "isError": False,
                    },
                }
            except Exception as exc:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": f"Tool execution failed: {exc}"}
                        ],
                        "isError": True,
                    },
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method '{method}' not supported"},
            }

    async def run_stdio(self) -> None:
        """Run standard I/O loop consuming line-delimited JSON-RPC from stdin."""
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            line = await reader.readline()
            if not line:
                break

            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue

            try:
                req = json.loads(line_str)
                resp = await self.handle_request(req)
                if resp is not None:
                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()
            except json.JSONDecodeError:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error: Invalid JSON"},
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()
