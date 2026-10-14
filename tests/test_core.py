"""Tests for SYNTRA core module."""

import pytest

from syntra.core import (
    AutonomyMode,
    Event,
    EventBus,
    EventType,
    TelemetryCollector,
    get_settings,
    reset_settings,
)


def test_settings_defaults():
    reset_settings()
    settings = get_settings()
    assert settings.default_model == "gemini-2.5-flash"
    assert settings.reasoning_model == "gemini-2.5-pro"
    assert settings.autonomy_mode == AutonomyMode.SEMI_AUTONOMOUS
    assert settings.sandbox_timeout_seconds == 120
    assert not settings.is_api_key_configured()


def test_telemetry_cost_calculation():
    collector = TelemetryCollector()
    # Flash: input 0.075 / 1M, output 0.30 / 1M
    cost = collector.calculate_cost("gemini-2.5-flash", prompt_tokens=1000, completion_tokens=1000)
    expected = (1000 / 1_000_000) * 0.075 + (1000 / 1_000_000) * 0.30
    assert cost == pytest.approx(expected, rel=1e-4)

    metric = collector.record_call(
        session_id="sess-1",
        agent_id="agent-1",
        agent_role="coder",
        model="gemini-2.5-flash",
        latency_seconds=1.2,
        prompt_tokens=5000,
        completion_tokens=2000,
    )
    assert metric.usage.total_tokens == 7000
    assert metric.usage.estimated_cost_usd > 0

    session_usage = collector.get_session_usage("sess-1")
    assert session_usage.total_tokens == 7000

    summary = collector.get_summary()
    assert summary["total_invocations"] == 1
    assert summary["total_tokens"] == 7000


@pytest.mark.asyncio
async def test_event_bus_publish_and_subscribe():
    bus = EventBus()
    received_events: list[Event] = []

    async def on_event(event: Event):
        received_events.append(event)

    bus.subscribe(on_event, EventType.TASK_STARTED)

    # Publish matching event
    ev1 = Event(
        type=EventType.TASK_STARTED,
        session_id="s1",
        data={"task_name": "Implement auth"},
    )
    await bus.publish(ev1)

    # Publish non-matching event
    ev2 = Event(
        type=EventType.TASK_COMPLETED,
        session_id="s1",
        data={"result": "done"},
    )
    await bus.publish(ev2)

    assert len(received_events) == 1
    assert received_events[0].data["task_name"] == "Implement auth"

    # Queue streaming test
    q = bus.create_event_queue()
    await bus.publish(ev1)
    streamed = await q.get()
    assert streamed.type == EventType.TASK_STARTED
    bus.remove_event_queue(q)
