"""Real Streamable HTTP MCP transport integration tests using official MCP SDK (mcp==2.3.0).

Verifies all 10 protocol interoperability scenarios:
1. Server startup on ephemeral port.
2. Client initialization & protocol negotiation.
3. Tool discovery via HTTP.
4. Successful tool invocation.
5. Invalid tool arguments rejection.
6. Connection timeout enforcement.
7. Server disconnection handling.
8. Connection recovery.
9. Authorization enforcement via ToolGateway.
10. Clean server shutdown and resource release.
"""

import asyncio
import socket
import time
from uuid import uuid4

import pytest
import uvicorn
from mcp.server.mcpserver import MCPServer

from syntra.domain.entities import MCPTransportType, TrustClassification
from syntra.mcp.client_manager import MCPClientManager, MCPTimeoutError
from syntra.mcp.gateway import ToolGateway
from syntra.mcp.policy import CapabilityPolicyEngine
from syntra.mcp.registry import MCPRegistry
from syntra.mcp.types import ConnectionStatus, MCPInvocationRequest, MCPServerDefinition


def get_ephemeral_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest.fixture
async def http_mcp_server():
    """Start a real local Streamable HTTP MCP server on an ephemeral local port."""
    port = get_ephemeral_port()
    server = MCPServer("real_http_mcp", version="0.1.0")

    @server.tool("echo", description="Echo message back over HTTP")
    def echo(message: str) -> str:
        return f"http-echo: {message}"

    @server.tool("slow_http_tool", description="Slow tool for HTTP timeout testing")
    def slow_http_tool(delay_seconds: float) -> str:
        time.sleep(delay_seconds)
        return "slow-http-completed"

    @server.tool("math_multiply", description="Multiply two integers")
    def math_multiply(a: int, b: int) -> int:
        return a * b

    app = server.streamable_http_app(streamable_http_path="/mcp")
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    uv_server = uvicorn.Server(config)

    server_task = asyncio.create_task(uv_server.serve())
    while not uv_server.started:
        await asyncio.sleep(0.05)

    url = f"http://127.0.0.1:{port}/mcp"

    yield {
        "url": url,
        "port": port,
        "uv_server": uv_server,
        "server_task": server_task,
    }

    uv_server.should_exit = True
    await server_task


# ==============================================================================
# TEST 1 & 2: Server Startup and Client Initialization
# ==============================================================================
@pytest.mark.asyncio
async def test_01_and_02_server_startup_and_initialization(http_mcp_server):
    """Verify HTTP server startup on ephemeral port and client protocol negotiation."""
    registry = MCPRegistry()
    client_manager = MCPClientManager(registry)

    server_def = MCPServerDefinition(
        name="real_http_mcp",
        transport=MCPTransportType.STREAMABLE_HTTP,
        trust_classification=TrustClassification.LOCAL_TRUSTED,
        command_or_url=http_mcp_server["url"],
        is_enabled=True,
    )
    client_manager.register_server(server_def)

    conn = await client_manager.initialize_connection("real_http_mcp")
    assert conn.status == ConnectionStatus.CONNECTED
    assert conn.server_name == "real_http_mcp"
    assert conn.last_error is None


# ==============================================================================
# TEST 3: Tool Discovery via Streamable HTTP
# ==============================================================================
@pytest.mark.asyncio
async def test_03_tool_discovery_over_http(http_mcp_server):
    """Verify tool discovery across real HTTP /mcp endpoint and schema snapshotting."""
    registry = MCPRegistry()
    client_manager = MCPClientManager(registry)

    server_def = MCPServerDefinition(
        name="real_http_mcp",
        transport=MCPTransportType.STREAMABLE_HTTP,
        trust_classification=TrustClassification.LOCAL_TRUSTED,
        command_or_url=http_mcp_server["url"],
        is_enabled=True,
    )
    client_manager.register_server(server_def)

    tools = await client_manager.discover_tools("real_http_mcp")
    tool_names = [t.name for t in tools]

    assert "echo" in tool_names
    assert "slow_http_tool" in tool_names
    assert "math_multiply" in tool_names

    # Verify registry snapshot
    snapshot = registry.get_tool_schema("real_http_mcp", "echo")
    assert len(snapshot.schema_hash) == 64


