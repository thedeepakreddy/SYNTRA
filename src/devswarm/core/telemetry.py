"""Telemetry and cost estimation for DevSwarm."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock

# Standard pricing per million tokens (in USD) as of 2025/2026
MODEL_PRICING: dict[str, dict[str, float]] = {
    # Gemini 2.5 Flash / 2.0 Flash
    "gemini-2.5-flash": {"input_per_m": 0.075, "output_per_m": 0.30},
    "gemini-2.0-flash": {"input_per_m": 0.075, "output_per_m": 0.30},
    "gemini-2.0-flash-lite": {"input_per_m": 0.0375, "output_per_m": 0.15},
    # Gemini 2.5 Pro / 1.5 Pro
    "gemini-2.5-pro": {"input_per_m": 1.25, "output_per_m": 5.00},
    "gemini-1.5-pro": {"input_per_m": 1.25, "output_per_m": 5.00},
    "default": {"input_per_m": 0.10, "output_per_m": 0.40},
}


@dataclass
class TokenUsage:
    """Usage stats for a single LLM invocation or aggregated session."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def add(self, other: "TokenUsage") -> "TokenUsage":
        """Combine two token usages."""
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cached_tokens=self.cached_tokens + other.cached_tokens,
            estimated_cost_usd=self.estimated_cost_usd + other.estimated_cost_usd,
        )


@dataclass
class InvocationMetric:
    """Detailed record of an agent or LLM call."""

    session_id: str
    agent_id: str
    agent_role: str
    model: str
    latency_seconds: float
    usage: TokenUsage
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    success: bool = True
    error_message: str | None = None


class TelemetryCollector:
    """Thread-safe collector for session and system-wide metrics."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._metrics: list[InvocationMetric] = []
        self._session_usage: dict[str, TokenUsage] = {}

    def calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate invocation cost in USD."""
        rates = MODEL_PRICING.get(model, MODEL_PRICING["default"])
        cost_in = (prompt_tokens / 1_000_000.0) * rates["input_per_m"]
        cost_out = (completion_tokens / 1_000_000.0) * rates["output_per_m"]
        return round(cost_in + cost_out, 6)

    def record_call(
        self,
        session_id: str,
        agent_id: str,
        agent_role: str,
        model: str,
        latency_seconds: float,
        prompt_tokens: int,
        completion_tokens: int,
        cached_tokens: int = 0,
        success: bool = True,
        error_message: str | None = None,
    ) -> InvocationMetric:
        """Record an LLM invocation."""
        cost = self.calculate_cost(model, prompt_tokens, completion_tokens)
        total_tokens = prompt_tokens + completion_tokens
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cached_tokens=cached_tokens,
            estimated_cost_usd=cost,
        )
        metric = InvocationMetric(
            session_id=session_id,
            agent_id=agent_id,
            agent_role=agent_role,
            model=model,
            latency_seconds=latency_seconds,
            usage=usage,
            success=success,
            error_message=error_message,
        )

        with self._lock:
            self._metrics.append(metric)
            if session_id not in self._session_usage:
                self._session_usage[session_id] = TokenUsage()
            self._session_usage[session_id] = self._session_usage[session_id].add(usage)

        return metric

    def get_session_usage(self, session_id: str) -> TokenUsage:
        """Get total aggregated usage for a specific session."""
        with self._lock:
            return self._session_usage.get(session_id, TokenUsage())

    def get_summary(self) -> dict:
        """Get overall system summary."""
        with self._lock:
            total_prompt = sum(m.usage.prompt_tokens for m in self._metrics)
            total_comp = sum(m.usage.completion_tokens for m in self._metrics)
            total_cost = sum(m.usage.estimated_cost_usd for m in self._metrics)
            total_calls = len(self._metrics)
            successful_calls = sum(1 for m in self._metrics if m.success)
            avg_latency = (
                sum(m.latency_seconds for m in self._metrics) / total_calls if total_calls > 0 else 0.0
            )

            return {
                "total_invocations": total_calls,
                "successful_invocations": successful_calls,
                "failed_invocations": total_calls - successful_calls,
                "total_prompt_tokens": total_prompt,
                "total_completion_tokens": total_comp,
                "total_tokens": total_prompt + total_comp,
                "total_estimated_cost_usd": round(total_cost, 6),
                "average_latency_seconds": round(avg_latency, 3),
            }

    def clear(self) -> None:
        """Clear all metrics."""
        with self._lock:
            self._metrics.clear()
            self._session_usage.clear()


# Global TelemetryCollector singleton
_telemetry_instance: TelemetryCollector | None = None


def get_telemetry() -> TelemetryCollector:
    """Retrieve global TelemetryCollector instance."""
    global _telemetry_instance
    if _telemetry_instance is None:
        _telemetry_instance = TelemetryCollector()
    return _telemetry_instance
