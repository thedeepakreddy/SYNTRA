"""Phase 10 acceptance resources are isolated in a disposable PostgreSQL schema."""

import os
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from syntra.persistence.models import Base
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork


@dataclass
class IsolatedPhase10Database:
    uow_factory: Any = field(repr=False)
    checkpoint_url: str = field(repr=False)

    def __repr__(self):
        return "IsolatedPhase10Database(credentials=[REDACTED])"

    def __iter__(self):
        yield self.uow_factory
        yield self.checkpoint_url


@pytest.fixture
async def phase10_database():
    load_dotenv()
    url = os.environ.get("SYNTRA_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("BLOCKED_BY_DEPENDENCY: dedicated SYNTRA_TEST_POSTGRES_URL is required")
    parsed = make_url(url)
    if "test" not in (parsed.database or "").lower():
        raise ValueError("Phase 10 acceptance requires a dedicated test database")
    schema = "phase10_" + uuid4().hex
    admin = create_async_engine(url)
    scoped = None
    try:
        async with admin.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        scoped = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
        async with scoped.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(scoped, expire_on_commit=False)

        def uow_factory():
            return SqlAlchemyUnitOfWork(factory)

        checkpoint_url = parsed.set(
            drivername="postgresql", query={"options": f"-csearch_path={schema}"}
        ).render_as_string(hide_password=False)
        yield IsolatedPhase10Database(uow_factory, checkpoint_url)
    finally:
        if scoped:
            await scoped.dispose()
        async with admin.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await admin.dispose()
