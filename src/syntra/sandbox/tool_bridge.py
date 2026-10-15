"""Bidirectional tool bridge enabling agent tools to execute strictly within the sandbox."""

from __future__ import annotations

import logging

from syntra.sandbox.container import ContainerSandboxInstance
from syntra.sandbox.models import ExecutionResult

logger = logging.getLogger(__name__)


class SandboxToolBridge:
    """Restricted tool interface for engineering agents to operate within a sandbox.

    All file reads/writes are locked strictly within the ephemeral worktree.
    All shell commands execute strictly inside the isolated container sandbox.
    """

    def __init__(self, sandbox: ContainerSandboxInstance) -> None:
        self.sandbox = sandbox

    def read_file(self, relative_path: str) -> str:
        """Safely read a file within the sandbox worktree."""
        return self.sandbox.read_file(relative_path)

    def write_file(self, relative_path: str, content: str) -> int:
        """Safely write a file within the sandbox worktree."""
        return self.sandbox.write_file(relative_path, content)

    async def execute_command(self, command: str, timeout_seconds: int | None = None) -> ExecutionResult:
        """Execute a shell command inside the isolated container sandbox."""
        return await self.sandbox.execute_command(command, timeout_seconds=timeout_seconds)

    def list_directory(self, relative_path: str = ".") -> list[str]:
        """List files and directories within a relative path of the worktree."""
        worktree_path = self.sandbox.lease.worktree_path
        target = self.sandbox.worktree_manager._resolve_safe(worktree_path, relative_path)
        if not target.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {relative_path}")
        return sorted([p.name for p in target.iterdir() if not p.name.startswith(".git")])

    async def get_unified_diff(self) -> str:
        """Get the current unified diff of changes made in the sandbox."""
        return await self.sandbox.get_unified_diff()
