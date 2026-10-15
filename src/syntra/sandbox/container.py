"""Container sandbox instance managing isolated execution within Docker."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Mapping

from syntra.core.exceptions import (
    SandboxError,
    SandboxSecurityViolationError,
)
from syntra.sandbox.models import ContainerConfig, ExecutionResult, SandboxLease
from syntra.sandbox.safety import CommandSafetyValidator
from syntra.sandbox.worktree import GitWorktreeManager

logger = logging.getLogger(__name__)


class ContainerSandboxInstance:
    """Manages the full lifecycle of an isolated container execution sandbox."""

    def __init__(
        self,
        lease: SandboxLease,
        worktree_manager: GitWorktreeManager,
        config: ContainerConfig | None = None,
        base_commit: str = "HEAD",
        owns_worktree: bool = True,
    ) -> None:
        self.lease = lease
        self.worktree_manager = worktree_manager
        self.config = config or ContainerConfig()
        self.base_commit = base_commit
        self.owns_worktree = owns_worktree
        self.container_name = f"syntra_sandbox_{lease.task_id}_{lease.attempt_number}"
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    async def _run_docker(self, *args: str, timeout: float = 30.0) -> tuple[int, str, str]:
        """Execute a docker CLI command asynchronously."""
        proc = await asyncio.create_subprocess_exec(
            "docker",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return (
                proc.returncode or 0,
                stdout_b.decode("utf-8", errors="replace"),
                stderr_b.decode("utf-8", errors="replace"),
            )
        except TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            raise SandboxError(f"Docker command timed out: docker {' '.join(args)}")

    async def start(self) -> None:
        """Start the isolated container instance with all security constraints applied."""
        # Validate that container does not run as root (UID 0)
        effective_user = self.config.get_effective_user()
        uid_part = effective_user.split(":")[0]
        if uid_part == "0" or uid_part == "root":
            raise SandboxSecurityViolationError(
                f"Prohibited container user: '{effective_user}'. Containers must execute as non-root."
            )

        # Clean up any existing container with same name
        await self._run_docker("rm", "-f", self.container_name)

        docker_args = [
            "run",
            "-d",
            "--name",
            self.container_name,
            "--read-only",
            "--tmpfs",
            f"/tmp:rw,noexec,nosuid,size={self.config.tmpfs_size}",
            "--network",
            self.config.network_mode,
            "--cap-drop",
            "ALL",
            "--user",
            effective_user,
            "--pids-limit",
            str(self.config.pids_limit),
            "--memory",
            self.config.memory_limit,
            "--cpus",
            str(self.config.cpu_limit),
            "-v",
            f"{self.lease.worktree_path}:{self.config.workspace_mount_path}:{'ro' if self.config.workspace_read_only else 'rw'}",
            "-v",
            f"{self.lease.worktree_path / '.git'}:{self.config.workspace_mount_path}/.git:ro",
            "--workdir",
            self.config.workspace_mount_path,
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
        ]

        if self.config.seccomp_profile:
            docker_args.extend(["--security-opt", f"seccomp={self.config.seccomp_profile}"])

        docker_args.extend([self.config.image, "sleep", "infinity"])

        code, stdout, stderr = await self._run_docker(*docker_args)
        if code != 0:
            raise SandboxError(f"Failed to start sandbox container '{self.container_name}': {stderr or stdout}")

        self.lease.container_id = stdout.strip()
        self._is_running = True
        logger.info(
            "Started container sandbox %s (id=%s) for task %s attempt %d",
            self.container_name,
            self.lease.container_id[:12],
            self.lease.task_id,
            self.lease.attempt_number,
        )

    async def execute_command(
        self,
        command: str,
        env: Mapping[str, str] | None = None,
        timeout_seconds: int | None = None,
    ) -> ExecutionResult:
        """Execute a command inside the running sandbox container."""
        if not self._is_running:
            raise SandboxError(f"Cannot execute command: sandbox container '{self.container_name}' is not running.")

        # Command safety check (block dangerous shell constructs)
        CommandSafetyValidator.validate_command(command)

        # Sanitize environment (scrub API keys, secrets, cloud tokens)
        merged_env = dict(env or {})
        safe_env = CommandSafetyValidator.sanitize_env(merged_env)

        exec_timeout = timeout_seconds or self.config.timeout_seconds
        max_bytes = self.config.max_output_bytes

        # Build docker exec command
        exec_args = ["exec"]
        for k, v in safe_env.items():
            # Pass safe environment variables
            exec_args.extend(["-e", f"{k}={v}"])

        # The watchdog runs INSIDE the container, so killing the Docker client
        # cannot leave an unbounded child running in the execution plane.
        watchdog = (
            "import os,signal,subprocess,sys; "
            "p=subprocess.Popen(['sh','-c',sys.argv[1]],start_new_session=True); "
            "\ntry: sys.exit(p.wait(timeout=float(sys.argv[2])))"
            "\nexcept subprocess.TimeoutExpired: os.killpg(p.pid,signal.SIGKILL); p.wait(); sys.exit(124)"
        )
        exec_args.extend([self.container_name, "python", "-I", "-c", watchdog, command, str(exec_timeout)])

        start_time = time.perf_counter()
        proc = await asyncio.create_subprocess_exec(
            "docker",
            *exec_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        timed_out = False
        output_truncated = False
        stdout_str = ""
        stderr_str = ""

        try:

            async def bounded_read(stream: asyncio.StreamReader) -> bytes:
                nonlocal output_truncated
                captured = bytearray()
                while chunk := await stream.read(8192):
                    room = max_bytes - len(captured)
                    captured.extend(chunk[: max(0, room)])
                    if len(chunk) > room:
                        output_truncated = True
                return bytes(captured)

            async def collect() -> tuple[bytes, bytes]:
                assert proc.stdout is not None and proc.stderr is not None
                stdout_b, stderr_b = await asyncio.gather(bounded_read(proc.stdout), bounded_read(proc.stderr))
                await proc.wait()
                return stdout_b, stderr_b

            stdout_b, stderr_b = await asyncio.wait_for(collect(), timeout=exec_timeout + 3)
            exit_code = proc.returncode or 0
            if exit_code == 124:
                timed_out = True
                exit_code = -1
                stderr_b += f"\nExecution timed out after {exec_timeout} seconds.".encode()

            if output_truncated or len(stdout_b) > max_bytes:
                stdout_b = stdout_b[:max_bytes]
                output_truncated = True
                stdout_str = stdout_b.decode("utf-8", errors="replace") + f"\n... [TRUNCATED at {max_bytes} bytes]"
            else:
                stdout_str = stdout_b.decode("utf-8", errors="replace")

            if len(stderr_b) > max_bytes:
                stderr_b = stderr_b[:max_bytes]
                output_truncated = True
                stderr_str = stderr_b.decode("utf-8", errors="replace") + f"\n... [TRUNCATED at {max_bytes} bytes]"
            else:
                stderr_str = stderr_b.decode("utf-8", errors="replace")

        except TimeoutError:
            timed_out = True
            exit_code = -1
            stderr_str = f"Execution timed out after {exec_timeout} seconds."
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            await proc.wait()
            await self._run_docker("kill", self.container_name)
            self._is_running = False

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        return ExecutionResult(
            command=command,
            exit_code=exit_code,
            stdout=stdout_str,
            stderr=stderr_str,
            duration_ms=duration_ms,
            timed_out=timed_out,
            output_truncated=output_truncated,
        )

    def read_file(self, relative_path: str) -> str:
        """Safely read a file within the worktree."""
        return self.worktree_manager.read_file(self.lease.worktree_path, relative_path)

    def write_file(self, relative_path: str, content: str) -> int:
        """Safely write a file within the worktree."""
        return self.worktree_manager.write_file(self.lease.worktree_path, relative_path, content)

    async def get_unified_diff(self) -> str:
        """Extract unified git diff of all modifications made in the sandbox worktree."""
        return await self.worktree_manager.get_unified_diff(self.lease.worktree_path, self.base_commit)

    async def cleanup(self) -> None:
        """Destroy container, prune worktree, and clean up temporary assets."""
        logger.info("Cleaning up container sandbox %s", self.container_name)
        # Force remove container
        try:
            await self._run_docker("rm", "-f", self.container_name, timeout=10.0)
        except Exception as e:
            logger.warning("Error stopping container %s: %s", self.container_name, e)
        finally:
            self._is_running = False

        # Prune and remove ephemeral worktree
        try:
            if self.owns_worktree:
                await self.worktree_manager.remove_worktree(self.lease.worktree_path, self.lease.branch_name)
        except Exception as e:
            logger.warning("Error removing worktree %s: %s", self.lease.worktree_path, e)
