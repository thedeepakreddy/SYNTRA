"""Sandbox provider interface and Docker container implementation."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID

from syntra.sandbox.container import ContainerSandboxInstance
from syntra.sandbox.models import ContainerConfig, SandboxLease
from syntra.sandbox.worktree import GitWorktreeManager

logger = logging.getLogger(__name__)


class SandboxProvider(ABC):
    """Abstract interface for provisioning isolated execution sandboxes."""

    @abstractmethod
    async def create_sandbox(
        self,
        task_id: UUID,
        attempt_number: int,
        repository_path: Path,
        base_commit: str = "HEAD",
        config: ContainerConfig | None = None,
    ) -> ContainerSandboxInstance:
        """Provision a clean, isolated sandbox with dedicated Git worktree."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check whether the underlying container runtime is functional and responsive."""
        pass


class DockerSandboxProvider(SandboxProvider):
    """Docker-backed container sandbox provider."""

    def __init__(self, default_config: ContainerConfig | None = None) -> None:
        self.default_config = default_config or ContainerConfig()

    async def is_available(self) -> bool:
        """Verify that the Docker daemon is accessible and responsive."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=5.0)
            return proc.returncode == 0
        except Exception as exc:
            logger.debug("Docker daemon availability check failed: %s", exc)
            return False

    async def create_sandbox(
        self,
        task_id: UUID,
        attempt_number: int,
        repository_path: Path,
        base_commit: str = "HEAD",
        config: ContainerConfig | None = None,
    ) -> ContainerSandboxInstance:
        """Create and start an isolated Docker container with an ephemeral worktree."""
        effective_config = config or self.default_config
        repo_path = Path(repository_path).resolve()
        worktree_manager = GitWorktreeManager(repo_path)

        # 1. Create isolated Git worktree
        worktree_path, branch_name = await worktree_manager.create_worktree(
            task_id=task_id,
            attempt_number=attempt_number,
            base_commit=base_commit,
        )

        lease = SandboxLease(
            task_id=task_id,
            attempt_number=attempt_number,
            worktree_path=worktree_path,
            branch_name=branch_name,
        )

        instance = ContainerSandboxInstance(
            lease=lease,
            worktree_manager=worktree_manager,
            config=effective_config,
            base_commit=base_commit,
        )

        # 2. Start container instance
        try:
            await instance.start()
        except Exception:
            # Guarantee cleanup on startup failure
            await instance.cleanup()
            raise

        return instance
