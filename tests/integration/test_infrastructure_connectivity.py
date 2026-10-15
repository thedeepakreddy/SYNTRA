"""Integration tests verifying PostgreSQL, Redis, and MinIO connectivity when Docker is available."""

import os
import shutil
import socket

import pytest
import redis.asyncio as aioredis
from minio import Minio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from syntra.core.config import get_settings

docker_installed = shutil.which("docker") is not None


def is_service_reachable(host: str, port: int) -> bool:
    try:
        sock = socket.socket()
        sock.settimeout(1.0)
        res = sock.connect_ex((host, port))
        sock.close()
        return res == 0
    except Exception:
        return False


postgres_available = is_service_reachable("127.0.0.1", 5432)
redis_available = is_service_reachable("127.0.0.1", 6379)
minio_available = is_service_reachable("127.0.0.1", 9000)


@pytest.mark.integration
@pytest.mark.skipif(not (postgres_available or docker_installed), reason="PostgreSQL service not reachable on 5432")
@pytest.mark.asyncio
async def test_containerized_postgres_connectivity():
    """Verify live PostgreSQL instance responds to queries."""
    settings = get_settings()
    db_url = settings.database_url
    if "sqlite" in db_url:
        db_url = os.environ.get(
            "SYNTRA_TEST_POSTGRES_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/syntra_test",
        )

    engine = create_async_engine(db_url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
    finally:
        await engine.dispose()


@pytest.mark.integration
@pytest.mark.skipif(not (redis_available or docker_installed), reason="Redis service not reachable on 6379")
@pytest.mark.asyncio
async def test_containerized_redis_connectivity():
    """Verify live Redis instance responds to PING."""
    settings = get_settings()
    client = aioredis.from_url(settings.redis_url, socket_connect_timeout=2.0)
    try:
        res = await client.ping()
        assert res is True
    finally:
        await client.aclose()


@pytest.mark.integration
@pytest.mark.skipif(not minio_available, reason="MinIO service / Docker is not available on host machine")
def test_containerized_minio_connectivity():
    """Verify live MinIO container responds to API requests."""
    settings = get_settings()
    endpoint = settings.s3_endpoint
    if "://" in endpoint:
        endpoint = endpoint.split("://")[1]

    client = Minio(
        endpoint=endpoint,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        secure=settings.s3_secure,
    )
    buckets = client.list_buckets()
    assert isinstance(buckets, list)
