"""Model configuration registry, specifications, and cost accounting."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from syntra.llm.exceptions import ModelPricingError


class UnknownCostPolicy(str, Enum):
    """Policy for handling models with unverified or missing pricing."""

    REJECT = "reject"
    CONSERVATIVE_FALLBACK = "conservative_fallback"
    FLAG_UNVERIFIED = "flag_unverified"


class ModelTier(str, Enum):
    """Model capability and cost tiers."""

    FAST = "fast"
    BALANCED = "balanced"
    REASONING = "reasoning"


class ContextPolicy(BaseModel):
    """Context window and token truncation policies."""

    context_window_tokens: int = Field(default=1_048_576, description="Total input + output context limit")
    truncation_strategy: str = Field(
        default="prioritize_system_and_recent",
        description="Truncation rule: 'prioritize_system_and_recent', 'summarize_oldest', or 'none'",
    )


class RetryPolicy(BaseModel):
    """Bounded retry parameters for transient model failures."""

    max_retries: int = Field(default=3, ge=0, le=10)
    initial_delay_seconds: float = Field(default=1.0, ge=0.0)
    backoff_multiplier: float = Field(default=2.0, ge=1.0)
    max_delay_seconds: float = Field(default=10.0, ge=1.0)


class PricingConfiguration(BaseModel):
    """Documented pricing metadata distinguishing measured usage from estimated cost."""

    pricing_known: bool = Field(default=True, description="Whether pricing is documented and verified")
    source: str | None = Field(default=None, description="Documented pricing source / URL reference")
    effective_date: str | None = Field(default=None, description="Date pricing was verified (YYYY-MM-DD)")
    input_per_million_usd: Decimal | None = Field(default=None, description="USD per 1,000,000 prompt tokens")
    output_per_million_usd: Decimal | None = Field(default=None, description="USD per 1,000,000 completion tokens")
    unknown_cost_policy: UnknownCostPolicy = Field(
        default=UnknownCostPolicy.CONSERVATIVE_FALLBACK,
        description="Policy applied when pricing_known is False or rates are None",
    )
    fallback_input_per_million_usd: Decimal = Field(
        default=Decimal("2.50"),
        description="Ceiling prompt token rate per million USD when unverified",
    )
    fallback_output_per_million_usd: Decimal = Field(
        default=Decimal("10.00"),
        description="Ceiling completion token rate per million USD when unverified",
    )


class ModelSpec(BaseModel):
    """Authoritative specification and pricing profile for a supported model."""

    provider: str = Field(..., description="Provider name (e.g. 'gemini', 'mock')")
    model_id: str = Field(..., description="Canonical model identifier recognized by provider")
    name: str = Field(default="", description="Alias identifier (defaults to model_id)")
    enabled: bool = Field(default=True, description="Whether model is enabled for agent execution")
    tier: ModelTier = Field(default=ModelTier.BALANCED, description="Operational capability tier")
    lifecycle_status: str = Field(default="ACTIVE", description="Lifecycle status: ACTIVE, DEPRECATED, or SHUTDOWN")
    deprecated: bool = Field(default=False, description="Whether model has been deprecated")
    shutdown_date: str | None = Field(default=None, description="Official shutdown date if deprecated (YYYY-MM-DD)")
    replacement: str | None = Field(default=None, description="Recommended active replacement model")
    supported_capabilities: list[str] = Field(
        default_factory=lambda: ["text_generation", "structured_output", "function_calling"],
        description="Capabilities verified for this model",
    )
    max_output_tokens: int = Field(default=8_192, description="Maximum generation token limit per response")
    context_policy: ContextPolicy = Field(default_factory=ContextPolicy)
    timeout_seconds: float = Field(default=60.0, description="Standard timeout for generation requests")
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    pricing_configuration: PricingConfiguration = Field(default_factory=PricingConfiguration)
    default_temperature: float = Field(default=0.2, description="Default temperature for balanced reasoning")

    def model_post_init(self, __context: Any) -> None:
        if not self.name:
            self.name = self.model_id

    @property
    def context_window_tokens(self) -> int:
        return self.context_policy.context_window_tokens

    @property
    def cost_per_input_token(self) -> Decimal:
        if self.pricing_configuration.pricing_known and self.pricing_configuration.input_per_million_usd is not None:
            return self.pricing_configuration.input_per_million_usd / Decimal(1_000_000)
        return self.pricing_configuration.fallback_input_per_million_usd / Decimal(1_000_000)

    @property
    def cost_per_output_token(self) -> Decimal:
        if self.pricing_configuration.pricing_known and self.pricing_configuration.output_per_million_usd is not None:
            return self.pricing_configuration.output_per_million_usd / Decimal(1_000_000)
        return self.pricing_configuration.fallback_output_per_million_usd / Decimal(1_000_000)

    @property
    def supports_tools(self) -> bool:
        return "function_calling" in self.supported_capabilities

    @property
    def supports_structured_outputs(self) -> bool:
        return "structured_output" in self.supported_capabilities

    @property
    def is_pricing_known(self) -> bool:
        return (
            self.pricing_configuration.pricing_known
            and self.pricing_configuration.input_per_million_usd is not None
            and self.pricing_configuration.output_per_million_usd is not None
        )


def load_model_registry(config_path: Path | None = None) -> dict[str, ModelSpec]:
    """Load model registry from YAML config file or fallback to authoritative defaults."""
    registry: dict[str, ModelSpec] = {}
    path = config_path or Path("config/models.yaml")

    if path.is_file():
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            models_data = data.get("models", {})
            for m_key, m_val in models_data.items():
                if isinstance(m_val, dict):
                    # Determine tier based on model name
                    tier = ModelTier.BALANCED
                    if "pro" in m_key:
                        tier = ModelTier.REASONING
                    elif "lite" in m_key or "fast" in m_key:
                        tier = ModelTier.FAST

                    spec = ModelSpec(
                        provider=m_val.get("provider", "gemini"),
                        model_id=m_val.get("model_id", m_key),
                        name=m_key,
                        enabled=m_val.get("enabled", True),
                        tier=tier,
                        lifecycle_status=m_val.get("lifecycle_status", "ACTIVE"),
                        deprecated=m_val.get("deprecated", False),
                        shutdown_date=m_val.get("shutdown_date"),
                        replacement=m_val.get("replacement"),
                        supported_capabilities=m_val.get(
                            "supported_capabilities", ["text_generation", "structured_output", "function_calling"]
                        ),
                        max_output_tokens=m_val.get("max_output_tokens", 8192),
                        context_policy=ContextPolicy(**m_val.get("context_policy", {})),
                        timeout_seconds=m_val.get("timeout_seconds", 60.0),
                        retry_policy=RetryPolicy(**m_val.get("retry_policy", {})),
                        pricing_configuration=PricingConfiguration(**m_val.get("pricing_configuration", {})),
                        default_temperature=0.1 if tier == ModelTier.REASONING else 0.2,
                    )
                    registry[m_key] = spec
        except Exception:
            pass

    if not registry:
        registry = _default_registry()

    return registry


def _default_registry() -> dict[str, ModelSpec]:
    return {
        "gemini-2.5-pro": ModelSpec(
            provider="gemini",
            model_id="gemini-2.5-pro",
            name="gemini-2.5-pro",
            enabled=True,
            tier=ModelTier.REASONING,
            lifecycle_status="ACTIVE",
            max_output_tokens=8192,
            context_policy=ContextPolicy(context_window_tokens=2_097_152),
            timeout_seconds=90.0,
            pricing_configuration=PricingConfiguration(
                pricing_known=True,
                source="Google Cloud Vertex AI Pricing",
                effective_date="2026-10-15",
                input_per_million_usd=Decimal("1.25"),
                output_per_million_usd=Decimal("5.00"),
                unknown_cost_policy=UnknownCostPolicy.CONSERVATIVE_FALLBACK,
                fallback_input_per_million_usd=Decimal("2.50"),
                fallback_output_per_million_usd=Decimal("10.00"),
            ),
            default_temperature=0.1,
        ),
        "gemini-2.5-flash": ModelSpec(
            provider="gemini",
            model_id="gemini-2.5-flash",
            name="gemini-2.5-flash",
            enabled=True,
            tier=ModelTier.BALANCED,
            lifecycle_status="ACTIVE",
            max_output_tokens=8192,
            context_policy=ContextPolicy(context_window_tokens=1_048_576),
            timeout_seconds=60.0,
            pricing_configuration=PricingConfiguration(
                pricing_known=True,
                source="Google Cloud Vertex AI Pricing",
                effective_date="2026-10-15",
                input_per_million_usd=Decimal("0.15"),
                output_per_million_usd=Decimal("0.60"),
                unknown_cost_policy=UnknownCostPolicy.CONSERVATIVE_FALLBACK,
                fallback_input_per_million_usd=Decimal("2.50"),
                fallback_output_per_million_usd=Decimal("10.00"),
            ),
            default_temperature=0.2,
        ),
        "gemini-2.0-flash-lite": ModelSpec(
            provider="gemini",
            model_id="gemini-2.0-flash-lite",
            name="gemini-2.0-flash-lite",
            enabled=False,
            tier=ModelTier.FAST,
            lifecycle_status="SHUTDOWN",
            deprecated=True,
            shutdown_date="2026-06-01",
            replacement="gemini-2.5-flash",
            max_output_tokens=8192,
            context_policy=ContextPolicy(context_window_tokens=1_048_576),
            timeout_seconds=30.0,
            pricing_configuration=PricingConfiguration(
                pricing_known=False,
                source="Google AI Studio Historical (Retired)",
                effective_date="2026-06-01",
                input_per_million_usd=Decimal("0.075"),
                output_per_million_usd=Decimal("0.30"),
                unknown_cost_policy=UnknownCostPolicy.REJECT,
                fallback_input_per_million_usd=Decimal("2.50"),
                fallback_output_per_million_usd=Decimal("10.00"),
            ),
            default_temperature=0.2,
        ),
        "mock-model": ModelSpec(
            provider="mock",
            model_id="mock-model",
            name="mock-model",
            enabled=True,
            tier=ModelTier.FAST,
            lifecycle_status="ACTIVE",
            max_output_tokens=4096,
            context_policy=ContextPolicy(context_window_tokens=1_000_000, truncation_strategy="none"),
            timeout_seconds=10.0,
            retry_policy=RetryPolicy(max_retries=1, initial_delay_seconds=0.1),
            pricing_configuration=PricingConfiguration(
                pricing_known=True,
                source="Mock Deterministic Test Provider",
                effective_date="2026-01-01",
                input_per_million_usd=Decimal("0.0"),
                output_per_million_usd=Decimal("0.0"),
                unknown_cost_policy=UnknownCostPolicy.CONSERVATIVE_FALLBACK,
                fallback_input_per_million_usd=Decimal("2.50"),
                fallback_output_per_million_usd=Decimal("10.00"),
            ),
            default_temperature=0.0,
        ),
    }


MODEL_REGISTRY: dict[str, ModelSpec] = load_model_registry()


def get_model_spec(model_name: str | None = None) -> ModelSpec:
    """Retrieve ModelSpec for a given model name, falling back to gemini-2.5-flash."""
    name = (model_name or "gemini-2.5-flash").strip().lower()
    if name in MODEL_REGISTRY:
        return MODEL_REGISTRY[name]

    # Prefix match (e.g. gemini-2.5-pro-001 -> gemini-2.5-pro)
    for key, spec in MODEL_REGISTRY.items():
        if name.startswith(key):
            return spec

    # Default fallback
    return MODEL_REGISTRY.get("gemini-2.5-flash", next(iter(MODEL_REGISTRY.values())))


def compute_token_cost(
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    unknown_policy: UnknownCostPolicy | None = None,
) -> Decimal:
    """Calculate estimated USD cost based on token counts and documented model pricing.

    Unknown pricing must NOT evaluate to $0.00. An unpriced model will apply its
    configured unknown_cost_policy (REJECT, CONSERVATIVE_FALLBACK, or FLAG_UNVERIFIED).
    """
    spec = get_model_spec(model_name)
    pricing = spec.pricing_configuration
    policy = unknown_policy or pricing.unknown_cost_policy

    if not spec.is_pricing_known:
        if policy == UnknownCostPolicy.REJECT:
            raise ModelPricingError(
                f"Model '{spec.model_id}' has unverified pricing and unknown-cost policy is REJECT. "
                "Execution prohibited to preserve budget integrity."
            )
        # Apply conservative ceiling reservation
        in_rate = pricing.fallback_input_per_million_usd / Decimal(1_000_000)
        out_rate = pricing.fallback_output_per_million_usd / Decimal(1_000_000)
        estimated = (Decimal(prompt_tokens) * in_rate) + (Decimal(completion_tokens) * out_rate)
        if policy == UnknownCostPolicy.FLAG_UNVERIFIED:
            import logging

            logging.getLogger(__name__).warning(
                "UNVERIFIED_PRICING_FLAG: Model '%s' pricing is not verified. "
                "Applied conservative ceiling reservation of $%.6f (policy=%s).",
                spec.model_id,
                estimated,
                policy.value,
            )
        return estimated

    input_cost = Decimal(prompt_tokens) * spec.cost_per_input_token
    output_cost = Decimal(completion_tokens) * spec.cost_per_output_token
    return input_cost + output_cost
