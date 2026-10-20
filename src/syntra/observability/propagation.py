"""W3C traceparent context injection, extraction, and distributed propagation for SYNTRA."""

from __future__ import annotations

import re

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

_PROPAGATOR = TraceContextTextMapPropagator()
_TRACEPARENT_REGEX = re.compile(r"^00-([0-9a-fA-F]{32})-([0-9a-fA-F]{16})-([0-9a-fA-F]{2})$")


def inject_trace_context(carrier: dict[str, str] | None = None, context: Context | None = None) -> dict[str, str]:
    """Inject W3C traceparent (and tracestate if present) into the carrier dictionary."""
    if carrier is None:
        carrier = {}
    _PROPAGATOR.inject(carrier, context=context)
    return carrier


def extract_trace_context(carrier: dict[str, str], context: Context | None = None) -> Context:
    """Extract W3C trace context from carrier dictionary and return an OpenTelemetry Context."""
    # Ensure lowercase keys for case-insensitive lookup
    normalized_carrier = {k.lower(): v for k, v in carrier.items()}
    return _PROPAGATOR.extract(normalized_carrier, context=context)


def get_current_trace_id() -> str | None:
    """Return the 32-character hex trace ID of the currently active span, or None."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.trace_id != 0:
        return format(ctx.trace_id, "032x")
    return None


def get_current_span_id() -> str | None:
    """Return the 16-character hex span ID of the currently active span, or None."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.span_id != 0:
        return format(ctx.span_id, "016x")
    return None


def format_traceparent(trace_id: str, span_id: str, sampled: bool = True) -> str:
    """Format trace_id and span_id into a W3C traceparent header string."""
    clean_trace = trace_id.lower().strip()
    clean_span = span_id.lower().strip()
    flags = "01" if sampled else "00"
    return f"00-{clean_trace}-{clean_span}-{flags}"


def parse_traceparent(traceparent: str) -> tuple[str, str, bool] | None:
    """Parse and validate a W3C traceparent header.

    Returns (trace_id, span_id, sampled) if valid, or None if malformed or all zeros.
    """
    if not traceparent:
        return None

    match = _TRACEPARENT_REGEX.match(traceparent.strip())
    if not match:
        return None

    trace_id, span_id, flags = match.group(1).lower(), match.group(2).lower(), match.group(3)

    # All-zero trace_id or span_id is invalid according to W3C Trace Context spec
    if trace_id == "0" * 32 or span_id == "0" * 16:
        return None

    flags_int = int(flags, 16)
    sampled = bool(flags_int & 0x01)
    return trace_id, span_id, sampled
