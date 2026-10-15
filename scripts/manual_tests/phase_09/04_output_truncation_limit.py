#!/usr/bin/env python3
"""Manual Test 04: Output Truncation Limit.

Verifies:
1. Commands producing stdout larger than max_output_bytes are capped.
2. An explicit truncation marker is appended to stdout.
3. output_truncated flag is set to True.
"""

import asyncio
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from syntra.sandbox.models import ContainerConfig
from syntra.sandbox.provider import DockerSandboxProvider


async def main() -> None:
    print("=== [PHASE 9 SCENARIO 04] Output Truncation Limit ===")

    base_dir = Path(__file__).parent.parent.parent.parent / ".syntra" / "test_sandboxes" / f"sc04_{uuid4().hex[:6]}"
    base_dir.mkdir(parents=True, exist_ok=True)
    repo_dir = base_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
        (repo_dir / "README.md").write_text("# Truncation Test\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True, capture_output=True)
        base_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True
        ).stdout.strip()

        # Set 4KB limit
        config = ContainerConfig(max_output_bytes=4096)
        provider = DockerSandboxProvider(default_config=config)
        sandbox = await provider.create_sandbox(uuid4(), 1, repo_dir, base_commit, config=config)

        try:
            print("[INFO] Generating 50KB of stdout...")
            res = await sandbox.execute_command("python3 -c \"print('X' * 50000)\"")

            assert res.is_success, "Command should complete with exit code 0"
            assert res.output_truncated is True, "output_truncated flag must be True"
            assert "[TRUNCATED at 4096 bytes]" in res.stdout, "Truncation marker must appear in stdout"
            print(f"[OK] Output capped at 4096 bytes with truncation marker: len={len(res.stdout)}")

        finally:
            await sandbox.cleanup()
            print("[OK] Sandbox cleanup complete")

    finally:
        shutil.rmtree(base_dir, ignore_errors=True)

    print("=== [SCENARIO 04 PASSED] ===\n")


if __name__ == "__main__":
    asyncio.run(main())
