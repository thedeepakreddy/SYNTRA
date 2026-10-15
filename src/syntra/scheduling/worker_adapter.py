"""Deterministic Test-Only Worker Execution Adapter.

=============================================================================
CRITICAL ARCHITECTURAL WARNING: TEST_ONLY ADAPTER
=============================================================================
This worker adapter is strictly intended for scheduler, dispatch, and lifecycle
integration tests in Phase 8. It DOES NOT provide isolated container sandboxes,
git worktree isolation, or restricted subprocess execution (which belong strictly
to Phase 9 Sandbox Execution).

Do not use this adapter in production deployments.
=============================================================================
"""

from __future__ import annotations

import logging
from decimal import Decimal
from uuid import uuid4

from syntra.domain.entities import AttemptState
from syntra.scheduling.models import TaskDispatchPayload, TaskExecutionResult

logger = logging.getLogger(__name__)


class TestWorkerAdapter:
    """TEST_ONLY: Simulates worker execution turns and result payload submission."""

    __test__ = False

    def __init__(self, worker_id: str = "test-worker-01") -> None:
        self.worker_id = worker_id

    async def execute_task(
        self,
        dispatch: TaskDispatchPayload,
        simulate_failure: bool = False,
        error_message: str | None = None,
        custom_diff: str | None = None,
        tokens_consumed: int = 500,
        cost_usd: Decimal = Decimal("0.001000"),
    ) -> TaskExecutionResult:
        """Simulate worker processing and generate an authoritative TaskExecutionResult."""
        logger.info(
            "[TEST_ONLY_ADAPTER] Executing task %s (role=%s, fencing_token=%d)",
            dispatch.task_id,
            dispatch.assigned_role,
            dispatch.fencing_token,
        )

        if simulate_failure:
            return TaskExecutionResult(
                task_id=dispatch.task_id,
                attempt_number=dispatch.attempt_number,
                worker_id=self.worker_id,
                fencing_token=dispatch.fencing_token,
                status=AttemptState.FAILED,
                exit_code=1,
                output_summary="Simulated worker execution failure.",
                error_message=error_message or "Process exited with non-zero exit code 1",
                actual_prompt_tokens=tokens_consumed // 2,
                actual_completion_tokens=tokens_consumed // 2,
                actual_cost_usd=cost_usd,
            )

        diff = custom_diff or (
            f"--- a/src/{dispatch.assigned_role}_module.py\n"
            f"+++ b/src/{dispatch.assigned_role}_module.py\n"
            "@@ -0,0 +1,5 @@\n"
            "+# Implemented task: " + str(dispatch.task_id) + "\n"
            "+def run():\n"
            "+    return True\n"
        )

        return TaskExecutionResult(
            task_id=dispatch.task_id,
            attempt_number=dispatch.attempt_number,
            worker_id=self.worker_id,
            fencing_token=dispatch.fencing_token,
            status=AttemptState.SUCCEEDED,
            exit_code=0,
            output_summary="Task completed successfully by test worker adapter.",
            unified_diff=diff,
            produced_artifact_ids=[uuid4()],
            actual_prompt_tokens=tokens_consumed // 2,
            actual_completion_tokens=tokens_consumed // 2,
            actual_cost_usd=cost_usd,
        )
