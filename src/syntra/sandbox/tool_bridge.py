"""Bidirectional tool bridge enabling agent tools to execute strictly within the sandbox."""

from __future__ import annotations

import json
import logging
import shlex

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

    async def isolated_file_operation(self, operation: str, relative_path: str, content: str = "") -> str:
        """Model-controlled file operations execute in the container, including path resolution.

        Host-side Phase 9 helpers remain available for trusted fixture preparation.
        """
        script = (
            "import json,pathlib,sys; a=json.loads(sys.argv[1]); root=pathlib.Path.cwd().resolve(); "
            "p=(root/a['path']).resolve(); "
            "assert p.is_relative_to(root), 'Path traversal denied'; "
            "assert not any(x=='.git' or x=='.env' for x in p.relative_to(root).parts), 'Protected path'; "
            "op=a['op']; "
            "\nif op=='read':\n assert p.stat().st_size<=100000, 'File too large'\n print(p.read_text())"
            "\nelif op=='write':\n p.parent.mkdir(parents=True,exist_ok=True)\n p.write_text(a['content'])\n print('written')"
            "\nelif op=='list':\n print(json.dumps(sorted(x.name for x in p.iterdir() if x.name not in {'.git','.env'})[:200]))"
            "\nelse: raise ValueError('Unknown file operation')"
        )
        payload = json.dumps({"op": operation, "path": relative_path, "content": content})
        result = await self.execute_command("python -I -c " + shlex.quote(script) + " " + shlex.quote(payload))
        if not result.is_success:
            raise ValueError(result.stderr[:1000])
        return result.stdout
