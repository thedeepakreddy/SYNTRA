"""Comprehensive end-to-end evaluation tests for SYNTRA."""

import pytest

from syntra.core.config import AutonomyMode
from syntra.llm import MockLLMClient
from syntra.swarm import SwarmEngine


@pytest.mark.asyncio
async def test_self_healing_review_and_fix_loop(tmp_path):
    """Test multi-agent self-healing cycle:
    1. Architect designs
    2. Planner breaks down tasks
    3. Coder implements with a minor bug
    4. Tester notices test failure
    5. Reviewer rejects and requests fix
    6. Coder fixes implementation
    7. Tester reports all green
    8. Reviewer APPROVES
    9. Security audits and passes
    """
    mock_llm = MockLLMClient()

    # 1. Architect
    mock_llm.queue_response("Architecture: Math service with fibonacci calculation.")
    # 2. Planner
    mock_llm.queue_response("Task 1: Implement fibonacci function. Task 2: Add tests.")
    # 3. Coder Iteration 0 (Buggy implementation: n <= 0 returns 0, but n=1 returns 0 instead of 1)
    mock_llm.queue_response(
        {
            "text": "Writing buggy fibonacci to math_svc.py",
            "tool_calls": [
                {
                    "id": "c-buggy",
                    "name": "write_file",
                    "arguments": {
                        "relative_path": "math_svc.py",
                        "content": "def fib(n):\n    if n <= 1:\n        return 0\n    return fib(n-1) + fib(n-2)\n",
                    },
                }
            ],
        }
    )
    mock_llm.queue_response("Implemented initial math_svc.py")
    # 4. Tester Iteration 0
    mock_llm.queue_response("Running tests: FAILED fib(1) expected 1 got 0.")
    # 5. Reviewer Iteration 0 (REJECTS with feedback)
    mock_llm.queue_response("Code Review: REJECTED. fib(1) must return 1, not 0. Fix the base condition.")
    # 6. Coder Iteration 1 (Fixes the bug)
    mock_llm.queue_response(
        {
            "text": "Fixing fibonacci base condition in math_svc.py",
            "tool_calls": [
                {
                    "id": "c-fix",
                    "name": "replace_content",
                    "arguments": {
                        "relative_path": "math_svc.py",
                        "target": "    if n <= 1:\n        return 0",
                        "replacement": "    if n <= 0:\n        return 0\n    if n == 1:\n        return 1",
                    },
                }
            ],
        }
    )
    mock_llm.queue_response("Fixed fibonacci base condition in math_svc.py.")
    # 7. Tester Iteration 1
    mock_llm.queue_response("Running tests: PASSED 5 tests, 0 failed. All green.")
    # 8. Reviewer Iteration 1 (APPROVES)
    mock_llm.queue_response("Code Review: APPROVED. Base condition is correct and all tests pass.")
    # 9. Security
    mock_llm.queue_response("Security audit: No vulnerabilities found. Clean release.")

    engine = SwarmEngine(
        workspace_dir=tmp_path,
        llm_client=mock_llm,
        session_id="test-self-healing",
        autonomy_mode=AutonomyMode.AUTONOMOUS,
    )

    final_state = await engine.execute_task(
        objective="Implement and verify mathematical fibonacci service",
        max_iterations=3,
    )

    assert final_state.is_completed
    assert final_state.iteration == 1  # Exactly 1 retry occurred and succeeded
    assert final_state.review_approved is True
    assert final_state.security_passed is True

    # Validate workspace file state
    assert engine.workspace.file_exists("math_svc.py")
    content = engine.workspace.read_file("math_svc.py")
    assert "if n == 1:\n        return 1" in content
