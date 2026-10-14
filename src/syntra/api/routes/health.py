"""Healthcheck and telemetry endpoints."""

from fastapi import APIRouter
from syntra.api.schemas import SystemHealthResponse
from syntra.core.config import get_settings
from syntra.core.telemetry import get_telemetry

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=SystemHealthResponse)
async def health_check() -> SystemHealthResponse:
    """Check health, Gemini readiness, and operational status."""
    settings = get_settings()
    telemetry = get_telemetry().get_summary()

    return SystemHealthResponse(
        status="healthy",
        version="0.1.0",
        gemini_configured=settings.is_api_key_configured(),
        autonomy_mode=settings.autonomy_mode.value,
        telemetry=telemetry,
    )


@router.get("/telemetry")
async def get_telemetry_metrics() -> dict:
    """Retrieve detailed token usage, cost, and latency analytics."""
    return get_telemetry().get_summary()
