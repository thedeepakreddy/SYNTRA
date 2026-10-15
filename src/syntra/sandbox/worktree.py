"""Ephemeral Git worktree management for isolated task execution.

Every task attempt provisions a dedicated Git worktree branched from target commit/branch,
enforcing complete isolation from the host repository and enabling clean unified diff extraction.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from pathlib import Path
from uuid import UUID

from syntra.core.exceptions import SandboxError, SandboxSecurityViolationError

logger = logging.getLogger(__name__)


class GitWorktreeManager:
    """Manages ephemeral git worktrees for isolated task execution."""

    def __init__(self, repository_path: str | Path, worktrees_dir: str | Path | None = None) -> None:
        self.repo_path = Path(repository_path).resolve()
        if not (self.repo_path / ".git").exists():
            raise SandboxError(f"Target repository {self.repo_path} is not a valid git repository (missing .git).")

        self.worktrees_dir = (
            Path(worktrees_dir).resolve() if worktrees_dir else self.repo_path / ".syntra" / "sandboxes"
        )
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe(self, worktree_path: Path, relative_path: str | Path) -> Path:
        """Resolve a path within the worktree and verify it cannot traverse outside."""
        resolved_worktree = worktree_path.resolve()
        target = (resolved_worktree / relative_path).resolve()
        try:
            target.relative_to(resolved_worktree)
        except ValueError:
            raise SandboxSecurityViolationError(
                f"Path traversal detected: '{relative_path}' resolves outside worktree root '{resolved_worktree}'"
            )
        return target

    async def _run_git(self, *args: str, cwd: Path | None = None) -> tuple[int, str, str]:
        """Execute a git command with timeout and output capture."""
        target_cwd = cwd or self.repo_path
        proc = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=str(target_cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=30.0)
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
            raise SandboxError(f"Git command timed out: git {' '.join(args)}")

    async def create_worktree(
        self,
        task_id: UUID,
        attempt_number: int,
        base_commit: str = "HEAD",
    ) -> tuple[Path, str]:
        """Create an ephemeral worktree branched from base_commit."""
        branch_name = f"syntra/task-{task_id}-{attempt_number}"
        worktree_path = self.worktrees_dir / f"wt_{task_id}_{attempt_number}"

        # Clean up any leftover branch or path
        if worktree_path.exists():
            shutil.rmtree(worktree_path, ignore_errors=True)
            await self._run_git("worktree", "prune")

        # Delete existing branch if lingering
        await self._run_git("branch", "-D", branch_name)

        # Create worktree
        code, stdout, stderr = await self._run_git(
            "worktree", "add", "-b", branch_name, str(worktree_path), base_commit
        )
        if code != 0:
            raise SandboxError(f"Failed to create git worktree at {worktree_path}: {stderr or stdout}")

        # Ensure permissions are open so container user (UID != host UID) can read and write
        try:
            os.chmod(worktree_path, 0o777)
            for root, dirs, files in os.walk(worktree_path):
                for d in dirs:
                    os.chmod(os.path.join(root, d), 0o777)
                for f in files:
                    try:
                        os.chmod(os.path.join(root, f), 0o666)
                    except OSError:
                        pass
        except OSError as e:
            logger.warning("Failed to chmod worktree files: %s", e)

        return worktree_path, branch_name

    async def get_unified_diff(self, worktree_path: Path, base_commit: str = "HEAD") -> str:
        """Extract a clean unified diff of all modifications made in the worktree."""
        if not worktree_path.exists():
            return ""

        # Mark all untracked files with intent-to-add so they appear in git diff
        await self._run_git("add", "-N", ".", cwd=worktree_path)

        code, stdout, stderr = await self._run_git(
            "diff", "--no-ext-diff", "--no-textconv", "--binary", "-u", base_commit, cwd=worktree_path
        )
        if code != 0:
            logger.warning("git diff returned code %d: %s", code, stderr)
            # Fallback to diff against HEAD
            code, stdout, _ = await self._run_git("diff", "-u", "HEAD", cwd=worktree_path)

        return stdout

    async def remove_worktree(self, worktree_path: Path, branch_name: str | None = None) -> None:
        """Cleanly remove worktree, prune references, and delete ephemeral branch."""
        if worktree_path.exists():
            await self._run_git("worktree", "remove", "--force", str(worktree_path))

        await self._run_git("worktree", "prune")

        if branch_name:
            await self._run_git("branch", "-D", branch_name)

        # Guarantee filesystem cleanup
        if worktree_path.exists():
            shutil.rmtree(worktree_path, ignore_errors=True)

    def read_file(self, worktree_path: Path, relative_path: str) -> str:
        """Read a file within the worktree with strict path traversal checking."""
        target = self._resolve_safe(worktree_path, relative_path)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {relative_path}")
        return target.read_text(encoding="utf-8", errors="replace")

    def write_file(self, worktree_path: Path, relative_path: str, content: str) -> int:
        """Write a file within the worktree with strict path traversal checking."""
        target = self._resolve_safe(worktree_path, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return len(content.encode("utf-8"))
