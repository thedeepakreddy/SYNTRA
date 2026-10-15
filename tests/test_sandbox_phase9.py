"""Comprehensive tests for Phase 9: Isolated Sandbox Workers and Git Worktree Execution."""

from __future__ import annotations

import asyncio
import shutil
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from syntra.core.exceptions import SandboxSecurityViolationError
from syntra.domain.entities import AttemptState
from syntra.sandbox.models import ContainerConfig
from syntra.sandbox.provider import DockerSandboxProvider
from syntra.sandbox.tool_bridge import SandboxToolBridge
from syntra.sandbox.worker_bridge import SandboxWorkerAdapter
from syntra.sandbox.worktree import GitWorktreeManager
from syntra.scheduling.models import TaskDispatchPayload


@pytest.fixture(scope="session")
def docker_available() -> bool:
    """Check if Docker daemon is accessible for live container tests."""
    try:
        import subprocess

        res = subprocess.run(["docker", "info"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        return res.returncode == 0
    except Exception:
        return False


@pytest.fixture
def test_git_repo():
    """Fixture initializing a clean Git repository for testing worktree isolation."""
    base_test_dir = Path(__file__).parent.parent / ".syntra" / "test_sandboxes" / f"repo_{uuid4().hex[:8]}"
    base_test_dir.mkdir(parents=True, exist_ok=True)
    repo_dir = base_test_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    import subprocess

    subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test Runner"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@syntra.local"], cwd=repo_dir, check=True, capture_output=True)

    # Initial commit
    (repo_dir / "README.md").write_text("# Test Repo\n", encoding="utf-8")
    (repo_dir / "src").mkdir()
    (repo_dir / "src" / "service.py").write_text("def run():\n    return False\n", encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True, capture_output=True)

    head_res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True)
    base_commit = head_res.stdout.strip()

    yield repo_dir, base_commit

    # Teardown
    shutil.rmtree(base_test_dir, ignore_errors=True)


# =============================================================================
# 1. GitWorktreeManager Tests
# =============================================================================


@pytest.mark.asyncio
async def test_worktree_creation_and_removal(test_git_repo):
    """Verify that GitWorktreeManager provisions ephemeral worktree and cleans it up."""
    repo_dir, base_commit = test_git_repo
    wt_manager = GitWorktreeManager(repo_dir)

    task_id = uuid4()
    attempt = 1

    wt_path, branch_name = await wt_manager.create_worktree(task_id, attempt, base_commit)
    assert wt_path.exists()
    assert (wt_path / "README.md").exists()
    assert branch_name == f"syntra/task-{task_id}-{attempt}"

    # Verify path traversal protection
    with pytest.raises(SandboxSecurityViolationError):
        wt_manager.read_file(wt_path, "../../etc/passwd")

    with pytest.raises(SandboxSecurityViolationError):
        wt_manager.write_file(wt_path, "../outside.txt", "attack")

    # Safe write and read
    wt_manager.write_file(wt_path, "src/service.py", "def run():\n    return True\n")
    content = wt_manager.read_file(wt_path, "src/service.py")
    assert "return True" in content

    # Unified diff extraction
    diff = await wt_manager.get_unified_diff(wt_path, base_commit)
    assert "-    return False" in diff
    assert "+    return True" in diff

    # Clean removal
    await wt_manager.remove_worktree(wt_path, branch_name)
    assert not wt_path.exists()


@pytest.mark.asyncio
async def test_worktree_diff_includes_untracked_files(test_git_repo):
    """Verify that newly created untracked files are captured in the unified diff."""
    repo_dir, base_commit = test_git_repo
    wt_manager = GitWorktreeManager(repo_dir)

    task_id = uuid4()
    wt_path, branch_name = await wt_manager.create_worktree(task_id, 1, base_commit)

    try:
        wt_manager.write_file(wt_path, "src/new_module.py", "# New module\n")
        diff = await wt_manager.get_unified_diff(wt_path, base_commit)
        assert "+++ b/src/new_module.py" in diff
        assert "+# New module" in diff
    finally:
        await wt_manager.remove_worktree(wt_path, branch_name)


# =============================================================================
# 2. Container Security & Isolation Tests (Live Docker via Colima)
# =============================================================================


@pytest.mark.asyncio
async def test_docker_sandbox_provider_availability(docker_available):
    """Verify Docker provider availability detection."""
    provider = DockerSandboxProvider()
    avail = await provider.is_available()
    assert avail == docker_available


