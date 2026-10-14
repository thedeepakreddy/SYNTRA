"""Agent context, conversation history, and context compaction."""

from dataclasses import dataclass, field
from typing import Any
from syntra.agents.memory import AgentMemory
from syntra.llm.models import LLMMessage, MessageRole, ToolCall


@dataclass
class AgentContext:
    """Execution context and conversational state for an individual agent."""

    session_id: str
    agent_id: str
    role: str
    task: str = ""
    history: list[LLMMessage] = field(default_factory=list)
    memory: AgentMemory = field(default_factory=AgentMemory)
    blackboard: dict[str, Any] = field(default_factory=dict)
    max_history_messages: int = 50

    def add_user_message(self, content: str) -> None:
        """Append user instruction to history."""
        self.history.append(LLMMessage(role=MessageRole.USER, content=content))
        self._maybe_compact()

    def add_assistant_message(self, content: str = "", tool_calls: list[ToolCall] | None = None) -> None:
        """Append model output to history."""
        self.history.append(
            LLMMessage(
                role=MessageRole.ASSISTANT,
                content=content,
                tool_calls=tool_calls or [],
            )
        )
        self._maybe_compact()

    def add_tool_result(self, call_id: str, tool_name: str, result: Any) -> None:
        """Append tool execution output to history."""
        content_str = str(result)
        # Limit individual tool result size in context
        if len(content_str) > 10000:
            content_str = content_str[:10000] + "\n... [TRUNCATED FOR CONTEXT LIMIT]"

        self.history.append(
            LLMMessage(
                role=MessageRole.TOOL,
                content=content_str,
                name=tool_name,
                tool_call_id=call_id,
            )
        )
        self._maybe_compact()

    def _maybe_compact(self) -> None:
        """Compact history if it exceeds threshold to preserve token capacity."""
        if len(self.history) <= self.max_history_messages:
            return

        # Keep initial prompt, and last 20 messages
        initial = self.history[:2]
        recent = self.history[-20:]

        summary_msg = LLMMessage(
            role=MessageRole.SYSTEM,
            content=f"[SYSTEM CONTEXT COMPACTION: {len(self.history) - 22} prior messages compacted]",
        )
        self.history = initial + [summary_msg] + recent
