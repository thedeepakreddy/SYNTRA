"""Add verification_records table for independent cryptographic verification evidence.

Revision ID: 0005_independent_verification
Revises: 0004_memory_feedback
Create Date: 2026-10-20 02:50:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_independent_verification"
down_revision: Union[str, None] = "0004_memory_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "verification_records",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "mission_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("missions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "task_attempt_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("task_attempts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("plan_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(50), nullable=False, server_default="PASSED"),
        sa.Column("clean_base_commit", sa.String(64), nullable=False),
        sa.Column("patch_hash", sa.String(64), nullable=False),
        sa.Column("protected_test_suite_hash", sa.String(64), nullable=False),
        sa.Column("exit_code", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("execution_duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stdout_digest", sa.String(64), nullable=False),
        sa.Column("stderr_digest", sa.String(64), nullable=False),
        sa.Column("evidence_json", sa.Text(), nullable=False),
        sa.Column("verifier_signature", sa.String(64), nullable=False),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("span_id", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_verification_records_org_mission",
        "verification_records",
        ["org_id", "mission_id"],
    )
    op.create_index(
        "idx_verification_records_attempt",
        "verification_records",
        ["task_attempt_id"],
    )
    op.create_index(
        "idx_verification_records_patch_hash",
        "verification_records",
        ["patch_hash"],
    )
    op.create_index(
        "idx_verification_records_status",
        "verification_records",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("idx_verification_records_status", table_name="verification_records")
    op.drop_index("idx_verification_records_patch_hash", table_name="verification_records")
    op.drop_index("idx_verification_records_attempt", table_name="verification_records")
    op.drop_index("idx_verification_records_org_mission", table_name="verification_records")
    op.drop_table("verification_records")
