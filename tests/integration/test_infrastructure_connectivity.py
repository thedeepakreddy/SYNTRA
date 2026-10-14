"""Integration tests verifying PostgreSQL, Redis, and MinIO connectivity when Docker is available."""

import shutil

import pytest
import redis.asyncio as aioredis
from minio import Minio
from sqlalchemy import text

from syntra.core.config import get_settings
from syntra.storage.database import get_db_manager

docker_installed = shutil.which("docker") is not None


@pytest.mark.integration
@pytest.mark.docker
@pytest.mark.skipif(not docker_installed, reason="Docker is not installed on host machine")
@pytest.mark.asyncio
async def test_containerized_postgres_connectivity():
    """Verify live PostgreSQL container responds to queries."""
    settings = get_settings()
    if "sqlite" in settings.database_url:
        pytest.skip("Test requires PostgreSQL connection string in SYNTRA_DATABASE_URL")

    db = get_db_manager()
    async with db.session() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.integration
@pytest.mark.docker
@pytest.mark.skipif(not docker_installed, reason="Docker is not installed on host machine")
@pytest.mark.asyncio
async def test_containerized_redis_connectivity():
    """Verify live Redis container responds to PING."""
    settings = get_settings()
    client = aioredis.from_url(settings.redis_url, socket_connect_timeout=2.0)
    try:
        res = await client.ping()
        assert res is True
    finally:
        await client.aclose()


@pytest.mark.integration
@pytest.mark.docker
@pytest.mark.skipif(not docker_installed, reason="Docker is not installed on host machine")
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
