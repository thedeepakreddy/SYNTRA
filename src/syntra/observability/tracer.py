"""OpenTelemetry distributed tracer and span lifecycle configuration for SYNTRA."""

from __future__ import annotations

import os
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Span, Tracer

from syntra.core.redactor import SecretScrubbingSpanProcessor

# Canonical span names mandated by Phase 12 architecture
SPAN_MISSION_EXECUTE = "mission.execute"
SPAN_ORCHESTRATOR_NODE = "orchestrator.node"
SPAN_AGENT_REACT_LOOP = "agent.react_loop"
SPAN_MODEL_GEMINI_GENERATE = "model.gemini_generate"
SPAN_MCP_TOOL_INVOCATION = "mcp.tool_invocation"
SPAN_SANDBOX_COMMAND_RUN = "sandbox.command_run"
SPAN_VERIFICATION_RUN = "verification.run"

TRACER_NAME = "syntra-engine"

_global_provider: TracerProvider | None = None
_global_in_memory_exporter: InMemorySpanExporter | None = None


def init_tracer_provider(service_name: str = TRACER_NAME) -> tuple[TracerProvider, InMemorySpanExporter]:
    """Initialize OpenTelemetry TracerProvider with SecretScrubbingSpanProcessor.

    Defaults to InMemorySpanExporter when OTEL_EXPORTER_OTLP_ENDPOINT is unset,
    guaranteeing zero external network dependencies in tests and hermetic execution.
    """
    global _global_provider, _global_in_memory_exporter

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    # 1. Add secret scrubber processor first so attributes are sanitized on end
    scrubber = SecretScrubbingSpanProcessor()
    provider.add_span_processor(scrubber)

    # 2. Add span exporter
    in_memory_exporter = InMemorySpanExporter()
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")

    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter  # type: ignore

            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            provider.add_span_processor(SimpleSpanProcessor(otlp_exporter))
        except Exception:
            # Fall back safely to in-memory exporter if OTLP package or collector is unreachable
            provider.add_span_processor(SimpleSpanProcessor(in_memory_exporter))
    else:
        provider.add_span_processor(SimpleSpanProcessor(in_memory_exporter))

    _global_provider = provider
    _global_in_memory_exporter = in_memory_exporter
    trace.set_tracer_provider(provider)

    return provider, in_memory_exporter


def get_tracer_provider() -> TracerProvider:
    """Return the active global TracerProvider, initializing if necessary."""
    global _global_provider
    if _global_provider is None:
        init_tracer_provider()
    assert _global_provider is not None
    return _global_provider


def get_tracer(name: str = TRACER_NAME) -> Tracer:
    """Retrieve an OpenTelemetry tracer from the active TracerProvider."""
    provider = get_tracer_provider()
    return provider.get_tracer(name)


def get_in_memory_spans() -> Sequence[ReadableSpan]:
    """Return finished spans recorded by the in-memory exporter."""
    global _global_in_memory_exporter
    if _global_in_memory_exporter is None:
        init_tracer_provider()
    assert _global_in_memory_exporter is not None
    return _global_in_memory_exporter.get_finished_spans()


def clear_in_memory_spans() -> None:
    """Reset the recorded in-memory spans buffer."""
    global _global_in_memory_exporter
    if _global_in_memory_exporter is not None:
        _global_in_memory_exporter.clear()


def reset_tracer_provider() -> None:
    """Reset the tracer provider and clear in-memory state (used by test fixtures)."""
    global _global_provider, _global_in_memory_exporter
    if _global_in_memory_exporter is not None:
        _global_in_memory_exporter.clear()
    if _global_provider is None:
        init_tracer_provider()


@contextmanager
def start_span(
    name: str,
    mission_id: str | UUID | None = None,
    task_id: str | UUID | None = None,
    agent_role: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> Iterator[Span]:
    """Context manager to start a span with standardized Phase 12 boundary attributes.

    Every span carries mission_id, task_id, and agent_role when provided.
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        if mission_id is not None:
            span.set_attribute("mission_id", str(mission_id))
        if task_id is not None:
            span.set_attribute("task_id", str(task_id))
        if agent_role is not None:
            span.set_attribute("agent_role", str(agent_role))
        if attributes:
            for k, v in attributes.items():
                if v is not None:
                    span.set_attribute(k, str(v) if isinstance(v, (UUID, int, float, bool, str)) else str(v))
        yield span