@pytest.mark.asyncio
async def test_container_sandbox_lifecycle_and_security(test_git_repo, docker_available):
    """Verify container sandbox lifecycle, read-only root, non-root user, and network isolation."""
    if not docker_available:
        pytest.skip("Docker container runtime is not available.")

    repo_dir, base_commit = test_git_repo
    provider = DockerSandboxProvider()

    task_id = uuid4()
    attempt = 1

    sandbox = await provider.create_sandbox(
        task_id=task_id,
        attempt_number=attempt,
        repository_path=repo_dir,
        base_commit=base_commit,
    )
    assert sandbox.is_running

    try:
        # 1. Non-root user verification
        id_res = await sandbox.execute_command("id -u")
        assert id_res.is_success
        uid = int(id_res.stdout.strip())
        assert uid != 0, "Container MUST NOT execute as root (UID 0)"

        # 2. Read-only root filesystem enforcement: writing to /etc must fail
        ro_res = await sandbox.execute_command("touch /etc/forbidden_file")
        assert not ro_res.is_success
        assert "Read-only file system" in ro_res.stderr or "Permission denied" in ro_res.stderr

        # 3. Dedicated writable tmpfs: writing to /tmp must succeed
        tmpfs_res = await sandbox.execute_command("touch /tmp/test_tmpfs && echo 'tmpfs_ok' > /tmp/test_tmpfs")
        assert tmpfs_res.is_success

        # 4. Network isolation: outbound networking must fail
        net_res = await sandbox.execute_command(
            "python3 -c \"import urllib.request; urllib.request.urlopen('http://google.com', timeout=1)\""
        )
        assert not net_res.is_success

        # 5. Worktree modification inside container
        edit_res = await sandbox.execute_command("echo '# Container edit' >> README.md")
        assert edit_res.is_success

        diff = await sandbox.get_unified_diff()
        assert "+# Container edit" in diff

    finally:
        await sandbox.cleanup()
        assert not sandbox.is_running


@pytest.mark.asyncio
async def test_container_timeout_enforcement(test_git_repo, docker_available):
    """Verify that runaway commands are killed when exceeding timeout."""
    if not docker_available:
        pytest.skip("Docker container runtime is not available.")

    repo_dir, base_commit = test_git_repo
    provider = DockerSandboxProvider()

    task_id = uuid4()
    sandbox = await provider.create_sandbox(
        task_id=task_id,
        attempt_number=1,
        repository_path=repo_dir,
        base_commit=base_commit,
    )

    try:
        # Run command with 2-second timeout
        res = await sandbox.execute_command("sleep 10", timeout_seconds=2)
        assert res.timed_out
        assert not res.is_success
        assert "timed out after 2 seconds" in res.stderr
    finally:
        await sandbox.cleanup()


@pytest.mark.asyncio
async def test_container_output_truncation(test_git_repo, docker_available):
    """Verify that command output exceeding max_output_bytes is truncated with a warning."""
    if not docker_available:
        pytest.skip("Docker container runtime is not available.")

    repo_dir, base_commit = test_git_repo
    # Set a tiny output limit for fast verification
    tiny_config = ContainerConfig(max_output_bytes=2048)
    provider = DockerSandboxProvider(default_config=tiny_config)

    task_id = uuid4()
    sandbox = await provider.create_sandbox(
        task_id=task_id,
        attempt_number=1,
        repository_path=repo_dir,
        base_commit=base_commit,
        config=tiny_config,
    )

    try:
        # Generate 10KB of text
        res = await sandbox.execute_command("python3 -c \"print('A' * 10000)\"")
        assert res.is_success
        assert res.output_truncated
        assert "[TRUNCATED at 2048 bytes]" in res.stdout
    finally:
        await sandbox.cleanup()


# =============================================================================
# 3. SandboxToolBridge Tests
# =============================================================================


@pytest.mark.asyncio
async def test_sandbox_tool_bridge(test_git_repo, docker_available):
    """Verify agent tool interactions through SandboxToolBridge."""
    if not docker_available:
        pytest.skip("Docker container runtime is not available.")

    repo_dir, base_commit = test_git_repo
    provider = DockerSandboxProvider()

    task_id = uuid4()
    sandbox = await provider.create_sandbox(
        task_id=task_id,
        attempt_number=1,
        repository_path=repo_dir,
        base_commit=base_commit,
    )

    try:
        bridge = SandboxToolBridge(sandbox)

        # Directory listing
        files = bridge.list_directory(".")
        assert "README.md" in files
        assert "src" in files

        # Write and read
        bridge.write_file("src/calculator.py", "def add(a, b):\n    return a + b\n")
        read_back = bridge.read_file("src/calculator.py")
        assert "return a + b" in read_back

        # Execute test inside container
        cmd_res = await bridge.execute_command('python3 -c "from src.calculator import add; assert add(2, 3) == 5"')
        assert cmd_res.is_success

        # Diff
        diff = await bridge.get_unified_diff()
        assert "+++ b/src/calculator.py" in diff
    finally:
        await sandbox.cleanup()


# =============================================================================
# 4. SandboxWorkerAdapter Tests
# =============================================================================


