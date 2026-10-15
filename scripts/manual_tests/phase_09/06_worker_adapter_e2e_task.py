#!/usr/bin/env python3
"""Manual Test 06: End-to-End Task Execution via SandboxWorkerAdapter.

Verifies:
1. Dispatch of engineering task to SandboxWorkerAdapter.
2. Code modification applied inside worktree.
3. Automated verification executed inside container.
4. Unified diff artifact generated.
5. Produced artifact ID and token/cost metrics recorded.
"""

import asyncio
import shutil
import subprocess
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from syntra.domain.entities import AttemptState
from syntra.sandbox.worker_bridge import SandboxWorkerAdapter
from syntra.scheduling.models import TaskDispatchPayload


async def main() -> None:
    print("=== [PHASE 9 SCENARIO 06] End-to-End Task Execution ===")

    base_dir = Path(__file__).parent.parent.parent.parent / ".syntra" / "test_sandboxes" / f"sc06_{uuid4().hex[:6]}"
    base_dir.mkdir(parents=True, exist_ok=True)
    repo_dir = base_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
        (repo_dir / "app.py").write_text("def solve():\n    return 'unimplemented'\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True, capture_output=True)
        base_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True
        ).stdout.strip()

        adapter = SandboxWorkerAdapter(repo_dir, worker_id="e2e-worker", base_commit=base_commit)

        task_id = uuid4()
        dispatch = TaskDispatchPayload(
            task_id=task_id,
            mission_id=uuid4(),
            org_id=uuid4(),
            attempt_number=1,
            assigned_role="backend_engineer",
            fencing_token=1,
            lease_expires_at=datetime.now(UTC),
            specification="Implement solve() in app.py to return 'solved'",
        )

        print("[INFO] Executing task via SandboxWorkerAdapter...")
        result = await adapter.execute_task(
            dispatch=dispatch,
            code_changes={"app.py": "def solve():\n    return 'solved'\n"},
            commands_to_run=["python3 -c \"import app; assert app.solve() == 'solved'\""],
            tokens_consumed=800,
            cost_usd=Decimal("0.001600"),
        )

        assert result.status == AttemptState.SUCCEEDED
        assert result.exit_code == 0
        assert result.unified_diff is not None
        assert "-    return 'unimplemented'" in result.unified_diff
        assert "+    return 'solved'" in result.unified_diff
        assert len(result.produced_artifact_ids) > 0
        assert result.actual_prompt_tokens == 400
        assert result.actual_cost_usd == Decimal("0.001600")

        print("[OK] Task succeeded with verified diff and artifact ID:")
        print(f"     Artifact ID: {result.produced_artifact_ids[0]}")
        print(f"     Tokens: {result.actual_prompt_tokens} prompt / {result.actual_completion_tokens} completion")
        print(f"     Cost: ${result.actual_cost_usd}")

    finally:
        shutil.rmtree(base_dir, ignore_errors=True)

    print("=== [SCENARIO 06 PASSED] ===\n")


if __name__ == "__main__":
    asyncio.run(main())
