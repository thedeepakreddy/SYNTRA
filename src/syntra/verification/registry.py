"""Protected Test Suite Registry enforcing test immutability and anti-tampering invariants."""

from __future__ import annotations

import fnmatch
import hashlib
import re
from pathlib import Path
from typing import Sequence

from syntra.domain.entities import ProtectedTestSuiteManifest
from syntra.domain.exceptions import ProtectedTestViolationError

# Default glob patterns representing immutable regression and baseline test suites
DEFAULT_PROTECTED_PATTERNS: tuple[str, ...] = (
    "tests/protected/**",
    "tests/protected/*",
    "tests/regression/**",
    "tests/regression/*",
    "tests/baseline/**",
    "tests/baseline/*",
    "tests/test_phase10_*.py",
    "tests/test_phase11_*.py",
    "tests/test_phase12_*.py",
)

# Regex patterns matching attempts to skip or disable tests in added diff hunks
DISABLING_PATTERNS = [
    re.compile(r"^\+\s*@pytest\.mark\.skip", re.MULTILINE),
    re.compile(r"^\+\s*@pytest\.mark\.xfail", re.MULTILINE),
    re.compile(r"^\+\s*pytest\.skip\(", re.MULTILINE),
    re.compile(r"^\+\s*@unittest\.skip", re.MULTILINE),
    re.compile(r"^\+\s*raise\s+pytest\.skip", re.MULTILINE),
]


class ProtectedTestRegistry:
    """Manages immutable regression test manifests and guards against test tampering."""

    def __init__(self, patterns: Sequence[str] | None = None) -> None:
        self.patterns = tuple(patterns) if patterns is not None else DEFAULT_PROTECTED_PATTERNS

    def is_protected_path(self, relative_path: str) -> bool:
        """Determine whether a repository-relative path matches protected test patterns."""
        normalized = relative_path.strip().replace("\\", "/").lstrip("/")
        for pattern in self.patterns:
            if fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(f"/{normalized}", pattern):
                return True
            # Also support directory-level matching
            if pattern.endswith("/**"):
                prefix = pattern[:-3].rstrip("/")
                if normalized == prefix or normalized.startswith(f"{prefix}/"):
                    return True
        return False

    def extract_touched_files(self, patch: str) -> set[str]:
        """Extract all relative file paths modified, added, deleted, or renamed in a unified diff."""
        touched: set[str] = set()
        for line in patch.splitlines():
            # Check diff header: diff --git a/path b/path
            if line.startswith("diff --git "):
                parts = line.split(" ")
                if len(parts) >= 4:
                    path_a = parts[2].removeprefix("a/").strip()
                    path_b = parts[3].removeprefix("b/").strip()
                    if path_a and path_a != "/dev/null":
                        touched.add(path_a.replace("\\", "/"))
                    if path_b and path_b != "/dev/null":
                        touched.add(path_b.replace("\\", "/"))
            elif line.startswith("--- ") and not line.startswith("--- /dev/null"):
                path = line.split()[1].removeprefix("a/").strip()
                if path and path != "/dev/null":
                    touched.add(path.replace("\\", "/"))
            elif line.startswith("+++ ") and not line.startswith("+++ /dev/null"):
                path = line.split()[1].removeprefix("b/").strip()
                if path and path != "/dev/null":
                    touched.add(path.replace("\\", "/"))
            elif line.startswith("rename from "):
                path = line.removeprefix("rename from ").strip()
                touched.add(path.replace("\\", "/"))
            elif line.startswith("rename to "):
                path = line.removeprefix("rename to ").strip()
                touched.add(path.replace("\\", "/"))
            elif line.startswith("deleted file mode "):
                # File deletion
                pass
        return touched

    def check_patch(
        self,
        patch: str,
        manifest: ProtectedTestSuiteManifest | None = None,
    ) -> None:
        """Validate that a unified diff does not mutate, delete, or skip protected tests.

        Raises:
            ProtectedTestViolationError: If the patch alters protected tests or disables assertions.
        """
        if not patch or not patch.strip():
            return

        touched = self.extract_touched_files(patch)
        violations: list[str] = []

        for file_path in touched:
            if self.is_protected_path(file_path):
                violations.append(file_path)
            elif manifest and file_path in manifest.protected_files:
                violations.append(file_path)

        if violations:
            raise ProtectedTestViolationError(
                f"Patch attempts to mutate protected regression test files: {sorted(violations)}. "
                "Developer agents are strictly barred from modifying protected test suites."
            )

        # Check for adversarial test deactivation in added hunks
        for pat in DISABLING_PATTERNS:
            match = pat.search(patch)
            if match:
                raise ProtectedTestViolationError(
                    f"Patch introduces test suppression/skipping directive: '{match.group(0).strip()}'. "
                    "Skipping or disabling assertions in verified deliverables is strictly prohibited."
                )

    def compute_manifest(self, repo_root: Path | str) -> ProtectedTestSuiteManifest:
        """Scan repository and compute SHA-256 digests for all protected test files."""
        root = Path(repo_root).resolve()
        protected_files: dict[str, str] = {}

        if not root.exists() or not root.is_dir():
            manifest_hash = hashlib.sha256(b"empty_manifest").hexdigest()
            return ProtectedTestSuiteManifest(
                manifest_hash=manifest_hash,
                protected_files={},
                registered_patterns=list(self.patterns),
            )

        # Walk repository and find files matching patterns
        for path in root.rglob("*"):
            if path.is_file():
                rel_path = path.relative_to(root).as_posix()
                if self.is_protected_path(rel_path):
                    hasher = hashlib.sha256()
                    hasher.update(path.read_bytes())
                    protected_files[rel_path] = hasher.hexdigest()

        # Compute deterministic overall manifest hash
        manifest_hasher = hashlib.sha256()
        for p in sorted(protected_files.keys()):
            manifest_hasher.update(f"{p}:{protected_files[p]}\n".encode("utf-8"))

        manifest_hash = manifest_hasher.hexdigest()
        return ProtectedTestSuiteManifest(
            manifest_hash=manifest_hash,
            protected_files=protected_files,
            registered_patterns=list(self.patterns),
        )

    def validate_workspace(
        self,
        repo_root: Path | str,
        manifest: ProtectedTestSuiteManifest,
    ) -> None:
        """Validate that all protected test files in the workspace match expected hashes.

        Raises:
            ProtectedTestViolationError: If any protected file is missing or its checksum altered.
        """
        root = Path(repo_root).resolve()
        for rel_path, expected_hash in manifest.protected_files.items():
            target_path = root / rel_path
            if not target_path.exists():
                raise ProtectedTestViolationError(f"Protected test file missing from workspace: {rel_path}")
            actual_hash = hashlib.sha256(target_path.read_bytes()).hexdigest()
            if actual_hash != expected_hash:
                raise ProtectedTestViolationError(
                    f"Protected test file tampered in workspace: {rel_path} "
                    f"(expected {expected_hash}, got {actual_hash})"
                )
