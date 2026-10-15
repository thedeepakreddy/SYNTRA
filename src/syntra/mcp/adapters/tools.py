"""Safe, boundary-scoped tool adapters for workspace filesystem, git operations, and artifacts."""

import fnmatch
import json
import subprocess
from pathlib import Path
from typing import Any
from uuid import UUID

from mcp.server.mcpserver import MCPServer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from syntra.mcp.policy import ScopeViolationError
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork


def resolve_safe_path(workspace_root: Path, relative_path: str) -> Path:
    """Resolve a path and ensure it is strictly contained within the workspace boundary."""
    root = workspace_root.resolve()
    if relative_path.startswith("/") or relative_path.startswith("\\") or Path(relative_path).is_absolute():
        raise ScopeViolationError(
            f"Absolute path '{relative_path}' is forbidden. All paths must be relative to the workspace boundary."
        )
    target = (root / relative_path).resolve()
    if not target.is_relative_to(root):
        raise ScopeViolationError(
            f"Path traversal detected: Path '{relative_path}' resolves to '{target}', escaping root '{root}'."
        )
    return target


class ScopedFilesystemTools:
    """Provides safe filesystem primitives with canonical path confinement."""

    @staticmethod
    def read_scoped(workspace_root: Path, relative_path: str, max_bytes: int = 10 * 1024 * 1024) -> str:
        """Safely read content from a file inside the scoped workspace root."""
        path = resolve_safe_path(workspace_root, relative_path)
        if not path.exists():
            raise FileNotFoundError(f"File '{relative_path}' does not exist inside workspace.")
        if path.is_dir():
            raise IsADirectoryError(f"Target '{relative_path}' is a directory, not a file.")

        size = path.stat().st_size
        if size > max_bytes:
            raise ValueError(f"File '{relative_path}' size ({size} bytes) exceeds maximum limit ({max_bytes} bytes).")

        return path.read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def list_scoped(workspace_root: Path, relative_path: str = ".") -> list[dict[str, Any]]:
        """Safely list entries within a directory inside the workspace root."""
        dir_path = resolve_safe_path(workspace_root, relative_path)
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory '{relative_path}' does not exist.")
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Target '{relative_path}' is not a directory.")

        results = []
        for entry in sorted(dir_path.iterdir()):
            results.append(
                {
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size_bytes": entry.stat().st_size if entry.is_file() else None,
                }
            )
        return results

    @staticmethod
    def search_scoped(
        workspace_root: Path,
        pattern: str,
        extension_filter: str | None = None,
        max_matches: int = 100,
    ) -> list[str]:
        """Search for filenames or glob patterns strictly confined to workspace root."""
        root = workspace_root.resolve()
        matches = []
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            if extension_filter and not rel.endswith(extension_filter):
                continue
            if fnmatch.fnmatch(rel, pattern) or pattern in rel:
                matches.append(rel)
                if len(matches) >= max_matches:
                    break
        return matches


class ScopedGitTools:
    """Safe read-only Git inspection tools within the workspace root."""

    @staticmethod
    def status(workspace_root: Path) -> str:
        """Execute safe read-only git status --porcelain in the workspace root."""
        root = workspace_root.resolve()
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if res.returncode != 0:
            return f"Git status failed (code {res.returncode}): {res.stderr.strip()}"
        return res.stdout if res.stdout else "Clean working directory"

    @staticmethod
    def diff(workspace_root: Path, staged: bool = False) -> str:
        """Execute safe read-only git diff in the workspace root."""
        root = workspace_root.resolve()
        cmd = ["git", "diff", "--no-pager"]
        if staged:
            cmd.append("--staged")
        res = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if res.returncode != 0:
            return f"Git diff failed (code {res.returncode}): {res.stderr.strip()}"
        return res.stdout if res.stdout else "No differences found"


def create_workspace_mcp_server(
    workspace_root: Path,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> MCPServer:
    """Construct an MCP Server exposing safe workspace filesystem, git, and artifact tools."""
    server = MCPServer("workspace", version="0.1.0")

    @server.tool(
        name="filesystem.read_scoped",
        description="Read file content strictly confined within the assigned workspace boundary.",
    )
    def read_scoped(relative_path: str) -> str:
        return ScopedFilesystemTools.read_scoped(workspace_root, relative_path)

    @server.tool(
        name="filesystem.list_scoped",
        description="List files and directories within a scoped workspace path.",
    )
    def list_scoped(relative_path: str = ".") -> str:
        entries = ScopedFilesystemTools.list_scoped(workspace_root, relative_path)
        return json.dumps(entries, indent=2)

    @server.tool(
        name="filesystem.search_scoped",
        description="Search for files matching pattern or extension strictly inside workspace.",
    )
    def search_scoped(pattern: str, extension_filter: str | None = None) -> str:
        matches = ScopedFilesystemTools.search_scoped(workspace_root, pattern, extension_filter)
        return json.dumps(matches, indent=2)

    @server.tool(
        name="git.status",
        description="Inspect git working tree status within workspace root.",
    )
    def git_status() -> str:
        return ScopedGitTools.status(workspace_root)

    @server.tool(
        name="git.diff",
        description="Inspect git diff within workspace root.",
    )
    def git_diff(staged: bool = False) -> str:
        return ScopedGitTools.diff(workspace_root, staged=staged)

    @server.tool(
        name="artifact.read_metadata",
        description="Read metadata and cryptographic checksum for a stored artifact.",
    )
    async def read_metadata(artifact_id: str) -> str:
        if not session_factory:
            return json.dumps({"error": "Persistence not available for artifact metadata"})
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            res = await uow.artifacts.get_by_id(UUID(artifact_id))
            if not res:
                return json.dumps({"error": f"Artifact {artifact_id} not found."})
            art, ver = res
            return json.dumps(
                {
                    "artifact_id": str(art.id),
                    "name": art.title,
                    "title": art.title,
                    "type": art.type.value if hasattr(art.type, "value") else str(art.type),
                    "version": art.current_version,
                    "sha256_checksum": ver.sha256_checksum if ver else None,
                    "size_bytes": ver.size_bytes if ver else 0,
                },
                indent=2,
            )

    return server
