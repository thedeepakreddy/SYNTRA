"""Model registry and routing policy visibility endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from syntra.api.auth.dependencies import require_viewer_or_above
from syntra.api.auth.models import AuthenticatedUser
from syntra.core.config import get_settings
from syntra.llm.config import ModelSpec, ModelTier, load_model_registry
from syntra.llm.router import ModelRouter

router = APIRouter(prefix="/models", tags=["Models"])


class ModelRoutingSimulationRequest(BaseModel):
    """Parameters for simulating a model routing decision."""

    agent_role: str | None = None
    requested_model: str | None = None
    is_complex: bool = False


class ModelRoutingSimulationResponse(BaseModel):
    """Result and rationale of a simulated model routing decision."""

    resolved_model: str
    assigned_tier: str
    rationale: str


class RoutingPolicyResponse(BaseModel):
    """Active model routing policy rules and tier mappings."""

    default_model: str
    fast_model: str
    reasoning_model: str
    role_defaults: dict[str, str]
    fallback_policy: str = "conservative_fallback"


@router.get("", response_model=list[ModelSpec])
async def list_models(
    user: Annotated[AuthenticatedUser, Depends(require_viewer_or_above)],
) -> list[ModelSpec]:
    """List all registered models and verified pricing profiles from config/models.yaml."""
    registry = load_model_registry()
    return list(registry.values())


@router.get("/routing", response_model=RoutingPolicyResponse)
async def get_routing_policy(
    user: Annotated[AuthenticatedUser, Depends(require_viewer_or_above)],
) -> RoutingPolicyResponse:
    """Retrieve active model routing configuration and role-to-tier mappings."""
    settings = get_settings()
    role_defaults_str = {role: tier.value for role, tier in ModelRouter.ROLE_DEFAULTS.items()}
    return RoutingPolicyResponse(
        default_model=settings.default_model,
        fast_model=settings.fast_model,
        reasoning_model=settings.reasoning_model,
        role_defaults=role_defaults_str,
    )


@router.post("/routing/simulate", response_model=ModelRoutingSimulationResponse)
async def simulate_routing(
    req: ModelRoutingSimulationRequest,
    user: Annotated[AuthenticatedUser, Depends(require_viewer_or_above)],
) -> ModelRoutingSimulationResponse:
    """Simulate a deterministic model routing decision for a given agent role and task complexity."""
    settings = get_settings()

    if req.requested_model:
        return ModelRoutingSimulationResponse(
            resolved_model=req.requested_model,
            assigned_tier="EXPLICIT",
            rationale=f"Model '{req.requested_model}' was explicitly requested by caller.",
        )

    if req.is_complex:
        return ModelRoutingSimulationResponse(
            resolved_model=settings.reasoning_model,
            assigned_tier=ModelTier.REASONING.value,
            rationale=f"Task flagged as high-complexity; escalated to reasoning tier '{settings.reasoning_model}'.",
        )

    if req.agent_role:
        role_key = req.agent_role.lower()
        tier = ModelRouter.ROLE_DEFAULTS.get(role_key, ModelTier.BALANCED)
        if tier == ModelTier.REASONING:
            resolved = settings.reasoning_model
        elif tier == ModelTier.FAST:
            resolved = settings.fast_model
        else:
            resolved = settings.default_model

        return ModelRoutingSimulationResponse(
            resolved_model=resolved,
            assigned_tier=tier.value,
            rationale=f"Role '{req.agent_role}' mapped to tier '{tier.value}' via AGENTS.md policy.",
        )

    return ModelRoutingSimulationResponse(
        resolved_model=settings.default_model,
        assigned_tier=ModelTier.BALANCED.value,
        rationale=f"No role specified; routed to default balanced model '{settings.default_model}'.",
    )
