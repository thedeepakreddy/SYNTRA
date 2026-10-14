"""Unit tests verifying liveness and readiness probe behaviors."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from syntra.api.app import app


@pytest.mark.unit
@pytest.mark.asyncio
async def test_v1_health_liveness():
    """Verify that /v1/health responds with 200 OK and valid health telemetry."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert "telemetry" in data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_v1_ready_probe_success():
    """Verify that /v1/ready responds with ready status when database is reachable."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v1/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["components"]["database"]["status"] == "healthy"
        assert data["components"]["sandbox"]["status"] == "healthy"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_v1_ready_probe_database_failure():
    """Verify that /v1/ready returns 503 and not_ready status when database is unavailable."""
    transport = httpx.ASGITransport(app=app)
    with patch("syntra.storage.database.DatabaseManager.session") as mock_session:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.side_effect = ConnectionRefusedError("Simulated database connection failure")
        mock_session.return_value = mock_ctx

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/v1/ready")
            assert resp.status_code == 503
            data = resp.json()
            assert data["status"] == "not_ready"
            assert data["components"]["database"]["status"] == "unhealthy"
            assert "Simulated database connection failure" in data["components"]["database"]["details"]