@pytest.mark.asyncio
async def test_sandbox_worker_adapter_success(test_git_repo, docker_available):
    """Verify SandboxWorkerAdapter end-to-end task execution in container with diff extraction."""
    if not docker_available:
        pytest.skip("Docker container runtime is not available.")

    repo_dir, base_commit = test_git_repo
    adapter = SandboxWorkerAdapter(repository_path=repo_dir, base_commit=base_commit)

    task_id = uuid4()
    dispatch = TaskDispatchPayload(
        task_id=task_id,
        mission_id=uuid4(),
        org_id=uuid4(),
        attempt_number=1,
        assigned_role="backend_engineer",
        fencing_token=1,
        lease_expires_at=datetime.now(UTC),
        specification="Fix service.py to return True and verify with python assertion",
    )

    result = await adapter.execute_task(
        dispatch=dispatch,
        code_changes={"src/service.py": "def run():\n    return True\n"},
        commands_to_run=['python3 -c "from src.service import run; assert run() is True"'],
        tokens_consumed=600,
        cost_usd=Decimal("0.001200"),
    )

    assert result.status == AttemptState.SUCCEEDED
    assert result.exit_code == 0
    assert result.unified_diff is not None
    assert "-    return False" in result.unified_diff
    assert "+    return True" in result.unified_diff
    assert len(result.produced_artifact_ids) > 0
    assert result.actual_prompt_tokens == 300
    assert result.actual_completion_tokens == 300


@pytest.mark.asyncio
async def test_sandbox_worker_adapter_failure(test_git_repo, docker_available):
    """Verify SandboxWorkerAdapter failure capture and cleanup when command fails."""
    if not docker_available:
        pytest.skip("Docker container runtime is not available.")

    repo_dir, base_commit = test_git_repo
    adapter = SandboxWorkerAdapter(repository_path=repo_dir, base_commit=base_commit)

    task_id = uuid4()
    dispatch = TaskDispatchPayload(
        task_id=task_id,
        mission_id=uuid4(),
        org_id=uuid4(),
        attempt_number=1,
        assigned_role="qa_engineer",
        fencing_token=1,
        lease_expires_at=datetime.now(UTC),
        specification="Run failing assertion",
    )

    result = await adapter.execute_task(
        dispatch=dispatch,
        commands_to_run=["python3 -c \"assert 1 == 2, 'Intentional Failure'\""],
    )

    assert result.status == AttemptState.FAILED
    assert result.exit_code != 0
    assert "Intentional Failure" in str(result.error_message)


@pytest.mark.asyncio
async def test_concurrent_container_sandboxes(test_git_repo, docker_available):
    """Verify that multiple container sandboxes can execute in parallel without cross-contamination."""
    if not docker_available:
        pytest.skip("Docker container runtime is not available.")

    repo_dir, base_commit = test_git_repo
    adapter_1 = SandboxWorkerAdapter(repository_path=repo_dir, worker_id="worker-01", base_commit=base_commit)
    adapter_2 = SandboxWorkerAdapter(repository_path=repo_dir, worker_id="worker-02", base_commit=base_commit)

    task_1 = uuid4()
    task_2 = uuid4()

    dispatch_1 = TaskDispatchPayload(
        task_id=task_1,
        mission_id=uuid4(),
        org_id=uuid4(),
        attempt_number=1,
        assigned_role="backend_engineer",
        fencing_token=1,
        lease_expires_at=datetime.now(UTC),
        specification="Add module 1",
    )
    dispatch_2 = TaskDispatchPayload(
        task_id=task_2,
        mission_id=uuid4(),
        org_id=uuid4(),
        attempt_number=1,
        assigned_role="frontend_engineer",
        fencing_token=1,
        lease_expires_at=datetime.now(UTC),
        specification="Add module 2",
    )

    # Execute both in parallel
    res_1, res_2 = await asyncio.gather(
        adapter_1.execute_task(
            dispatch=dispatch_1,
            code_changes={"src/module_1.py": "def m1(): return 1\n"},
            commands_to_run=['python3 -c "from src.module_1 import m1; assert m1() == 1"'],
        ),
        adapter_2.execute_task(
            dispatch=dispatch_2,
            code_changes={"src/module_2.py": "def m2(): return 2\n"},
            commands_to_run=['python3 -c "from src.module_2 import m2; assert m2() == 2"'],
        ),
    )

    assert res_1.status == AttemptState.SUCCEEDED
    assert res_2.status == AttemptState.SUCCEEDED
    assert res_1.unified_diff is not None
    assert res_2.unified_diff is not None
    assert "module_1.py" in res_1.unified_diff
    assert "module_2.py" not in res_1.unified_diff
    assert "module_2.py" in res_2.unified_diff
    assert "module_1.py" not in res_2.unified_diff


@pytest.mark.asyncio
async def test_container_resource_limits(test_git_repo, docker_available):
    """Verify that memory and PID limits are enforced inside the container."""
    if not docker_available:
        pytest.skip("Docker container runtime is not available.")

    repo_dir, base_commit = test_git_repo
    # Very small memory limit to trigger memory constraint if exceeded
    config = ContainerConfig(memory_limit="64m", pids_limit=30)
    provider = DockerSandboxProvider(default_config=config)

    task_id = uuid4()
    sandbox = await provider.create_sandbox(
        task_id=task_id,
        attempt_number=1,
        repository_path=repo_dir,
        base_commit=base_commit,
        config=config,
    )

    try:
        # Verify container runs normally within limits
        res = await sandbox.execute_command('python3 -c "x = [i for i in range(1000)]; print(len(x))"')
        assert res.is_success
        assert "1000" in res.stdout
    finally:
        await sandbox.cleanup()
