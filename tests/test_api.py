"""Integration tests for DevSwarm FastAPI REST endpoints."""

import httpx
import pytest
from devswarm.api.app import app
from devswarm.checkpoints.engine import get_checkpoint_engine
from devswarm.checkpoints.models import CheckpointActionType
from devswarm.storage.database import get_db_manager


@pytest.fixture(autouse=True)
async def init_test_db():
    db = get_db_manager()
    await db.init_tables()
    yield


@pytest.mark.asyncio
async def test_health_and_telemetry():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Health
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"

        # Telemetry
        resp2 = await client.get("/api/telemetry")
        assert resp2.status_code == 200
        assert "total_invocations" in resp2.json()


@pytest.mark.asyncio
async def test_session_lifecycle_api():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        create_resp = await client.post(
            "/api/sessions",
            json={"objective": "Build REST endpoint", "autonomy_mode": "semi_autonomous"},
        )
        assert create_resp.status_code == 201
        sess_data = create_resp.json()
        session_id = sess_data["session_id"]
        assert session_id.startswith("sess-")

        # Get session
        get_resp = await client.get(f"/api/sessions/{session_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["objective"] == "Build REST endpoint"

        # List sessions
        list_resp = await client.get("/api/sessions")
        assert list_resp.status_code == 200
        sessions = list_resp.json()
        assert any(s["session_id"] == session_id for s in sessions)


@pytest.mark.asyncio
async def test_checkpoint_api():
    engine = get_checkpoint_engine()
    cp = await engine.create_checkpoint(
        session_id="test-api-session",
        agent_id="coder-1",
        agent_role="coder",
        action_type=CheckpointActionType.COMMAND_EXECUTION,
        description="Run test suite",
        proposed_command="pytest",
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Get checkpoint
        resp = await client.get(f"/api/checkpoints/{cp.checkpoint_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"

        # Resolve checkpoint (approve)
        resolve_resp = await client.post(
            f"/api/checkpoints/{cp.checkpoint_id}/resolve",
            json={"decision": "approve", "feedback": "Approved via test"},
        )
        assert resolve_resp.status_code == 200
        resolved_data = resolve_resp.json()
        assert resolved_data["status"] == "approved"
        assert resolved_data["human_feedback"] == "Approved via test"
