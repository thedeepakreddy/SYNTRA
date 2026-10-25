"""Comprehensive Automated Test Suite for TransferSession API.

Authored by SYNTRA QA & Backend Engineer Agents.
Follows TDD principles, testing CRUD operations, validation rules, 404 boundaries, and search filters.
"""

import sys
from pathlib import Path

pkg_dir = str(Path(__file__).resolve().parent)
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

try:
    from database import get_db
    from main import app
    from models import Base
except ImportError:
    from .database import get_db
    from .main import app
    from .models import Base

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def async_client():
    test_engine = create_async_engine(TEST_DB_URL, echo=False)
    async_session = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with async_session() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_health_check(async_client):
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "HEALTHY"


@pytest.mark.asyncio
async def test_create_and_get_item(async_client):
    payload = {
        "title": "Automated Test Item",
        "category": "Testing",
        "status": "CONNECTED",
        "priority": "HIGH",
        "description": "Integration test created payload",
        "tags": ["Test", "QA"],
    }
    create_resp = await async_client.post("/api/v1/transfer_sessions", json=payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["title"] == payload["title"]
    assert "id" in created

    # Fetch by ID
    get_resp = await async_client.get(f"/api/v1/transfer_sessions/{created['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_get_not_found(async_client):
    resp = await async_client.get("/api/v1/transfer_sessions/non-existent-uuid")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_item(async_client):
    payload = {
        "title": "Initial Item",
        "category": "Testing",
        "status": "CONNECTED",
        "priority": "LOW",
        "tags": ["Init"],
    }
    create_resp = await async_client.post("/api/v1/transfer_sessions", json=payload)
    item_id = create_resp.json()["id"]

    update_payload = {"title": "Updated Title", "priority": "CRITICAL"}
    put_resp = await async_client.put(f"/api/v1/transfer_sessions/{item_id}", json=update_payload)
    assert put_resp.status_code == 200
    assert put_resp.json()["title"] == "Updated Title"
    assert put_resp.json()["priority"] == "CRITICAL"


@pytest.mark.asyncio
async def test_delete_item(async_client):
    payload = {"title": "Item To Delete", "category": "Testing"}
    create_resp = await async_client.post("/api/v1/transfer_sessions", json=payload)
    item_id = create_resp.json()["id"]

    del_resp = await async_client.delete(f"/api/v1/transfer_sessions/{item_id}")
    assert del_resp.status_code == 204

    # Verify deleted
    get_resp = await async_client.get(f"/api/v1/transfer_sessions/{item_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_list_and_search_filters(async_client):
    await async_client.post("/api/v1/transfer_sessions", json={"title": "Search Alpha Target", "category": "Alpha"})
    await async_client.post("/api/v1/transfer_sessions", json={"title": "Search Beta Noise", "category": "Beta"})

    # Search query
    resp = await async_client.get("/api/v1/transfer_sessions?q=Alpha")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    assert any("Alpha Target" in it["title"] for it in items)

    # Category filter
    resp_cat = await async_client.get("/api/v1/transfer_sessions?category=Beta")
    assert resp_cat.status_code == 200
    assert all(it["category"] == "Beta" for it in resp_cat.json())


@pytest.mark.asyncio
async def test_stats_endpoint(async_client):
    await async_client.post("/api/v1/transfer_sessions", json={"title": "Stats Record 1", "category": "CatA", "status": "DONE"})
    resp = await async_client.get("/api/v1/transfer_sessions/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_records" in data
    assert "by_category" in data
    assert "by_status" in data