# ==============================================================================
# TEST 4: Successful Tool Invocation over HTTP
# ==============================================================================
@pytest.mark.asyncio
async def test_04_successful_tool_invocation_over_http(http_mcp_server):
    """Verify remote tool execution over real HTTP transport."""
    registry = MCPRegistry()
    client_manager = MCPClientManager(registry)

    server_def = MCPServerDefinition(
        name="real_http_mcp",
        transport=MCPTransportType.STREAMABLE_HTTP,
        trust_classification=TrustClassification.LOCAL_TRUSTED,
        command_or_url=http_mcp_server["url"],
        is_enabled=True,
    )
    client_manager.register_server(server_def)
    await client_manager.discover_tools("real_http_mcp")

    res = await client_manager.invoke_tool(
        server_name="real_http_mcp",
        tool_name="echo",
        arguments={"message": "SYNTRA HTTP Protocol Active"},
    )

    assert res["is_error"] is False
    assert res["raw_output"] == "http-echo: SYNTRA HTTP Protocol Active"


# ==============================================================================
# TEST 5: Invalid Tool Arguments over HTTP
# ==============================================================================
@pytest.mark.asyncio
async def test_05_invalid_tool_arguments_over_http(http_mcp_server):
    """Verify Tool Gateway validates schemas and rejects invalid arguments before/during HTTP dispatch."""
    registry = MCPRegistry()
    client_manager = MCPClientManager(registry)
    policy_engine = CapabilityPolicyEngine()
    gateway = ToolGateway(registry, client_manager, policy_engine)

    server_def = MCPServerDefinition(
        name="real_http_mcp",
        transport=MCPTransportType.STREAMABLE_HTTP,
        trust_classification=TrustClassification.LOCAL_TRUSTED,
        command_or_url=http_mcp_server["url"],
        is_enabled=True,
    )
    client_manager.register_server(server_def)
    await client_manager.discover_tools("real_http_mcp")

    org_id = uuid4()
    policy_engine.register_grant(org_id=org_id, agent_role="backend_engineer", tool_name_pattern="*")

    # Missing required argument 'message'
    req = MCPInvocationRequest(
        org_id=org_id,
        caller_role="backend_engineer",
        server_name="real_http_mcp",
        tool_name="echo",
        arguments={},
    )
    result = await gateway.execute_tool_call(req)

    assert result.status == "ERROR"
    assert result.is_error is True
    assert result.error_code == -32602
    assert "Argument schema validation failed" in (result.error_message or "")


# ==============================================================================
# TEST 6: Connection Timeout over HTTP
# ==============================================================================
@pytest.mark.asyncio
async def test_06_connection_timeout_over_http(http_mcp_server):
    """Verify tool execution exceeding allocated timeout is cancelled."""
    registry = MCPRegistry()
    client_manager = MCPClientManager(registry)

    server_def = MCPServerDefinition(
        name="real_http_mcp",
        transport=MCPTransportType.STREAMABLE_HTTP,
        trust_classification=TrustClassification.LOCAL_TRUSTED,
        command_or_url=http_mcp_server["url"],
        is_enabled=True,
    )
    client_manager.register_server(server_def)
    await client_manager.discover_tools("real_http_mcp")

    with pytest.raises(MCPTimeoutError) as exc_info:
        await client_manager.invoke_tool(
            server_name="real_http_mcp",
            tool_name="slow_http_tool",
            arguments={"delay_seconds": 3.0},
            timeout_seconds=1.0,
        )

    assert "timed out after 1.0s" in str(exc_info.value)


# ==============================================================================
# TEST 7: Server Disconnection
# ==============================================================================
@pytest.mark.asyncio
async def test_07_server_disconnection_handling(http_mcp_server):
    """Verify graceful handling when the remote HTTP server disconnects or stops."""
    registry = MCPRegistry()
    client_manager = MCPClientManager(registry)

    # Point to an unallocated port where server is not listening
    unallocated_port = get_ephemeral_port()
    server_def = MCPServerDefinition(
        name="dead_http_mcp",
        transport=MCPTransportType.STREAMABLE_HTTP,
        trust_classification=TrustClassification.LOCAL_TRUSTED,
        command_or_url=f"http://127.0.0.1:{unallocated_port}/mcp",
        is_enabled=True,
    )
    client_manager.register_server(server_def)

    with pytest.raises(Exception):
        await client_manager.initialize_connection("dead_http_mcp")

    conn = client_manager.get_connection_status("dead_http_mcp")
    assert conn.status == ConnectionStatus.FAILED
    assert conn.last_error is not None


