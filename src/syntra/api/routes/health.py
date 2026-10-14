"""Healthcheck, readiness probes, and telemetry endpoints."""

import asyncio
from datetime import datetime, timezone
import time
from fastapi import APIRouter, Response, status
from sqlalchemy import text
from syntra.api.schemas import ComponentHealth, SystemHealthResponse, SystemReadinessResponse
from syntra.core.config import get_settings
from syntra.core.telemetry import get_telemetry
from syntra.storage.database import get_db_manager

router = APIRouter(tags=["health"])


@router.get("/health", response_model=SystemHealthResponse)
@router.get("/api/health", response_model=SystemHealthResponse)
async def health_check() -> SystemHealthResponse:
    """Liveness probe: verifies process health, Gemini readiness, and operational status."""
    settings = get_settings()
    telemetry = get_telemetry().get_summary()

    return SystemHealthResponse(
        status="healthy",
        version="0.1.0",
        gemini_configured=settings.is_api_key_configured(),
        autonomy_mode=settings.autonomy_mode.value,
        telemetry=telemetry,
    )


@router.get("/health/ready", response_model=SystemReadinessResponse)
@router.get("/api/health/ready", response_model=SystemReadinessResponse)
async def readiness_check(response: Response) -> SystemReadinessResponse:
    """Readiness probe: validates connectivity across PostgreSQL, Redis, MinIO, and Sandbox filesystem."""
    settings = get_settings()
    components: dict[str, ComponentHealth] = {}
    is_ready = True

    # 1. Database Connectivity Probe
    db_start = time.perf_counter()
    try:
        db_mgr = get_db_manager()
        async with db_mgr.get_session() as session:
            await session.execute(text("SELECT 1"))
        db_latency = (time.perf_counter() - db_start) * 1000
        components["database"] = ComponentHealth(
            status="healthy",
            latency_ms=round(db_latency, 2),
            details=settings.database_url.split("@")[-1] if "@" in settings.database_url else "local",
        )
    except Exception as exc:
        is_ready = False
        components["database"] = ComponentHealth(
            status="unhealthy",
            details=f"Database probe failed: {exc}",
        )

    # 2. Redis Task Queue Connectivity Probe
    redis_start = time.perf_counter()
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(
            settings.redis_url,
            socket_connect_timeout=1.5,
            socket_timeout=1.5,
        )
        await client.ping()
        await client.aclose()
        redis_latency = (time.perf_counter() - redis_start) * 1000
        components["redis"] = ComponentHealth(
            status="healthy",
            latency_ms=round(redis_latency, 2),
            details=settings.redis_url.split("@")[-1] if "@" in settings.redis_url else settings.redis_url,
        )
    except Exception as exc:
        components["redis"] = ComponentHealth(
            status="unavailable",
            details=f"Redis unreachable: {exc}",
        )

    # 3. MinIO / S3 Object Storage Connectivity Probe
    minio_start = time.perf_counter()
    try:
        from minio import Minio
        import urllib3
        endpoint = settings.s3_endpoint
        if "://" in endpoint:
            endpoint = endpoint.split("://")[1]

        fast_http = urllib3.PoolManager(
            timeout=urllib3.Timeout(connect=0.5, read=0.5),
            retries=False,
        )
        client = Minio(
            endpoint=endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            secure=settings.s3_secure,
            http_client=fast_http,
        )
        loop = asyncio.get_running_loop()
        await asyncio.wait_for(
            loop.run_in_executor(None, client.list_buckets),
            timeout=1.0,
        )
        minio_latency = (time.perf_counter() - minio_start) * 1000
        components["minio"] = ComponentHealth(
            status="healthy",
            latency_ms=round(minio_latency, 2),
            details=f"Endpoint: {endpoint}, Bucket: {settings.s3_bucket}",
        )
    except Exception as exc:
        components["minio"] = ComponentHealth(
            status="unavailable",
            details=f"MinIO unreachable: {exc}",
        )

    # 4. Sandbox Filesystem Probe
    try:
        settings.sandbox_base_dir.mkdir(parents=True, exist_ok=True)
        probe_file = settings.sandbox_base_dir / ".health_probe.tmp"
        probe_file.write_text("probe")
        probe_file.unlink(missing_ok=True)
        components["sandbox"] = ComponentHealth(
            status="healthy",
            details=f"Base directory: {settings.sandbox_base_dir.resolve()}",
        )
    except Exception as exc:
        is_ready = False
        components["sandbox"] = ComponentHealth(
            status="unhealthy",
            details=f"Sandbox filesystem error: {exc}",
        )

    overall_status = "ready" if is_ready else "not_ready"
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return SystemReadinessResponse(
        status=overall_status,
        version="0.1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        components=components,
    )


@router.get("/telemetry")
@router.get("/api/telemetry")
async def get_telemetry_metrics() -> dict:
    """Retrieve detailed token usage, cost, and latency analytics."""
    return get_telemetry().get_summary()
