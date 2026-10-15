"""Live negative acceptance checks against malicious target-repository files."""

from uuid import uuid4

import pytest

from syntra.sandbox.provider import DockerSandboxProvider

pytest_plugins = ["test_sandbox_phase9"]


@pytest.mark.docker
async def test_watchdog_ignores_implementer_subprocess_module(test_git_repo):
    repo, base = test_git_repo
    sandbox = await DockerSandboxProvider().create_sandbox(uuid4(), 1, repo, base)
    try:
        sandbox.write_file("subprocess.py", "import sys\nsys.exit(0)\n")
        result = await sandbox.execute_command("python -I -c 'raise SystemExit(17)'")
        assert result.exit_code == 17
        assert not result.is_success
    finally:
        await sandbox.cleanup()


@pytest.mark.docker
async def test_container_cannot_rewrite_git_link_or_see_host_credentials(test_git_repo, monkeypatch):
    repo, base = test_git_repo
    monkeypatch.setenv("UNLISTED_DATABASE_PASSWORD", "must-never-enter-the-container")
    sandbox = await DockerSandboxProvider().create_sandbox(uuid4(), 1, repo, base)
    try:
        result = await sandbox.execute_command(
            "python -I -c 'import os; assert \"UNLISTED_DATABASE_PASSWORD\" not in os.environ'"
        )
        assert result.is_success
        denied = await sandbox.execute_command(
            'python -I -c \'from pathlib import Path; Path(".git").write_text("malicious")\''
        )
        assert not denied.is_success
        assert (await sandbox.get_unified_diff()) == ""
    finally:
        await sandbox.cleanup()
