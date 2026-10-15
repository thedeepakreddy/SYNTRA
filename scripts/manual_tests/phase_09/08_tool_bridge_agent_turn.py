#!/usr/bin/env python3
"""Manual Test 08: Agent Tool Bridge Operations.

Verifies:
1. Agent tools interact seamlessly with the sandbox via SandboxToolBridge.
2. list_directory scoped strictly to worktree.
3. write_file creates parent directories and writes contents safely.
4. read_file verifies content integrity.
5. execute_command runs test assertions inside container.
6. get_unified_diff captures all changes cleanly.
"""

import asyncio
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from syntra.sandbox.provider import DockerSandboxProvider
from syntra.sandbox.tool_bridge import SandboxToolBridge


async def main() -> None:
    print("=== [PHASE 9 SCENARIO 08] Agent Tool Bridge Operations ===")

    base_dir = Path(__file__).parent.parent.parent.parent / ".syntra" / "test_sandboxes" / f"sc08_{uuid4().hex[:6]}"
    base_dir.mkdir(parents=True, exist_ok=True)
    repo_dir = base_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
        (repo_dir / "README.md").write_text("# Project\n", encoding="utf-8")
        (repo_dir / "src").mkdir()
        (repo_dir / "src" / "math_lib.py").write_text("def mul(a, b):\n    return 0\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True, capture_output=True)
        base_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True
        ).stdout.strip()

        provider = DockerSandboxProvider()
        sandbox = await provider.create_sandbox(uuid4(), 1, repo_dir, base_commit)

        try:
            bridge = SandboxToolBridge(sandbox)

            # 1. Directory listing
            entries = bridge.list_directory(".")
            assert "README.md" in entries
            assert "src" in entries
            print(f"[OK] Directory listing verified: {entries}")

            # 2. Write file
            bridge.write_file("src/math_lib.py", "def mul(a, b):\n    return a * b\n")
            bridge.write_file("tests/test_math.py", "from src.math_lib import mul\nassert mul(6, 7) == 42\n")
            print("[OK] Wrote files via tool bridge: src/math_lib.py, tests/test_math.py")

            # 3. Read back
            content = bridge.read_file("src/math_lib.py")
            assert "return a * b" in content
            print("[OK] Read back file content verified")

            # 4. Execute test inside container
            res = await bridge.execute_command("PYTHONPATH=. python3 tests/test_math.py")
            assert res.is_success, f"Test execution failed: {res.stderr}"
            print("[OK] Executed test assertions successfully inside container")

            # 5. Extract unified diff
            diff = await bridge.get_unified_diff()
            assert "+++ b/src/math_lib.py" in diff
            assert "+    return a * b" in diff
            assert "+++ b/tests/test_math.py" in diff
            print("[OK] Unified diff verified with modified and new files")

        finally:
            await sandbox.cleanup()
            print("[OK] Sandbox cleaned up")

    finally:
        shutil.rmtree(base_dir, ignore_errors=True)

    print("=== [SCENARIO 08 PASSED] ===\n")


if __name__ == "__main__":
    asyncio.run(main())
