"""SQLAlchemy models for persistent storage of sessions, checkpoints, events, and artifacts.

Maintains backward-compatibility for Phase 1 session prototype while authoritative
domain models reside in syntra.persistence.models (ADR-007).
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from syntra.storage.database import Base


class SessionModel(Base):
    """Represents a SYNTRA multi-agent engineering session (prototype)."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    autonomy_mode: Mapped[str] = mapped_column(String(32), default="semi_autonomous", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    executions: Mapped[list["LegacyAgentExecutionModel"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    checkpoints: Mapped[list["CheckpointModel"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    events: Mapped[list["LegacyEventModel"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    artifacts: Mapped[list["LegacyArtifactModel"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class LegacyAgentExecutionModel(Base):
    """Logs individual agent steps and tasks (legacy prototype)."""

    __tablename__ = "legacy_agent_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_role: Mapped[str] = mapped_column(String(32), nullable=False)
    task_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    steps_taken: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tool_calls_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    session: Mapped["SessionModel"] = relationship(back_populates="executions")


class CheckpointModel(Base):
    """Stores human-in-the-loop checkpoint decisions and states (legacy prototype)."""

    __tablename__ = "checkpoints"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_role: Mapped[str] = mapped_column(String(32), nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_diff: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_command: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    human_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    session: Mapped["SessionModel"] = relationship(back_populates="checkpoints")


class LegacyEventModel(Base):
    """Audit trail log of all system and agent events (legacy prototype)."""

    __tablename__ = "legacy_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)
    data_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped["SessionModel | None"] = relationship(back_populates="events")


class LegacyArtifactModel(Base):
    """Files and deliverables produced by swarms (legacy prototype)."""

    __tablename__ = "legacy_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    session: Mapped["SessionModel"] = relationship(back_populates="artifacts")


# Backwards compatibility aliases
AgentExecutionModel = LegacyAgentExecutionModel
EventModel = LegacyEventModel
ArtifactModel = LegacyArtifactModel
