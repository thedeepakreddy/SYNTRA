#!/usr/bin/env python3
"""Manual Test 03: Execution Timeout Watchdog.

Verifies:
1. Long-running or runaway commands are terminated after the configured timeout.
2. timed_out flag is set to True.
3. Exit code indicates failure.
4. Container remains stable and responsive after timeout termination.
"""

import asyncio
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from syntra.sandbox.provider import DockerSandboxProvider


async def main() -> None:
    print("=== [PHASE 9 SCENARIO 03] Execution Timeout Watchdog ===")

    base_dir = Path(__file__).parent.parent.parent.parent / ".syntra" / "test_sandboxes" / f"sc03_{uuid4().hex[:6]}"
    base_dir.mkdir(parents=True, exist_ok=True)
    repo_dir = base_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
        (repo_dir / "README.md").write_text("# Timeout Test\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True, capture_output=True)
        base_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True
        ).stdout.strip()

        provider = DockerSandboxProvider()
        sandbox = await provider.create_sandbox(uuid4(), 1, repo_dir, base_commit)

        try:
            print("[INFO] Launching command 'sleep 10' with 2-second timeout...")
            res = await sandbox.execute_command("sleep 10", timeout_seconds=2)

            assert res.timed_out is True, "Expected res.timed_out to be True"
            assert not res.is_success, "Timed-out command must not report success"
            assert "timed out after 2 seconds" in res.stderr
            print(f"[OK] Watchdog fired in {res.duration_ms}ms: {res.stderr.strip()}")

            # Verify container is still healthy and accepts subsequent commands
            echo_res = await sandbox.execute_command("echo 'healthy'")
            assert echo_res.is_success
            assert "healthy" in echo_res.stdout
            print("[OK] Container remains responsive and healthy after timeout termination")

        finally:
            await sandbox.cleanup()
            print("[OK] Sandbox cleanup complete")

    finally:
        shutil.rmtree(base_dir, ignore_errors=True)

    print("=== [SCENARIO 03 PASSED] ===\n")


if __name__ == "__main__":
    asyncio.run(main())
