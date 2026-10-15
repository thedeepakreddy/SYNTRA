"""Add Phase 4 MCP infrastructure: server trust, versioned tool snapshots, and invocations.

Revision ID: 0002_mcp_infrastructure
Revises: 0001_initial_schema
Create Date: 2026-10-15 02:26:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_mcp_infrastructure"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enhance mcp_servers
    op.add_column(
        "mcp_servers",
        sa.Column("trust_classification", sa.String(50), nullable=False, server_default="LOCAL_TRUSTED"),
    )
    op.add_column(
        "mcp_servers",
        sa.Column("auth_policy", sa.String(50), nullable=False, server_default="NONE"),
    )
    op.add_column(
        "mcp_servers",
        sa.Column("allowed_capabilities", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "mcp_servers",
        sa.Column("version", sa.String(50), nullable=False, server_default="1.0.0"),
    )
    op.add_column(
        "mcp_servers",
        sa.Column("verification_status", sa.String(50), nullable=False, server_default="VERIFIED"),
    )

    # 2. Enhance mcp_tool_versions
    op.add_column(
        "mcp_tool_versions",
        sa.Column("action_classification", sa.String(50), nullable=False, server_default="READ_ONLY"),
    )
    op.add_column(
        "mcp_tool_versions",
        sa.Column("sha256_checksum", sa.String(64), nullable=False, server_default=""),
    )

    # 3. Enhance capability_grants
    op.add_column(
        "capability_grants",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 4. Create mcp_invocations
    op.create_table(
        "mcp_invocations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "mission_id", sa.Uuid(as_uuid=True), sa.ForeignKey("missions.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("task_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("server_name", sa.String(100), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("caller_role", sa.String(100), nullable=False),
        sa.Column("caller_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("arguments_scrubbed", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, default="PENDING"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("result_hash", sa.String(64), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_mcp_invocations_org", "mcp_invocations", ["org_id"])
    op.create_index("idx_mcp_invocations_mission", "mcp_invocations", ["mission_id"])
    op.create_index("idx_mcp_invocations_task", "mcp_invocations", ["task_id"])


def downgrade() -> None:
    op.drop_table("mcp_invocations")
    op.drop_column("capability_grants", "expires_at")
    op.drop_column("mcp_tool_versions", "sha256_checksum")
    op.drop_column("mcp_tool_versions", "action_classification")
    op.drop_column("mcp_servers", "verification_status")
    op.drop_column("mcp_servers", "version")
    op.drop_column("mcp_servers", "allowed_capabilities")
    op.drop_column("mcp_servers", "auth_policy")
    op.drop_column("mcp_servers", "trust_classification")
