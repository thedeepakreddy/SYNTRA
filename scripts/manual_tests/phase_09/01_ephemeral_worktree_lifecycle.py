#!/usr/bin/env python3
"""Manual Test 01: Ephemeral Git Worktree Lifecycle and Isolation.

Verifies:
1. Creation of ephemeral worktree branched from target commit.
2. Complete isolation from host repository.
3. Clean unified diff extraction.
4. Clean teardown and worktree pruning.
"""

import asyncio
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from syntra.sandbox.worktree import GitWorktreeManager


async def main() -> None:
    print("=== [PHASE 9 SCENARIO 01] Ephemeral Worktree Lifecycle ===")

    base_dir = Path(__file__).parent.parent.parent.parent / ".syntra" / "test_sandboxes" / f"sc01_{uuid4().hex[:6]}"
    base_dir.mkdir(parents=True, exist_ok=True)
    repo_dir = base_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Manual Tester"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "tester@syntra.local"], cwd=repo_dir, check=True, capture_output=True
        )

        (repo_dir / "main.py").write_text("def hello():\n    return False\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True, capture_output=True)
        res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True)
        base_commit = res.stdout.strip()
        print(f"[OK] Initialized test repository at base commit: {base_commit[:8]}")

        wt_mgr = GitWorktreeManager(repo_dir)
        task_id = uuid4()
        attempt = 1

        wt_path, branch_name = await wt_mgr.create_worktree(task_id, attempt, base_commit)
        assert wt_path.exists(), "Worktree path must exist on disk"
        print(f"[OK] Ephemeral worktree created: {wt_path.name} (branch: {branch_name})")

        # Modify file inside worktree
        wt_mgr.write_file(wt_path, "main.py", "def hello():\n    return True\n")
        print("[OK] Modified main.py inside worktree")

        # Verify host repo is completely untouched
        host_content = (repo_dir / "main.py").read_text(encoding="utf-8")
        assert "return False" in host_content, "Host repository must remain completely unmodified!"
        print("[OK] Host repository file content verified unmodified")

        # Extract diff
        diff = await wt_mgr.get_unified_diff(wt_path, base_commit)
        assert "-    return False" in diff and "+    return True" in diff, "Unified diff must capture modifications"
        print("[OK] Unified diff verified:")
        for line in diff.strip().splitlines()[-4:]:
            print(f"     {line}")

        # Clean removal
        await wt_mgr.remove_worktree(wt_path, branch_name)
        assert not wt_path.exists(), "Worktree directory must be removed"
        print("[OK] Ephemeral worktree removed and branch pruned successfully")

    finally:
        shutil.rmtree(base_dir, ignore_errors=True)

    print("=== [SCENARIO 01 PASSED] ===\n")


if __name__ == "__main__":
    asyncio.run(main())
