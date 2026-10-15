#!/usr/bin/env python3
"""Manual Test 07: Path Traversal Defense.

Verifies:
1. Canonical path checking prevents reading files outside worktree root.
2. Canonical path checking prevents writing files outside worktree root.
3. Path traversal attempts raise SandboxSecurityViolationError.
"""

import asyncio
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from syntra.core.exceptions import SandboxSecurityViolationError
from syntra.sandbox.worktree import GitWorktreeManager


async def main() -> None:
    print("=== [PHASE 9 SCENARIO 07] Path Traversal Defense ===")

    base_dir = Path(__file__).parent.parent.parent.parent / ".syntra" / "test_sandboxes" / f"sc07_{uuid4().hex[:6]}"
    base_dir.mkdir(parents=True, exist_ok=True)
    repo_dir = base_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
        (repo_dir / "README.md").write_text("# Defense Test\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True, capture_output=True)
        base_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True
        ).stdout.strip()

        wt_mgr = GitWorktreeManager(repo_dir)
        wt_path, branch = await wt_mgr.create_worktree(uuid4(), 1, base_commit)

        try:
            # Traversal read attack
            caught_read = False
            try:
                wt_mgr.read_file(wt_path, "../../etc/shadow")
            except SandboxSecurityViolationError as exc:
                caught_read = True
                print(f"[OK] Blocked traversal read: {exc}")
            assert caught_read, "Path traversal read must be rejected!"

            # Traversal write attack
            caught_write = False
            try:
                wt_mgr.write_file(wt_path, "../../../tmp/escaped.txt", "payload")
            except SandboxSecurityViolationError as exc:
                caught_write = True
                print(f"[OK] Blocked traversal write: {exc}")
            assert caught_write, "Path traversal write must be rejected!"

        finally:
            await wt_mgr.remove_worktree(wt_path, branch)

    finally:
        shutil.rmtree(base_dir, ignore_errors=True)

    print("=== [SCENARIO 07 PASSED] ===\n")


if __name__ == "__main__":
    asyncio.run(main())
