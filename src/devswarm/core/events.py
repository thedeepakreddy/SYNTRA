"""Asynchronous event bus and event type definitions for DevSwarm."""

import asyncio
import logging
import uuid
from collections import defaultdict
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Event types published across DevSwarm lifecycle."""

    # Session lifecycle
    SESSION_CREATED = "session.created"
    SESSION_STARTED = "session.started"
    SESSION_COMPLETED = "session.completed"
    SESSION_PAUSED = "session.paused"
    SESSION_RESUMED = "session.resumed"
    SESSION_FAILED = "session.failed"

    # Task lifecycle
    TASK_SCHEDULED = "task.scheduled"
    TASK_STARTED = "task.started"
    TASK_PROGRESS = "task.progress"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"

    # Agent actions
    AGENT_INITIALIZED = "agent.initialized"
    AGENT_STEP_STARTED = "agent.step_started"
    AGENT_THOUGHT = "agent.thought"
    AGENT_TOOL_CALL_STARTED = "agent.tool_call_started"
    AGENT_TOOL_CALL_COMPLETED = "agent.tool_call_completed"
    AGENT_TOOL_CALL_FAILED = "agent.tool_call_failed"
    AGENT_STEP_COMPLETED = "agent.step_completed"

    # Execution sandbox actions
    COMMAND_STARTED = "sandbox.command_started"
    COMMAND_OUTPUT = "sandbox.command_output"
    COMMAND_COMPLETED = "sandbox.command_completed"
    FILE_CREATED = "sandbox.file_created"
    FILE_MODIFIED = "sandbox.file_modified"
    FILE_DELETED = "sandbox.file_deleted"

    # Hybrid Autonomy Checkpoints
    CHECKPOINT_REQUESTED = "checkpoint.requested"
    CHECKPOINT_RESOLVED = "checkpoint.resolved"
    CHECKPOINT_CANCELLED = "checkpoint.cancelled"

    # System & Telemetry
    TOKEN_USAGE = "telemetry.token_usage"
    ERROR_OCCURRED = "system.error"


class Event(BaseModel):
    """Structured event model."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType
    session_id: str | None = None
    agent_id: str | None = None
    agent_role: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to serializable dictionary."""
        return {
            "event_id": self.event_id,
            "type": self.type.value,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "agent_role": self.agent_role,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """Async event bus for distributing events to subscribers."""

    def __init__(self) -> None:
        self._subscribers: dict[EventType | None, list[EventHandler]] = defaultdict(list)
        self._history: list[Event] = []
        self._max_history: int = 1000
        self._queues: list[asyncio.Queue[Event]] = []

    def subscribe(self, handler: EventHandler, event_type: EventType | None = None) -> None:
        """Subscribe a handler to a specific event type or all events (if None)."""
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, handler: EventHandler, event_type: EventType | None = None) -> None:
        """Unsubscribe a handler."""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    def create_event_queue(self, maxsize: int = 100) -> asyncio.Queue[Event]:
        """Create a dedicated async queue for streaming events (e.g. for WebSockets)."""
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=maxsize)
        self._queues.append(queue)
        return queue

    def remove_event_queue(self, queue: asyncio.Queue[Event]) -> None:
        """Remove a streaming queue."""
        if queue in self._queues:
            self._queues.remove(queue)

    async def publish(self, event: Event) -> None:
        """Publish an event to all relevant subscribers and streaming queues."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        # Distribute to queues (non-blocking)
        for queue in list(self._queues):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Event stream queue full, dropping event %s", event.event_id)

        # Notify specific and global subscribers
        handlers = list(self._subscribers.get(event.type, [])) + list(self._subscribers.get(None, []))
        if handlers:
            tasks = [asyncio.create_task(self._safe_invoke(handler, event)) for handler in handlers]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_invoke(self, handler: EventHandler, event: Event) -> None:
        try:
            await handler(event)
        except Exception as exc:
            logger.exception("Error in event handler for %s: %s", event.type, exc)

    def get_history(self, session_id: str | None = None, limit: int = 100) -> list[Event]:
        """Retrieve recent events, optionally filtered by session ID."""
        events = self._history
        if session_id:
            events = [e for e in events if e.session_id == session_id]
        return events[-limit:]

    def clear(self) -> None:
        """Clear all subscribers and history."""
        self._subscribers.clear()
        self._history.clear()
        self._queues.clear()


# Global EventBus singleton
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Retrieve global EventBus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
