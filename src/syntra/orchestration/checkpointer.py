"""Durable LangGraph Checkpointing Factory & Thread Management.

Provides production PostgreSQL checkpointing using AsyncPostgresSaver and
in-memory fallback (MemorySaver) for offline unit testing and environments
where live PostgreSQL infrastructure is not provisioned.
"""

from __future__ import annotations

import logging
from typing import Any, cast
from uuid import UUID

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


def build_mission_thread_id(mission_id: UUID | str) -> str:
    """Build a deterministic, stable thread identifier for mission workflows."""
    clean_id = str(mission_id).strip()
    if clean_id.startswith("mission:"):
        return clean_id
    return f"mission:{clean_id}"


def build_task_thread_id(task_id: UUID | str) -> str:
    """Build a deterministic, stable thread identifier for task workflows."""
    clean_id = str(task_id).strip()
    if clean_id.startswith("task:"):
        return clean_id
    return f"task:{clean_id}"


def format_postgres_conn_string(url: str) -> str:
    """Convert SQLAlchemy asyncpg / sqlite URLs to psycopg-compatible PostgreSQL conninfo."""
    clean = url.strip()
    if clean.startswith("postgresql+asyncpg://"):
        clean = "postgresql://" + clean[len("postgresql+asyncpg://") :]
    elif clean.startswith("postgresql+psycopg://"):
        clean = "postgresql://" + clean[len("postgresql+psycopg://") :]
    return clean


class CheckpointerFactory:
    """Factory creating and managing PostgreSQL or Memory checkpointers."""

    @classmethod
    async def create_checkpointer(
        cls,
        conn_string: str | None = None,
        force_memory: bool = False,
        allow_fallback: bool = False,
    ) -> tuple[BaseCheckpointSaver, bool]:
        """Create a checkpointer.

        Returns:
            tuple[BaseCheckpointSaver, bool]: (checkpointer_instance, is_postgres_active)
        """
        if force_memory or not conn_string or "sqlite" in conn_string:
            logger.info("Using in-memory MemorySaver checkpointer")
            return MemorySaver(), False

        clean_dsn = format_postgres_conn_string(conn_string)

        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            from psycopg_pool import AsyncConnectionPool

            pool = AsyncConnectionPool(
                conninfo=clean_dsn,
                max_size=5,
                open=False,
                timeout=3.0,
                kwargs={"autocommit": True, "prepare_threshold": 0},
            )
            await pool.open()

            saver = AsyncPostgresSaver(conn=cast(Any, pool))
            await saver.setup()
            logger.info("Successfully initialized AsyncPostgresSaver with PostgreSQL pool")
            return saver, True

        except Exception as exc:
            if not allow_fallback:
                logger.error(
                    "Production PostgreSQL checkpointer initialization failed (%s). Refusing silent downgrade to MemorySaver.",
                    exc,
                )
                raise ConnectionError(
                    f"PostgreSQL checkpointer initialization failed: {exc}. "
                    "Refusing to silently downgrade to in-memory storage in production."
                ) from exc
            logger.warning(
                "PostgreSQL checkpointer initialization failed (%s). Falling back to MemorySaver.",
                exc,
            )
            return MemorySaver(), False

    @classmethod
    async def create_postgres_checkpointer(
        cls,
        database_url: str,
        run_setup: bool = True,
    ) -> tuple[Any, Any]:
        """Create a dedicated AsyncPostgresSaver and underlying connection pool."""
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from psycopg_pool import AsyncConnectionPool

        clean_dsn = format_postgres_conn_string(database_url)
        pool = AsyncConnectionPool(
            conninfo=clean_dsn,
            max_size=5,
            open=False,
            timeout=3.0,
            kwargs={"autocommit": True, "prepare_threshold": 0},
        )
        await pool.open()
        saver = AsyncPostgresSaver(conn=cast(Any, pool))
        if run_setup:
            await saver.setup()
        return pool, saver


def create_checkpoint_metadata(
    mission_id: str,
    phase: str,
    version: int = 1,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build structured checkpoint metadata without secret leakage."""
    meta: dict[str, Any] = {
        "mission_id": mission_id,
        "phase": phase,
        "version": version,
    }
    if extra:
        # Guarantee secrets are not stored in checkpoint metadata
        for k, v in extra.items():
            if "secret" not in k.lower() and "key" not in k.lower() and "token" not in k.lower():
                meta[k] = v
    return meta
