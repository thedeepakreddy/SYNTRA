"""Tests for DevSwarm Model Context Protocol (MCP) server."""

import pytest
from devswarm.agents.tools import create_standard_workspace_tools
from devswarm.mcp.server import MCPServer
from devswarm.sandbox.runner import SandboxRunner
from devswarm.sandbox.workspace import WorkspaceManager


@pytest.fixture
def mcp_server(tmp_path):
    ws = WorkspaceManager(tmp_path)
    runner = SandboxRunner(tmp_path)
    tools = create_standard_workspace_tools(ws, runner)
    return MCPServer(tools=tools, server_name="devswarm-test-mcp")


@pytest.mark.asyncio
async def test_mcp_initialize(mcp_server):
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"},
        },
    }
    resp = await mcp_server.handle_request(req)
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    result = resp["result"]
    assert result["serverInfo"]["name"] == "devswarm-test-mcp"
    assert "tools" in result["capabilities"]


@pytest.mark.asyncio
async def test_mcp_ping(mcp_server):
    req = {"jsonrpc": "2.0", "id": 2, "method": "ping"}
    resp = await mcp_server.handle_request(req)
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 2
    assert resp["result"] == {}


@pytest.mark.asyncio
async def test_mcp_tools_list(mcp_server):
    req = {"jsonrpc": "2.0", "id": 3, "method": "tools/list"}
    resp = await mcp_server.handle_request(req)
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 3
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "read_file" in tool_names
    assert "write_file" in tool_names
    assert "execute_command" in tool_names
    assert "replace_content" in tool_names


@pytest.mark.asyncio
async def test_mcp_tools_call_execution(mcp_server):
    # 1. Call write_file
    write_req = {
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/call",
        "params": {
            "name": "write_file",
            "arguments": {
                "relative_path": "hello_mcp.txt",
                "content": "Hello from MCP Server!",
            },
        },
    }
    write_resp = await mcp_server.handle_request(write_req)
    assert write_resp["id"] == 10
    assert not write_resp["result"]["isError"]
    assert "Successfully wrote" in write_resp["result"]["content"][0]["text"]

    # 2. Call read_file
    read_req = {
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {
            "name": "read_file",
            "arguments": {
                "relative_path": "hello_mcp.txt",
            },
        },
    }
    read_resp = await mcp_server.handle_request(read_req)
    assert read_resp["id"] == 11
    assert not read_resp["result"]["isError"]
    assert read_resp["result"]["content"][0]["text"] == "Hello from MCP Server!"


@pytest.mark.asyncio
async def test_mcp_error_handling(mcp_server):
    # Unknown tool
    req_unknown = {
        "jsonrpc": "2.0",
        "id": 99,
        "method": "tools/call",
        "params": {
            "name": "nonexistent_tool",
            "arguments": {},
        },
    }
    resp = await mcp_server.handle_request(req_unknown)
    assert resp["id"] == 99
    assert resp["error"]["code"] == -32601

    # Unsupported method
    req_bad_method = {
        "jsonrpc": "2.0",
        "id": 100,
        "method": "unsupported_method",
        "params": {},
    }
    resp_bad = await mcp_server.handle_request(req_bad_method)
    assert resp_bad["id"] == 100
    assert resp_bad["error"]["code"] == -32601
