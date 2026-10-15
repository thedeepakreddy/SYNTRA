"""Integration tests verifying LangGraph AsyncPostgresSaver durable persistence against live PostgreSQL.

If live PostgreSQL container or service is offline, these tests cleanly report
BLOCKED_BY_INFRASTRUCTURE rather than falsely passing or masking real connectivity requirements.
"""

import os
import socket
from uuid import uuid4

import pytest
from dotenv import load_dotenv

from syntra.core.config import get_settings
from syntra.orchestration import (
    WorkflowOrchestrationEngine,
)
from syntra.orchestration.checkpointer import CheckpointerFactory

load_dotenv()


def _get_postgres_test_url() -> str | None:
    test_url = os.environ.get("SYNTRA_TEST_POSTGRES_URL")
    if test_url and "sqlite" not in test_url:
        return test_url
    settings = get_settings()
    if "sqlite" not in settings.database_url:
        return settings.database_url
    return None


def _is_postgres_reachable() -> bool:
    """Check if PostgreSQL port 5432 is reachable."""
    if not _get_postgres_test_url():
        return False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        result = sock.connect_ex(("localhost", 5432))
        sock.close()
        return result == 0
    except Exception:
        return False


POSTGRES_AVAILABLE = _is_postgres_reachable()
TEST_DB_URL = _get_postgres_test_url() or "postgresql://syntra_test_user:syntra_test_user@localhost:5432/syntra_test"


@pytest.mark.integration
@pytest.mark.skipif(not POSTGRES_AVAILABLE, reason="Live PostgreSQL unreachable - BLOCKED_BY_INFRASTRUCTURE")
@pytest.mark.asyncio
async def test_live_postgres_checkpointer_setup():
    """Verify AsyncPostgresSaver initializes and runs migrations against live PostgreSQL."""
    pool, saver = await CheckpointerFactory.create_postgres_checkpointer(
        database_url=TEST_DB_URL,
        run_setup=True,
    )
    assert pool is not None
    assert saver is not None

    try:
        # Verify checkpointer responds to queries
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1;")
                row = await cur.fetchone()
                assert row is not None
                assert row[0] == 1
    finally:
        await pool.close()


@pytest.mark.integration
@pytest.mark.docker
@pytest.mark.skipif(not POSTGRES_AVAILABLE, reason="Live PostgreSQL unreachable - BLOCKED_BY_INFRASTRUCTURE")
@pytest.mark.asyncio
async def test_live_postgres_process_restart_recovery():
    """Verify mission workflow pauses, simulates process termination, and restores from PostgreSQL."""
    pool1, saver1 = await CheckpointerFactory.create_postgres_checkpointer(
        database_url=TEST_DB_URL,
        run_setup=True,
    )

    m_id = uuid4()
    org_id = uuid4()

    try:
        # Process A: Start mission, advance to interrupt, and halt
        engine1 = WorkflowOrchestrationEngine(checkpointer=saver1)
        result1 = await engine1.start_mission(
            mission_id=m_id,
            org_id=org_id,
            objective="Postgres Durable Checkpointing Verification",
        )
        assert "__interrupt__" in result1
        interrupt_payload = result1["__interrupt__"][0].value
        assert "action_digest" in interrupt_payload
    finally:
        await pool1.close()

    # Process B: Connect with fresh connection pool and fresh Engine instance
    pool2, saver2 = await CheckpointerFactory.create_postgres_checkpointer(
        database_url=TEST_DB_URL,
        run_setup=False,
    )

    try:
        engine2 = WorkflowOrchestrationEngine(checkpointer=saver2)

        # Inspect state directly from PostgreSQL
        state_snap = await engine2.get_mission_state(m_id)
        assert state_snap["values"]["mission_id"] == str(m_id)
        assert state_snap["values"]["domain_state"] == "AWAITING_APPROVAL"

        # Resume from Process B
        resume_payload = {
            "approval_id": interrupt_payload["approval_id"],
            "org_id": str(org_id),
            "user_id": str(uuid4()),
            "decision": "APPROVED",
            "action_digest": interrupt_payload["action_digest"],
        }
        resumed = await engine2.resume_approval(m_id, resume_payload)
        assert resumed["current_phase"] in {
            "READY",
            "TASK_SCHEDULING",
            "EXECUTION_COORDINATION",
            "INTEGRATION",
            "INDEPENDENT_VERIFICATION",
            "AWAITING_DELIVERY_APPROVAL",
            "COMPLETED",
        }
    finally:
        await pool2.close()
