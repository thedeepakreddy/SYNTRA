"""Tests verifying Alembic database migrations: upgrade to head, schema consistency, and safe downgrade."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_migration_lifecycle(tmp_path: Path):
    """Verify fresh migration upgrade to head, schema inspection, downgrade to base, and re-upgrade."""
    db_file = tmp_path / "test_migration.db"
    db_url = f"sqlite:///{db_file}"

    # Prepare Alembic config
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    # 1. Fresh database upgrade to head
    command.upgrade(alembic_cfg, "head")

    # 2. Inspect tables in the freshly migrated database
    engine = create_engine(db_url)
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # Verify authoritative 30 tables are present
    expected_authoritative_tables = [
        "organizations",
        "users",
        "memberships",
        "projects",
        "repositories",
        "missions",
        "requirements",
        "architecture_decisions",
        "task_plans",
        "tasks",
        "task_dependencies",
        "task_attempts",
        "agent_executions",
        "sandbox_jobs",
        "worker_leases",
        "artifacts",
        "artifact_versions",
        "verification_runs",
        "mcp_servers",
        "mcp_tool_versions",
        "skills",
        "skill_versions",
        "capability_grants",
        "human_approvals",
        "budgets",
        "usage_records",
        "events",
        "transactional_outbox",
        "idempotency_keys",
        "memory_records",
    ]
    for table_name in expected_authoritative_tables:
        assert table_name in tables, f"Expected table '{table_name}' was not created by Alembic migration."

    # 3. Test downgrade to base
    command.downgrade(alembic_cfg, "base")

    inspector_after_downgrade = inspect(engine)
    tables_after = inspector_after_downgrade.get_table_names()
    # Only alembic_version should remain
    for table_name in expected_authoritative_tables:
        assert table_name not in tables_after, f"Table '{table_name}' was not dropped during downgrade."

    # 4. Re-upgrade to head
    command.upgrade(alembic_cfg, "head")
    inspector_reup = inspect(engine)
    re_tables = inspector_reup.get_table_names()
    assert "missions" in re_tables
    assert "tasks" in re_tables

    engine.dispose()
