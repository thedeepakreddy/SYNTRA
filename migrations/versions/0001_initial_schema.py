"""Initial schema migration establishing SYNTRA 30-table relational schema and legacy tables.

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-10-15 01:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. organizations
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_organizations_slug", "organizations", ["slug"])

    # 2. users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_service_account", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_users_email", "users", ["email"])

    # 3. memberships
    op.create_table(
        "memberships",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, default="engineer"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("org_id", "user_id", name="uq_membership_org_user"),
    )
    op.create_index("idx_memberships_org_id", "memberships", ["org_id"])
    op.create_index("idx_memberships_user_id", "memberships", ["user_id"])

    # 4. projects
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("org_id", "slug", name="uq_projects_org_slug"),
    )
    op.create_index("idx_projects_org_id", "projects", ["org_id"])

    # 5. repositories
    op.create_table(
        "repositories",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("clone_url", sa.Text(), nullable=False),
        sa.Column("default_branch", sa.String(100), nullable=False, default="main"),
        sa.Column("is_private", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "name", name="uq_repositories_project_name"),
    )
    op.create_index("idx_repositories_project_id", "repositories", ["project_id"])

    # 6. missions
    op.create_table(
        "missions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "repository_id", sa.Uuid(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("state", sa.String(50), nullable=False, default="DRAFT"),
        sa.Column("autonomy_mode", sa.String(50), nullable=False, default="semi_autonomous"),
        sa.Column("active_plan_version", sa.Integer(), nullable=False, default=1),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_missions_org_state", "missions", ["org_id", "state"])
    op.create_index("idx_missions_project_id", "missions", ["project_id"])

    # 7. requirements
    op.create_table(
        "requirements",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "mission_id", sa.Uuid(as_uuid=True), sa.ForeignKey("missions.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("identifier", sa.String(50), nullable=False),
        sa.Column("type", sa.String(50), nullable=False, default="functional"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("acceptance_criteria", sa.JSON(), nullable=False),
        sa.Column("is_ambiguous", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("mission_id", "identifier", name="uq_requirements_mission_identifier"),
    )
    op.create_index("idx_requirements_mission_id", "requirements", ["mission_id"])

    # 8. architecture_decisions
    op.create_table(
        "architecture_decisions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "mission_id", sa.Uuid(as_uuid=True), sa.ForeignKey("missions.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("adr_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, default="PROPOSED"),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("consequences", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("mission_id", "adr_number", name="uq_adr_mission_number"),
    )
    op.create_index("idx_adr_mission_id", "architecture_decisions", ["mission_id"])

    # 9. task_plans
    op.create_table(
        "task_plans",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "mission_id", sa.Uuid(as_uuid=True), sa.ForeignKey("missions.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("plan_version", sa.Integer(), nullable=False, default=1),
        sa.Column("status", sa.String(50), nullable=False, default="DRAFT"),
        sa.Column("total_tasks", sa.Integer(), nullable=False, default=0),
        sa.Column("estimated_tokens", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("mission_id", "plan_version", name="uq_task_plans_mission_version"),
    )
    op.create_index("idx_task_plans_mission", "task_plans", ["mission_id"])

    # 10. tasks
    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "task_plan_id", sa.Uuid(as_uuid=True), sa.ForeignKey("task_plans.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "mission_id", sa.Uuid(as_uuid=True), sa.ForeignKey("missions.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "org_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("identifier", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("assigned_role", sa.String(100), nullable=False),
        sa.Column("state", sa.String(50), nullable=False, default="PENDING"),
        sa.Column("priority", sa.Integer(), nullable=False, default=0),
        sa.Column("max_attempts", sa.Integer(), nullable=False, default=3),
        sa.Column("attempt_count", sa.Integer(), nullable=False, default=0),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("task_plan_id", "identifier", name="uq_tasks_plan_identifier"),
    )
    op.create_index("idx_tasks_mission_state", "tasks", ["mission_id", "state"])
    op.create_index("idx_tasks_org_state", "tasks", ["org_id", "state"])
    op.create_index("idx_tasks_plan_id", "tasks", ["task_plan_id"])

    # 11. task_dependencies
    op.create_table(
        "task_dependencies",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("task_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "depends_on_task_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependency"),
        sa.CheckConstraint("task_id <> depends_on_task_id", name="chk_no_self_dependency"),
    )
    op.create_index("idx_task_dependencies_task_id", "task_dependencies", ["task_id"])
    op.create_index("idx_task_dependencies_depends_on", "task_dependencies", ["depends_on_task_id"])

    # 12. task_attempts
    op.create_table(
        "task_attempts",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("task_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(50), nullable=False, default="INITIALIZING"),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("task_id", "attempt_number", name="uq_task_attempt_number"),
    )
    op.create_index("idx_task_attempts_task_id", "task_attempts", ["task_id"])

    # 13. agent_executions
    op.create_table(
        "agent_executions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "task_attempt_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("task_attempts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent_role", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, default=0),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, default=0),
        sa.Column("total_cost_usd", sa.Numeric(10, 6), nullable=False, default=0.000000),
        sa.Column("duration_ms", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_agent_executions_attempt", "agent_executions", ["task_attempt_id"])

    # 14. sandbox_jobs
    op.create_table(
        "sandbox_jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "task_attempt_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("task_attempts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("worker_id", sa.String(100), nullable=False),
        sa.Column("workspace_path", sa.Text(), nullable=False),
        sa.Column("git_worktree_branch", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, default="PROVISIONING"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, default=120),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("terminated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_sandbox_jobs_attempt", "sandbox_jobs", ["task_attempt_id"])
    op.create_index("idx_sandbox_jobs_worker", "sandbox_jobs", ["worker_id"])

    # 15. worker_leases
    op.create_table(
        "worker_leases",
        sa.Column("task_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("worker_id", sa.String(100), nullable=False),
        sa.Column("fencing_token", sa.BigInteger(), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_worker_leases_expires_at", "worker_leases", ["lease_expires_at"])

    # 16. artifacts
    op.create_table(
        "artifacts",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "mission_id", sa.Uuid(as_uuid=True), sa.ForeignKey("missions.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("task_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_artifacts_mission_type", "artifacts", ["mission_id", "type"])

    # 17. artifact_versions
    op.create_table(
        "artifact_versions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "artifact_id", sa.Uuid(as_uuid=True), sa.ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("sha256_checksum", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("artifact_id", "version", name="uq_artifact_version"),
    )
    op.create_index("idx_artifact_versions_artifact", "artifact_versions", ["artifact_id"])

    # 18. verification_runs
    op.create_table(
        "verification_runs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("task_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "artifact_version_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("verdict", sa.String(50), nullable=False, default="PASS"),
        sa.Column("tests_passed", sa.Integer(), nullable=False, default=0),
        sa.Column("tests_failed", sa.Integer(), nullable=False, default=0),
        sa.Column("coverage_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("raw_output", sa.Text(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_verification_runs_task", "verification_runs", ["task_id"])

    # 19. mcp_servers
    op.create_table(
        "mcp_servers",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("transport", sa.String(50), nullable=False, default="stdio"),
        sa.Column("command_or_url", sa.Text(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 20. mcp_tool_versions
    op.create_table(
        "mcp_tool_versions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "mcp_server_id", sa.Uuid(as_uuid=True), sa.ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("version", sa.String(50), nullable=False, default="1.0.0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("input_schema", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("mcp_server_id", "tool_name", "version", name="uq_tool_server_name_version"),
    )
    op.create_index("idx_tool_versions_server", "mcp_tool_versions", ["mcp_server_id"])

    # 21. skills
    op.create_table(
        "skills",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 22. skill_versions
    op.create_table(
        "skill_versions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("skill_id", sa.Uuid(as_uuid=True), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("manifest_yaml", sa.Text(), nullable=False),
        sa.Column("instruction_markdown", sa.Text(), nullable=False),
        sa.Column("compatible_roles", sa.JSON(), nullable=False),
        sa.Column("required_tools", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("skill_id", "version", name="uq_skill_version"),
    )
    op.create_index("idx_skill_versions_skill", "skill_versions", ["skill_id"])

    # 23. capability_grants
    op.create_table(
        "capability_grants",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("agent_role", sa.String(100), nullable=False),
        sa.Column("tool_name_pattern", sa.String(255), nullable=False),
        sa.Column("is_allowed", sa.Boolean(), nullable=False, default=True),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_capability_grants_org_role", "capability_grants", ["org_id", "agent_role"])

    # 24. human_approvals
    op.create_table(
        "human_approvals",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "mission_id", sa.Uuid(as_uuid=True), sa.ForeignKey("missions.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("task_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("action_digest", sa.String(64), nullable=False),
        sa.Column("decision", sa.String(50), nullable=False, default="PENDING"),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_human_approvals_mission_decision", "human_approvals", ["mission_id", "decision"])

    # 25. budgets
    op.create_table(
        "budgets",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("mission_id", sa.Uuid(as_uuid=True), sa.ForeignKey("missions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("max_tokens", sa.BigInteger(), nullable=False, default=1000000),
        sa.Column("max_cost_usd", sa.Numeric(10, 4), nullable=False, default=50.0000),
        sa.Column("reserved_tokens", sa.BigInteger(), nullable=False, default=0),
        sa.Column("consumed_tokens", sa.BigInteger(), nullable=False, default=0),
        sa.Column("consumed_cost_usd", sa.Numeric(10, 4), nullable=False, default=0.0000),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("mission_id", name="uq_budgets_mission"),
    )
    op.create_index("idx_budgets_org", "budgets", ["org_id"])

    # 26. usage_records
    op.create_table(
        "usage_records",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "mission_id", sa.Uuid(as_uuid=True), sa.ForeignKey("missions.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("task_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, default=0),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, default=0),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False, default=0.000000),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_usage_records_org_mission", "usage_records", ["org_id", "mission_id"])

    # 27. events
    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("mission_id", sa.Uuid(as_uuid=True), sa.ForeignKey("missions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("actor_type", sa.String(50), nullable=False, default="system"),
        sa.Column("actor_id", sa.String(100), nullable=False, default="orchestrator"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_events_mission", "events", ["mission_id", "created_at"])
    op.create_index("idx_events_type", "events", ["event_type"])

    # 28. transactional_outbox
    op.create_table(
        "transactional_outbox",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, default="PENDING"),
        sa.Column("retry_count", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_outbox_pending", "transactional_outbox", ["status", "created_at"])

    # 29. idempotency_keys
    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.String(255), primary_key=True),
        sa.Column(
            "org_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("response_code", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_idempotency_expires", "idempotency_keys", ["expires_at"])

    # 30. memory_records
    op.create_table(
        "memory_records",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("project_id", sa.Uuid(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("scope", sa.String(50), nullable=False, default="ORGANIZATION"),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("lesson_key", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "provenance_task_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("confidence_score", sa.Numeric(3, 2), nullable=False, default=1.00),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_memory_records_org_scope", "memory_records", ["org_id", "scope", "category"])

    # Legacy support tables
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, default="pending"),
        sa.Column("autonomy_mode", sa.String(32), nullable=False, default="semi_autonomous"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
    )
    op.create_table(
        "checkpoints",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("session_id", sa.String(64), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.String(64), nullable=False),
        sa.Column("agent_role", sa.String(32), nullable=False),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("risk_level", sa.String(16), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("proposed_diff", sa.Text(), nullable=True),
        sa.Column("proposed_command", sa.Text(), nullable=True),
        sa.Column("target_path", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, default="pending"),
        sa.Column("human_feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "legacy_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("session_id", sa.String(64), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("agent_id", sa.String(64), nullable=True),
        sa.Column("agent_role", sa.String(32), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("data_json", sa.Text(), nullable=True),
    )
    op.create_table(
        "legacy_artifacts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(64), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_path", sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "legacy_agent_executions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(64), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.String(64), nullable=False),
        sa.Column("agent_role", sa.String(32), nullable=False),
        sa.Column("task_prompt", sa.Text(), nullable=False),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("steps_taken", sa.Integer(), nullable=False, default=0),
        sa.Column("tool_calls_count", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    # Drop legacy tables
    op.drop_table("legacy_agent_executions")
    op.drop_table("legacy_artifacts")
    op.drop_table("legacy_events")
    op.drop_table("checkpoints")
    op.drop_table("sessions")

    # Drop in reverse order of foreign key dependencies
    op.drop_table("memory_records")
    op.drop_table("idempotency_keys")
    op.drop_table("transactional_outbox")
    op.drop_table("events")
    op.drop_table("usage_records")
    op.drop_table("budgets")
    op.drop_table("human_approvals")
    op.drop_table("capability_grants")
    op.drop_table("skill_versions")
    op.drop_table("skills")
    op.drop_table("mcp_tool_versions")
    op.drop_table("mcp_servers")
    op.drop_table("verification_runs")
    op.drop_table("artifact_versions")
    op.drop_table("artifacts")
    op.drop_table("worker_leases")
    op.drop_table("sandbox_jobs")
    op.drop_table("agent_executions")
    op.drop_table("task_attempts")
    op.drop_table("task_dependencies")
    op.drop_table("tasks")
    op.drop_table("task_plans")
    op.drop_table("architecture_decisions")
    op.drop_table("requirements")
    op.drop_table("missions")
    op.drop_table("repositories")
    op.drop_table("projects")
    op.drop_table("memberships")
    op.drop_table("users")
    op.drop_table("organizations")
