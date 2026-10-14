"""Database repositories for CRUD operations on sessions, checkpoints, and events."""

import json
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from syntra.checkpoints.models import Checkpoint
from syntra.core.events import Event
from syntra.storage.models import (
    CheckpointModel,
    EventModel,
    SessionModel,
)


class SessionRepository:
    """Data access for engineering sessions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        session_id: str,
        objective: str,
        autonomy_mode: str = "semi_autonomous",
        metadata: dict | None = None,
    ) -> SessionModel:
        """Create a new session record."""
        now = datetime.now(UTC)
        record = SessionModel(
            id=session_id,
            objective=objective,
            status="running",
            autonomy_mode=autonomy_mode,
            metadata_json=json.dumps(metadata or {}),
            created_at=now,
            updated_at=now,
        )
        self.session.add(record)
        return record

    async def get_by_id(self, session_id: str) -> SessionModel | None:
        """Retrieve a session by its unique ID."""
        stmt = select(SessionModel).where(SessionModel.id == session_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_recent(self, limit: int = 50) -> list[SessionModel]:
        """List sessions ordered by update time."""
        stmt = select(SessionModel).order_by(SessionModel.updated_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, session_id: str, status: str) -> None:
        """Update session status."""
        stmt = (
            update(SessionModel)
            .where(SessionModel.id == session_id)
            .values(status=status, updated_at=datetime.now(UTC))
        )
        await self.session.execute(stmt)


class CheckpointRepository:
    """Data access for hybrid autonomy checkpoints."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, cp: Checkpoint) -> CheckpointModel:
        """Save a checkpoint instance."""
        record = CheckpointModel(
            id=cp.checkpoint_id,
            session_id=cp.session_id,
            agent_id=cp.agent_id,
            agent_role=cp.agent_role,
            action_type=cp.action_type.value,
            risk_level=cp.risk_level.value,
            description=cp.description,
            proposed_diff=cp.proposed_diff,
            proposed_command=cp.proposed_command,
            target_path=cp.target_path,
            status=cp.status.value,
            human_feedback=cp.human_feedback,
            created_at=cp.created_at,
            resolved_at=cp.resolved_at,
        )
        self.session.add(record)
        return record

    async def get_by_id(self, checkpoint_id: str) -> CheckpointModel | None:
        """Fetch checkpoint by ID."""
        stmt = select(CheckpointModel).where(CheckpointModel.id == checkpoint_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_session(
        self,
        session_id: str,
        status: str | None = None,
    ) -> list[CheckpointModel]:
        """List checkpoints for a session."""
        stmt = select(CheckpointModel).where(CheckpointModel.session_id == session_id)
        if status:
            stmt = stmt.where(CheckpointModel.status == status)
        stmt = stmt.order_by(CheckpointModel.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        checkpoint_id: str,
        status: str,
        feedback: str | None = None,
    ) -> None:
        """Update checkpoint status and optional feedback."""
        stmt = (
            update(CheckpointModel)
            .where(CheckpointModel.id == checkpoint_id)
            .values(
                status=status,
                human_feedback=feedback,
                resolved_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)


class EventRepository:
    """Data access for audit events."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log_event(self, event: Event) -> EventModel:
        """Insert event record."""
        record = EventModel(
            id=event.event_id,
            event_type=event.type.value,
            session_id=event.session_id,
            agent_id=event.agent_id,
            agent_role=event.agent_role,
            timestamp=event.timestamp,
            data_json=json.dumps(event.data),
        )
        self.session.add(record)
        return record

    async def list_for_session(self, session_id: str, limit: int = 100) -> list[EventModel]:
        """List events for session."""
        stmt = (
            select(EventModel)
            .where(EventModel.session_id == session_id)
            .order_by(EventModel.timestamp.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
