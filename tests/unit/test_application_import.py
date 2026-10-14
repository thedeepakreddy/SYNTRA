"""Unit tests verifying clean application import and middleware wiring."""

import httpx
import pytest

from syntra.api.app import app


@pytest.mark.unit
def test_syntra_package_import():
    """Verify that syntra modules can be imported without side-effects."""
    import syntra
    from syntra.api.app import create_app
    from syntra.core.config import get_settings
    from syntra.storage.database import get_db_manager

    assert syntra.__version__ == "0.1.0"
    assert get_settings() is not None
    assert get_db_manager() is not None
    assert create_app() is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_correlation_id_middleware():
    """Verify that incoming or generated correlation IDs are propagated in response headers."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Case 1: No correlation ID provided; server generates one
        resp1 = await client.get("/v1/health")
        assert resp1.status_code == 200
        assert "x-correlation-id" in resp1.headers
        generated_id = resp1.headers["x-correlation-id"]
        assert len(generated_id) > 10

        # Case 2: Custom correlation ID provided; server preserves it
        custom_id = "test-custom-trace-uuid-12345"
        resp2 = await client.get("/v1/health", headers={"X-Correlation-ID": custom_id})
        assert resp2.status_code == 200
        assert resp2.headers.get("x-correlation-id") == custom_id
