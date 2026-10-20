"""Add memory_feedback_events audit table for evidence-based confidence lifecycle.

Revision ID: 0004_memory_feedback
Revises: 0003_memory_embeddings
Create Date: 2026-10-20 01:05:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_memory_feedback"
down_revision: Union[str, None] = "0003_memory_embeddings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "memory_feedback_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "memory_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("memory_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "task_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "attempt_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("task_attempts.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "source_artifact_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("artifacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_artifact_version", sa.String(50), nullable=True),
        sa.Column("source_artifact_checksum", sa.String(64), nullable=True),
        sa.Column("patch_hash", sa.String(64), nullable=True),
        sa.Column("outcome", sa.String(50), nullable=False),
        sa.Column("confidence_delta", sa.Numeric(4, 2), nullable=False),
        sa.Column("resulting_confidence_score", sa.Numeric(4, 2), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_memory_feedback_org_memory",
        "memory_feedback_events",
        ["org_id", "memory_id"],
    )
    op.create_index(
        "idx_memory_feedback_task_attempt",
        "memory_feedback_events",
        ["task_id", "attempt_id"],
    )
    op.create_index(
        "idx_memory_feedback_idempotency",
        "memory_feedback_events",
        ["idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("idx_memory_feedback_idempotency", table_name="memory_feedback_events")
    op.drop_index("idx_memory_feedback_task_attempt", table_name="memory_feedback_events")
    op.drop_index("idx_memory_feedback_org_memory", table_name="memory_feedback_events")
    op.drop_table("memory_feedback_events")
