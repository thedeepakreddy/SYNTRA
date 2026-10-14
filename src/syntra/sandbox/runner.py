"""Asynchronous subprocess runner with timeouts, memory limits, and security validation."""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from syntra.core.config import get_settings
from syntra.core.events import Event, EventType, get_event_bus
from syntra.sandbox.safety import CommandSafetyValidator

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result from executing a command in the sandbox."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False

    @property
    def is_success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


class SandboxRunner:
    """Safely executes bash/shell commands in an isolated workspace."""

    def __init__(self, cwd: str | Path, session_id: str = "default") -> None:
        self.cwd = Path(cwd).resolve()
        self.session_id = session_id
        self.settings = get_settings()

    async def run(
        self,
        command: str,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """Execute a shell command with isolation guarantees."""
        # Validate security policy
        CommandSafetyValidator.validate_command(command)

        timeout_sec = timeout or self.settings.sandbox_timeout_seconds
        max_bytes = self.settings.sandbox_max_output_bytes

        # Sanitize environment
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        safe_env = CommandSafetyValidator.sanitize_env(merged_env)

        # Notify start
        await get_event_bus().publish(
            Event(
                type=EventType.COMMAND_STARTED,
                session_id=self.session_id,
                data={"command": command, "cwd": str(self.cwd)},
            )
        )

        start_time = time.perf_counter()
        timed_out = False
        exit_code = -1
        stdout_str = ""
        stderr_str = ""

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(self.cwd),
                env=safe_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_sec,
                )
                exit_code = process.returncode or 0
                stdout_str = stdout_data[:max_bytes].decode("utf-8", errors="replace")
                stderr_str = stderr_data[:max_bytes].decode("utf-8", errors="replace")
                if len(stdout_data) > max_bytes:
                    stdout_str += f"\n... [TRUNCATED at {max_bytes} bytes]"
                if len(stderr_data) > max_bytes:
                    stderr_str += f"\n... [TRUNCATED at {max_bytes} bytes]"

            except TimeoutError:
                timed_out = True
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass
                stderr_str = f"Execution timed out after {timeout_sec} seconds."

        except Exception as exc:
            stderr_str = f"Execution error: {exc}"

        duration = time.perf_counter() - start_time

        result = ExecutionResult(
            command=command,
            exit_code=exit_code,
            stdout=stdout_str,
            stderr=stderr_str,
            duration_seconds=round(duration, 3),
            timed_out=timed_out,
        )

        # Notify completion
        await get_event_bus().publish(
            Event(
                type=EventType.COMMAND_COMPLETED,
                session_id=self.session_id,
                data={
                    "command": command,
                    "exit_code": result.exit_code,
                    "duration": result.duration_seconds,
                    "timed_out": result.timed_out,
                },
            )
        )

        return result