# ==============================================================================
# TEST 8: Connection Recovery over HTTP
# ==============================================================================
@pytest.mark.asyncio
async def test_08_connection_recovery_over_http(http_mcp_server):
    """Verify that recover_connection resets session state and successfully reconnects."""
    registry = MCPRegistry()
    client_manager = MCPClientManager(registry)

    server_def = MCPServerDefinition(
        name="real_http_mcp",
        transport=MCPTransportType.STREAMABLE_HTTP,
        trust_classification=TrustClassification.LOCAL_TRUSTED,
        command_or_url=http_mcp_server["url"],
        is_enabled=True,
    )
    client_manager.register_server(server_def)
    await client_manager.initialize_connection("real_http_mcp")

    recovered = await client_manager.recover_connection("real_http_mcp")
    assert recovered.status == ConnectionStatus.CONNECTED
    assert recovered.reconnect_attempts == 1


# ==============================================================================
# TEST 9: Authorization Enforcement via ToolGateway over HTTP
# ==============================================================================
@pytest.mark.asyncio
async def test_09_authorization_enforcement_over_http(http_mcp_server):
    """Verify ToolGateway RBAC and capability policy apply to remote HTTP MCP tools."""
    registry = MCPRegistry()
    client_manager = MCPClientManager(registry)
    policy_engine = CapabilityPolicyEngine()
    gateway = ToolGateway(registry, client_manager, policy_engine)

    server_def = MCPServerDefinition(
        name="real_http_mcp",
        transport=MCPTransportType.STREAMABLE_HTTP,
        trust_classification=TrustClassification.LOCAL_TRUSTED,
        command_or_url=http_mcp_server["url"],
        is_enabled=True,
    )
    client_manager.register_server(server_def)
    await client_manager.discover_tools("real_http_mcp")

    org_id = uuid4()
    # Grant ONLY backend_engineer, caller is product_manager
    policy_engine.register_grant(org_id=org_id, agent_role="backend_engineer", tool_name_pattern="*")

    req_denied = MCPInvocationRequest(
        org_id=org_id,
        caller_role="product_manager",  # Not granted
        server_name="real_http_mcp",
        tool_name="echo",
        arguments={"message": "test"},
    )
    res_denied = await gateway.execute_tool_call(req_denied)

    assert res_denied.status == "BLOCKED_BY_POLICY"
    assert res_denied.is_error is True
    assert res_denied.error_code == -32000

    # Authorized caller
    req_allowed = MCPInvocationRequest(
        org_id=org_id,
        caller_role="backend_engineer",
        server_name="real_http_mcp",
        tool_name="echo",
        arguments={"message": "Authorized User"},
    )
    res_allowed = await gateway.execute_tool_call(req_allowed)

    assert res_allowed.status == "SUCCESS"
    assert res_allowed.raw_output == "http-echo: Authorized User"


# ==============================================================================
# TEST 10: Clean Server Shutdown and Cleanup
# ==============================================================================
@pytest.mark.asyncio
async def test_10_server_shutdown_and_cleanup():
    """Verify server shutdown releases local socket and close_connection releases client."""
    port = get_ephemeral_port()
    server = MCPServer("temp_http_mcp", version="0.1.0")

    @server.tool("ping")
    def ping() -> str:
        return "pong"

    app = server.streamable_http_app(streamable_http_path="/mcp")
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    uv_server = uvicorn.Server(config)
    server_task = asyncio.create_task(uv_server.serve())

    while not uv_server.started:
        await asyncio.sleep(0.05)

    registry = MCPRegistry()
    client_manager = MCPClientManager(registry)
    server_def = MCPServerDefinition(
        name="temp_http_mcp",
        transport=MCPTransportType.STREAMABLE_HTTP,
        trust_classification=TrustClassification.LOCAL_TRUSTED,
        command_or_url=f"http://127.0.0.1:{port}/mcp",
        is_enabled=True,
    )
    client_manager.register_server(server_def)
    conn = await client_manager.initialize_connection("temp_http_mcp")
    assert conn.status == ConnectionStatus.CONNECTED

    # Close client connection
    await client_manager.close_connection("temp_http_mcp")
    assert conn.status == ConnectionStatus.CLOSED

    # Shutdown server
    uv_server.should_exit = True
    await server_task
    assert server_task.done()
