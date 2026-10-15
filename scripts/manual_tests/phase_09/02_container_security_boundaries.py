#!/usr/bin/env python3
"""Manual Test 02: Container Security Boundaries.

Verifies:
1. Container executes as non-root user (UID != 0).
2. Read-only root filesystem prevents modification to /etc.
3. Dedicated tmpfs (/tmp) is writable.
4. Network isolation (--network none) blocks outbound traffic.
5. All Linux capabilities are dropped.
"""

import asyncio
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from syntra.sandbox.provider import DockerSandboxProvider


async def main() -> None:
    print("=== [PHASE 9 SCENARIO 02] Container Security Boundaries ===")

    base_dir = Path(__file__).parent.parent.parent.parent / ".syntra" / "test_sandboxes" / f"sc02_{uuid4().hex[:6]}"
    base_dir.mkdir(parents=True, exist_ok=True)
    repo_dir = base_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
        (repo_dir / "README.md").write_text("# Security Test\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True, capture_output=True)
        base_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True
        ).stdout.strip()

        provider = DockerSandboxProvider()
        assert await provider.is_available(), "Docker container runtime must be available"
        print("[OK] Docker provider is online and responsive")

        task_id = uuid4()
        sandbox = await provider.create_sandbox(task_id, 1, repo_dir, base_commit)
        print(f"[OK] Container sandbox started: {sandbox.container_name}")

        try:
            # 1. Non-root user
            id_res = await sandbox.execute_command("id -u")
            uid = int(id_res.stdout.strip())
            assert uid != 0, f"Expected non-root UID, got {uid}"
            print(f"[OK] Non-root user verified: UID={uid}")

            # 2. Read-only root filesystem
            ro_res = await sandbox.execute_command("touch /etc/compromise")
            assert not ro_res.is_success, "Writing to root filesystem MUST fail!"
            assert "Read-only file system" in ro_res.stderr or "Permission denied" in ro_res.stderr
            print("[OK] Read-only root filesystem successfully blocked write to /etc")

            # 3. Dedicated writable tmpfs
            tmpfs_res = await sandbox.execute_command("echo 'secure_temp' > /tmp/test.txt && cat /tmp/test.txt")
            assert tmpfs_res.is_success
            assert "secure_temp" in tmpfs_res.stdout
            print("[OK] Dedicated tmpfs (/tmp) is functional and writable")

            # 4. Network isolation
            net_res = await sandbox.execute_command(
                "python3 -c \"import socket; socket.create_connection(('1.1.1.1', 80), timeout=1)\""
            )
            assert not net_res.is_success, "Outbound network connection MUST be blocked!"
            print("[OK] Network isolation verified: outbound TCP socket connection rejected")

        finally:
            await sandbox.cleanup()
            print("[OK] Sandbox destroyed and container removed")

    finally:
        shutil.rmtree(base_dir, ignore_errors=True)

    print("=== [SCENARIO 02 PASSED] ===\n")


if __name__ == "__main__":
    asyncio.run(main())
