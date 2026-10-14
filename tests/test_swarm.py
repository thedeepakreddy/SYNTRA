"""Tests for Swarm orchestration and StateGraph engine."""

import pytest
from devswarm.llm import MockLLMClient
from devswarm.swarm import StateGraph, SwarmEngine, SwarmState


@pytest.mark.asyncio
async def test_state_graph_execution():
    graph = StateGraph(name="test_graph")

    async def step_a(state: SwarmState) -> SwarmState:
        state.blackboard["a"] = "done"
        return state

    async def step_b(state: SwarmState) -> SwarmState:
        state.blackboard["b"] = "done"
        return state

    def route_condition(state: SwarmState) -> str:
        if state.blackboard.get("a") == "done":
            return "proceed"
        return "halt"

    graph.add_node("node_a", step_a)
    graph.add_node("node_b", step_b)
    graph.set_entry_point("node_a")

    graph.add_conditional_edges(
        "node_a",
        route_condition,
        {"proceed": "node_b", "halt": "node_a"},
    )
    graph.set_finish_point("node_b")

    initial = SwarmState(session_id="s1", objective="Test routing")
    final = await graph.execute(initial)

    assert final.is_completed
    assert final.blackboard.get("a") == "done"
    assert final.blackboard.get("b") == "done"


@pytest.mark.asyncio
async def test_swarm_engine_end_to_end_flow(tmp_path):
    mock_llm = MockLLMClient()

    # Step responses for each agent in order:
    # 1. Architect
    mock_llm.queue_response("Architecture spec: Modular monolith with user service and jwt auth.")
    # 2. Planner
    mock_llm.queue_response("Task 1: Create auth module. Task 2: Write tests.")
    # 3. Coder (tool call: write_file auth.py)
    mock_llm.queue_response({
        "text": "Writing auth.py file",
        "tool_calls": [
            {
                "id": "c-auth",
                "name": "write_file",
                "arguments": {
                    "relative_path": "auth.py",
                    "content": "def authenticate(user, password):\n    return True\n",
                },
            }
        ],
    })
    mock_llm.queue_response("Finished implementing auth.py")
    # 4. Tester
    mock_llm.queue_response("Ran tests: 2 passed, 0 failed. All tests green.")
    # 5. Reviewer
    mock_llm.queue_response("Code review: APPROVED. Clean code and tests pass.")
    # 6. Security
    mock_llm.queue_response("Security scan complete. No critical vulnerabilities found.")

    from devswarm.core.config import AutonomyMode
    engine = SwarmEngine(
        workspace_dir=tmp_path,
        llm_client=mock_llm,
        session_id="test-e2e",
        autonomy_mode=AutonomyMode.AUTONOMOUS,
    )
    final_state = await engine.execute_task(objective="Implement authentication system")

    assert final_state.is_completed
    assert final_state.stage == "completed"
    assert final_state.review_approved is True
    assert final_state.security_passed is True
    assert engine.workspace.file_exists("auth.py")
    assert "def authenticate" in engine.workspace.read_file("auth.py")
