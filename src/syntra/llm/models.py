"""LLM data structures and model representations."""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
from syntra.core.telemetry import TokenUsage


class MessageRole(str, Enum):
    """Message roles for conversational context."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ModelTier(str, Enum):
    """Model selection tiers."""
    FAST = "gemini-2.0-flash-lite"
    BALANCED = "gemini-2.5-flash"
    REASONING = "gemini-2.5-pro"


class ToolCall(BaseModel):
    """Represents a function/tool invocation request from the model."""
    id: str = Field(default="")
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Represents the output from executing a tool."""
    call_id: str
    name: str
    output: Any
    is_error: bool = False


class LLMMessage(BaseModel):
    """Single message in the LLM conversation history."""
    role: MessageRole
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None


class LLMResponse(BaseModel):
    """Unified response from LLM generation."""
    text: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: TokenUsage = Field(default_factory=TokenUsage)
    model: str
    finish_reason: str | None = None
    raw: Any = None


class ToolDefinition(BaseModel):
    """Specification of a tool exposed to the LLM."""
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema dict
