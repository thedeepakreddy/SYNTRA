"""Tests for SYNTRA sandbox module."""

import pytest

from syntra.core.exceptions import SandboxError, SandboxSecurityViolationError
from syntra.sandbox import (
    CommandSafetyValidator,
    FilePatcher,
    SandboxRunner,
    WorkspaceManager,
)


def test_safety_validator_rejects_dangerous():
    with pytest.raises(SandboxSecurityViolationError):
        CommandSafetyValidator.validate_command("rm -rf /")

    with pytest.raises(SandboxSecurityViolationError):
        CommandSafetyValidator.validate_command("rm -rf /etc/hosts")

    with pytest.raises(SandboxSecurityViolationError):
        CommandSafetyValidator.validate_command(":(){ :|:& };:")

    # Safe commands should pass
    CommandSafetyValidator.validate_command("pytest tests/")
    CommandSafetyValidator.validate_command("git status")


def test_safety_validator_sanitizes_env():
    dirty_env = {
        "PATH": "/usr/bin",
        "GEMINI_API_KEY": "secret_key_123",
        "AWS_SECRET_ACCESS_KEY": "aws_secret",
        "APP_ENV": "development",
    }
    clean = CommandSafetyValidator.sanitize_env(dirty_env)
    assert "GEMINI_API_KEY" not in clean
    assert "AWS_SECRET_ACCESS_KEY" not in clean
    assert clean["PATH"] == "/usr/bin"
    assert clean["APP_ENV"] == "development"


@pytest.mark.asyncio
async def test_workspace_manager(tmp_path):
    ws = WorkspaceManager(tmp_path)

    # Write file
    written = await ws.write_file("src/main.py", "def hello():\n    return 'world'\n")
    assert written > 0
    assert ws.file_exists("src/main.py")

    # Read file
    content = ws.read_file("src/main.py")
    assert "return 'world'" in content

    # Search code
    search_results = ws.search_code("return 'world'")
    assert len(search_results) == 1
    assert search_results[0]["file"] == "src/main.py"
    assert search_results[0]["line_number"] == 2

    # Tree & list files
    files = ws.list_files()
    assert "src/main.py" in files
    tree = ws.get_tree()
    assert tmp_path.name + "/" in tree

    # Path traversal defense
    with pytest.raises(SandboxSecurityViolationError):
        ws.read_file("../../etc/passwd")

    with pytest.raises(SandboxSecurityViolationError):
        await ws.write_file("../outside.txt", "hack")


def test_file_patcher():
    original = "line 1\nline 2 target\nline 3\n"
    modified = FilePatcher.replace_content(original, "line 2 target", "line 2 replaced")
    assert "line 2 replaced" in modified

    with pytest.raises(SandboxError):
        FilePatcher.replace_content(original, "nonexistent", "new")

    diff = FilePatcher.generate_diff(original, modified, "sample.txt")
    assert "-line 2 target" in diff
    assert "+line 2 replaced" in diff

    stats = FilePatcher.calculate_stats(diff)
    assert stats["additions"] == 1
    assert stats["deletions"] == 1


@pytest.mark.asyncio
async def test_sandbox_runner_execution(tmp_path):
    runner = SandboxRunner(cwd=tmp_path)

    # Safe execution
    result = await runner.run("echo 'SYNTRA Sandbox Test'")
    assert result.is_success
    assert "SYNTRA Sandbox Test" in result.stdout

    # Dangerous command rejection
    with pytest.raises(SandboxSecurityViolationError):
        await runner.run("rm -rf /")

    # Timeout handling
    timeout_result = await runner.run("sleep 3", timeout=0.1)
    assert timeout_result.timed_out
    assert not timeout_result.is_success
