"""Tests for DevSwarm agent framework."""

import pytest
from devswarm.agents import (
    AgentContext,
    AgentMemory,
    BaseAgent,
    CoderAgent,
    ToolRegistry,
    create_standard_workspace_tools,
)
from devswarm.llm import LLMMessage, MessageRole, MockLLMClient
from devswarm.sandbox import SandboxRunner, WorkspaceManager


def test_agent_memory():
    memory = AgentMemory()
    memory.set("current_branch", "feat/auth")
    assert memory.get("current_branch") == "feat/auth"

    memory.record_note("arch_decision", "Use JWT tokens with RS256", "architect", tags=["auth", "security"])
    memory.record_note("db_choice", "Use PostgreSQL with asyncpg", "architect", tags=["db"])

    auth_notes = memory.find_notes(tag="auth")
    assert len(auth_notes) == 1
    assert "RS256" in auth_notes[0].content

    dump = memory.dump_context()
    assert "current_branch" in dump
    assert "RS256" in dump


def test_agent_context_compaction():
    ctx = AgentContext(session_id="s1", agent_id="a1", role="coder", max_history_messages=10)
    # Add 15 messages
    for i in range(15):
        ctx.add_user_message(f"Message {i}")

    # Should have compacted
    assert len(ctx.history) <= 10 or "[SYSTEM CONTEXT COMPACTION" in str(ctx.history)


def test_tool_registry_mcp_export(tmp_path):
    ws = WorkspaceManager(tmp_path)
    runner = SandboxRunner(tmp_path)
    tools = create_standard_workspace_tools(ws, runner)

    # Check definitions
    defs = tools.get_definitions()
    tool_names = [d.name for d in defs]
    assert "read_file" in tool_names
    assert "write_file" in tool_names
    assert "execute_command" in tool_names

    # Check MCP schema export
    mcp_tools = tools.export_mcp_tools()
    assert len(mcp_tools) >= 5
    read_tool = next(t for t in mcp_tools if t["name"] == "read_file")
    assert "inputSchema" in read_tool
    assert read_tool["inputSchema"]["type"] == "object"


@pytest.mark.asyncio
async def test_agent_react_loop_with_tools(tmp_path):
    ws = WorkspaceManager(tmp_path)
    runner = SandboxRunner(tmp_path)
    tools = create_standard_workspace_tools(ws, runner)

    llm = MockLLMClient()
    # Step 1: LLM decides to call tool 'write_file'
    llm.queue_response({
        "text": "I will create index.py",
        "tool_calls": [
            {
                "id": "call-1",
                "name": "write_file",
                "arguments": {
                    "relative_path": "index.py",
                    "content": "print('DevSwarm is active')\n",
                },
            }
        ],
    })
    # Step 2: LLM finishes task
    llm.queue_response("I have successfully created index.py.")

    agent = CoderAgent(llm_client=llm, tools=tools, session_id="test-session")
    result = await agent.run_task("Create index.py file")

    assert result.success
    assert "successfully created" in result.output
    assert ws.file_exists("index.py")
    assert "DevSwarm is active" in ws.read_file("index.py")
    assert result.steps_taken == 2
    assert result.tool_calls_count == 1
