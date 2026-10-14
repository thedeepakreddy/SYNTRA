"""Agent memory systems: working memory, notes, and symbol store."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class MemoryNote:
    """A durable note recorded by an agent during analysis or execution."""

    key: str
    content: str
    author_role: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    tags: list[str] = field(default_factory=list)


class AgentMemory:
    """Manages working memory and durable notes for agents."""

    def __init__(self) -> None:
        self._working_memory: dict[str, Any] = {}
        self._notes: list[MemoryNote] = []

    def set(self, key: str, value: Any) -> None:
        """Store item in working memory."""
        self._working_memory[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve item from working memory."""
        return self._working_memory.get(key, default)

    def delete(self, key: str) -> None:
        """Remove item from working memory."""
        self._working_memory.pop(key, None)

    def record_note(self, key: str, content: str, author_role: str, tags: list[str] | None = None) -> MemoryNote:
        """Add a durable note to memory."""
        note = MemoryNote(
            key=key,
            content=content,
            author_role=author_role,
            tags=tags or [],
        )
        self._notes.append(note)
        return note

    def find_notes(self, tag: str | None = None, query: str | None = None) -> list[MemoryNote]:
        """Search notes by tag or content keyword."""
        results = self._notes
        if tag:
            results = [n for n in results if tag in n.tags]
        if query:
            q_lower = query.lower()
            results = [n for n in results if q_lower in n.content.lower() or q_lower in n.key.lower()]
        return results

    def dump_context(self) -> str:
        """Format notes and working memory into a prompt-friendly string."""
        sections = []
        if self._working_memory:
            sections.append("### Working Memory State:")
            for k, v in self._working_memory.items():
                sections.append(f"- **{k}**: {v}")

        if self._notes:
            sections.append("\n### Recorded Notes:")
            for n in self._notes[-10:]:  # most recent 10 notes
                sections.append(f"- [{n.author_role}] {n.key}: {n.content}")

        return "\n".join(sections)
