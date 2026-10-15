"""Data schemas and configurations for isolated sandbox execution."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4


@dataclass
class ExecutionResult:
    """Outcome of command execution inside the isolated sandbox."""

    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False
    output_truncated: bool = False
    command: str = ""

    @property
    def is_success(self) -> bool:
        """True if the command completed with exit code 0 without timing out."""
        return self.exit_code == 0 and not self.timed_out


@dataclass
class ContainerConfig:
    """Hardware and security isolation constraints for sandbox containers."""

    image: str = "syntra-sandbox:latest"
    cpu_limit: float = 1.0
    memory_limit: str = "512m"
    pids_limit: int = 100
    tmpfs_size: str = "64m"
    read_only_root: bool = True
    network_mode: str = "none"
    user: str = ""
    timeout_seconds: int = 120
    max_output_bytes: int = 1_048_576  # 1MB
    workspace_mount_path: str = "/workspace"
    workspace_read_only: bool = False
    seccomp_profile: str | None = None

    def get_effective_user(self) -> str:
        """Determine non-root user UID:GID for the container."""
        if self.user:
            return self.user
        # By default use host UID:GID if non-zero, otherwise default to unprivileged UID 1000
        try:
            uid = os.getuid()
            gid = os.getgid()
            if uid != 0:
                return f"{uid}:{gid}"
        except AttributeError:
            pass
        return "1000:1000"


@dataclass
class SandboxLease:
    """Active lease tracking an ephemeral worktree and container."""

    sandbox_id: UUID = field(default_factory=uuid4)
    task_id: UUID = field(default_factory=uuid4)
    attempt_number: int = 1
    worktree_path: Path = field(default_factory=Path)
    branch_name: str = ""
    container_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
