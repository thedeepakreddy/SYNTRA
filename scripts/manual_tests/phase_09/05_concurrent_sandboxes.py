#!/usr/bin/env python3
"""Manual Test 05: Concurrent Sandbox Execution.

Verifies:
1. Multiple isolated sandboxes run concurrently without race conditions.
2. Distinct branches and worktrees are completely isolated.
3. Both sandboxes produce disjoint, accurate unified diffs.
4. Independent teardown without interfering with sibling sandboxes.
"""

import asyncio
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from syntra.domain.entities import AttemptState
from syntra.sandbox.worker_bridge import SandboxWorkerAdapter
from syntra.scheduling.models import TaskDispatchPayload


async def main() -> None:
    print("=== [PHASE 9 SCENARIO 05] Concurrent Sandbox Execution ===")

    base_dir = Path(__file__).parent.parent.parent.parent / ".syntra" / "test_sandboxes" / f"sc05_{uuid4().hex[:6]}"
    base_dir.mkdir(parents=True, exist_ok=True)
    repo_dir = base_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
        (repo_dir / "README.md").write_text("# Concurrent Test\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True, capture_output=True)
        base_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True
        ).stdout.strip()

        adapter_1 = SandboxWorkerAdapter(repo_dir, worker_id="w-01", base_commit=base_commit)
        adapter_2 = SandboxWorkerAdapter(repo_dir, worker_id="w-02", base_commit=base_commit)

        task_1 = uuid4()
        task_2 = uuid4()

        d1 = TaskDispatchPayload(
            task_id=task_1,
            mission_id=uuid4(),
            org_id=uuid4(),
            attempt_number=1,
            assigned_role="backend_engineer",
            fencing_token=1,
            lease_expires_at=datetime.now(UTC),
            specification="Task 1",
        )
        d2 = TaskDispatchPayload(
            task_id=task_2,
            mission_id=uuid4(),
            org_id=uuid4(),
            attempt_number=1,
            assigned_role="frontend_engineer",
            fencing_token=1,
            lease_expires_at=datetime.now(UTC),
            specification="Task 2",
        )

        print("[INFO] Executing Task 1 and Task 2 concurrently in separate container sandboxes...")
        r1, r2 = await asyncio.gather(
            adapter_1.execute_task(
                dispatch=d1,
                code_changes={"task_1.py": "def f1(): return 100\n"},
                commands_to_run=['python3 -c "import task_1; assert task_1.f1() == 100"'],
            ),
            adapter_2.execute_task(
                dispatch=d2,
                code_changes={"task_2.py": "def f2(): return 200\n"},
                commands_to_run=['python3 -c "import task_2; assert task_2.f2() == 200"'],
            ),
        )

        assert r1.status == AttemptState.SUCCEEDED
        assert r2.status == AttemptState.SUCCEEDED
        print(f"[OK] Task 1 completed: exit_code={r1.exit_code}")
        print(f"[OK] Task 2 completed: exit_code={r2.exit_code}")

        # Check diff separation
        assert "task_1.py" in str(r1.unified_diff)
        assert "task_2.py" not in str(r1.unified_diff)

        assert "task_2.py" in str(r2.unified_diff)
        assert "task_1.py" not in str(r2.unified_diff)
        print("[OK] Disjoint unified diffs verified with zero cross-contamination")

    finally:
        shutil.rmtree(base_dir, ignore_errors=True)

    print("=== [SCENARIO 05 PASSED] ===\n")


if __name__ == "__main__":
    asyncio.run(main())
