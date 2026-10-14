"""Diff generation, unified patch application, and text replacement engine."""

import difflib
from syntra.core.exceptions import SandboxError


class FilePatcher:
    """Safely applies targeted content edits and diffs."""

    @classmethod
    def replace_content(
        cls,
        original: str,
        target: str,
        replacement: str,
        allow_multiple: bool = False,
    ) -> str:
        """Replace exact block of text in original content."""
        if not target:
            raise SandboxError("Target content to replace cannot be empty")

        count = original.count(target)
        if count == 0:
            raise SandboxError(
                "Target content not found in file. Ensure exact whitespace, indentation, and newlines match."
            )

        if count > 1 and not allow_multiple:
            raise SandboxError(
                f"Target content found {count} times in file. Provide more surrounding context lines or enable allow_multiple."
            )

        if allow_multiple:
            return original.replace(target, replacement)
        else:
            return original.replace(target, replacement, 1)

    @classmethod
    def generate_diff(cls, original: str, modified: str, filename: str = "file") -> str:
        """Generate unified diff string."""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
        )
        return "".join(diff)

    @classmethod
    def calculate_stats(cls, diff: str) -> dict[str, int]:
        """Calculate additions and deletions in diff."""
        additions = 0
        deletions = 0
        for line in diff.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                additions += 1
            elif line.startswith("-") and not line.startswith("---"):
                deletions += 1
        return {"additions": additions, "deletions": deletions}
