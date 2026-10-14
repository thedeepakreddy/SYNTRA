"""Tests for DevSwarm storage and persistence repositories."""

import pytest
from devswarm.checkpoints.models import Checkpoint, CheckpointActionType, RiskLevel
from devswarm.core.events import Event, EventType
from devswarm.storage import (
    CheckpointRepository,
    DatabaseManager,
    EventRepository,
    SessionRepository,
)


@pytest.mark.asyncio
async def test_database_and_repositories():
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.init_tables()

    async with db.session() as session:
        session_repo = SessionRepository(session)
        cp_repo = CheckpointRepository(session)
        event_repo = EventRepository(session)

        # 1. Create Session
        sess_rec = await session_repo.create(
            session_id="test-session-123",
            objective="Build microservice",
            autonomy_mode="semi_autonomous",
        )
        assert sess_rec.id == "test-session-123"

        # 2. Save Checkpoint
        cp = Checkpoint(
            session_id="test-session-123",
            agent_id="coder-1",
            agent_role="coder",
            action_type=CheckpointActionType.COMMAND_EXECUTION,
            description="Run database migration",
            risk_level=RiskLevel.HIGH,
            proposed_command="alembic upgrade head",
        )
        cp_rec = await cp_repo.save(cp)
        assert cp_rec.id == cp.checkpoint_id

        # 3. Log Event
        ev = Event(
            type=EventType.TASK_STARTED,
            session_id="test-session-123",
            data={"task": "Initialize DB"},
        )
        ev_rec = await event_repo.log_event(ev)
        assert ev_rec.id == ev.event_id

    # Verify retrieval in separate transaction
    async with db.session() as session:
        session_repo = SessionRepository(session)
        cp_repo = CheckpointRepository(session)
        event_repo = EventRepository(session)

        fetched_sess = await session_repo.get_by_id("test-session-123")
        assert fetched_sess is not None
        assert fetched_sess.objective == "Build microservice"

        # Update status
        await session_repo.update_status("test-session-123", "completed")
        updated_sess = await session_repo.get_by_id("test-session-123")
        assert updated_sess.status == "completed"

        # List checkpoints
        checkpoints = await cp_repo.list_for_session("test-session-123")
        assert len(checkpoints) == 1
        assert checkpoints[0].risk_level == "high"

        # Update checkpoint
        await cp_repo.update_status(cp.checkpoint_id, "approved", "Approved by lead")
        updated_cp = await cp_repo.get_by_id(cp.checkpoint_id)
        assert updated_cp.status == "approved"
        assert updated_cp.human_feedback == "Approved by lead"

        # List events
        events = await event_repo.list_for_session("test-session-123")
        assert len(events) == 1
        assert events[0].event_type == EventType.TASK_STARTED.value

    await db.close()
