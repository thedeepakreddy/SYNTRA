"""Isolated workspace management with strict path traversal defenses."""

import os
from pathlib import Path
from syntra.core.events import Event, EventType, get_event_bus
from syntra.core.exceptions import SandboxSecurityViolationError


class WorkspaceManager:
    """Manages an isolated directory workspace for autonomous software engineering."""

    def __init__(self, root_dir: str | Path, session_id: str = "default") -> None:
        self.root_path = Path(root_dir).resolve()
        self.session_id = session_id
        self.root_path.mkdir(parents=True, exist_ok=True)

    def _resolve_safe(self, relative_path: str | Path) -> Path:
        """Resolve a path and guarantee it does not escape root_path."""
        target = (self.root_path / relative_path).resolve()
        try:
            target.relative_to(self.root_path)
        except ValueError:
            raise SandboxSecurityViolationError(
                f"Path traversal attempt detected: '{relative_path}' resolves outside workspace root '{self.root_path}'"
            )
        return target

    def file_exists(self, relative_path: str | Path) -> bool:
        """Check if file exists within workspace."""
        path = self._resolve_safe(relative_path)
        return path.exists() and path.is_file()

    def dir_exists(self, relative_path: str | Path) -> bool:
        """Check if directory exists within workspace."""
        path = self._resolve_safe(relative_path)
        return path.exists() and path.is_dir()

    def read_file(self, relative_path: str | Path, offset_lines: int = 0, limit_lines: int | None = None) -> str:
        """Read text file contents from workspace."""
        path = self._resolve_safe(relative_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found in workspace: {relative_path}")

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        if offset_lines > 0:
            lines = lines[offset_lines:]
        if limit_lines is not None and limit_lines > 0:
            lines = lines[:limit_lines]

        return "".join(lines)

    async def write_file(self, relative_path: str | Path, content: str, overwrite: bool = True) -> int:
        """Write text file within workspace."""
        path = self._resolve_safe(relative_path)
        is_new = not path.exists()

        if path.exists() and not overwrite:
            raise FileExistsError(f"File already exists and overwrite=False: {relative_path}")

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        bytes_written = len(content.encode("utf-8"))

        # Publish event
        ev_type = EventType.FILE_CREATED if is_new else EventType.FILE_MODIFIED
        await get_event_bus().publish(
            Event(
                type=ev_type,
                session_id=self.session_id,
                data={
                    "path": str(path.relative_to(self.root_path)),
                    "bytes": bytes_written,
                },
            )
        )
        return bytes_written

    async def delete_file(self, relative_path: str | Path) -> bool:
        """Delete a file from the workspace."""
        path = self._resolve_safe(relative_path)
        if not path.exists():
            return False

        if path.is_file():
            path.unlink()
        elif path.is_dir():
            import shutil
            shutil.rmtree(path)

        await get_event_bus().publish(
            Event(
                type=EventType.FILE_DELETED,
                session_id=self.session_id,
                data={"path": str(path.relative_to(self.root_path))},
            )
        )
        return True

    def list_files(
        self,
        relative_dir: str | Path = ".",
        recursive: bool = True,
        pattern: str = "*",
    ) -> list[str]:
        """List files matching pattern in relative_dir."""
        target_dir = self._resolve_safe(relative_dir)
        if not target_dir.exists():
            return []

        results: list[str] = []
        iterator = target_dir.rglob(pattern) if recursive else target_dir.glob(pattern)

        for p in iterator:
            # Skip hidden git or cache directories
            parts = p.relative_to(self.root_path).parts
            if any(part.startswith(".") and part != "." for part in parts):
                continue
            if p.is_file():
                results.append(str(p.relative_to(self.root_path)))

        return sorted(results)

    def get_tree(self, max_depth: int = 4) -> dict:
        """Generate structured directory tree representation."""
        def _build_tree(current: Path, depth: int) -> dict:
            if depth > max_depth:
                return {"...": "max depth reached"}
            tree: dict = {}
            try:
                for entry in sorted(current.iterdir()):
                    if entry.name.startswith(".") or entry.name in ("__pycache__", "node_modules", ".venv"):
                        continue
                    if entry.is_dir():
                        tree[entry.name + "/"] = _build_tree(entry, depth + 1)
                    else:
                        tree[entry.name] = entry.stat().st_size
            except PermissionError:
                pass
            return tree

        return {self.root_path.name + "/": _build_tree(self.root_path, 1)}

    def search_code(self, query: str, extensions: list[str] | None = None) -> list[dict]:
        """Search text in files within the workspace."""
        results: list[dict] = []
        ext_set = set(extensions) if extensions else None

        for p in self.root_path.rglob("*"):
            if not p.is_file():
                continue
            parts = p.relative_to(self.root_path).parts
            if any(part.startswith(".") for part in parts):
                continue
            if ext_set and p.suffix not in ext_set:
                continue

            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    for idx, line in enumerate(f, start=1):
                        if query in line:
                            results.append({
                                "file": str(p.relative_to(self.root_path)),
                                "line_number": idx,
                                "line_content": line.strip(),
                            })
            except Exception:
                continue

        return results
