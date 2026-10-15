"""Redis Streams durable dispatch publisher, consumer groups, and acknowledgment engine.

Implements at-least-once task dispatch notifications using XADD, XREADGROUP, XACK,
and XAUTOCLAIM. Redis is strictly a notification transport; PostgreSQL remains the
authoritative record of truth.
"""

from __future__ import annotations

import logging
from typing import Any

import redis.asyncio as aioredis

from syntra.scheduling.exceptions import RedisStreamError
from syntra.scheduling.models import TaskDispatchPayload

logger = logging.getLogger(__name__)


class RedisTaskDispatcher:
    """Manages stream publishing, consumer groups, and delivery acknowledgments on Redis Streams."""

    STREAM_KEY = "syntra:task_dispatch"
    CONSUMER_GROUP = "syntra_workers"

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        stream_key: str | None = None,
        consumer_group: str | None = None,
    ) -> None:
        self.redis_url = redis_url
        self.stream_key = stream_key or self.STREAM_KEY
        self.consumer_group = consumer_group or self.CONSUMER_GROUP
        self._client: aioredis.Redis | None = None

    async def get_client(self) -> aioredis.Redis:
        """Get or initialize the underlying async Redis client."""
        if self._client is None:
            self._client = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=3.0,
            )
        return self._client

    async def close(self) -> None:
        """Close connection to Redis."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def ensure_consumer_group(self) -> None:
        """Ensure consumer group exists on the stream using MKSTREAM."""
        client = await self.get_client()
        try:
            await client.xgroup_create(
                name=self.stream_key,
                groupname=self.consumer_group,
                id="0",
                mkstream=True,
            )
            logger.info("Created consumer group '%s' on stream '%s'", self.consumer_group, self.stream_key)
        except aioredis.ResponseError as exc:
            if "BUSYGROUP" in str(exc):
                # Consumer group already exists - expected in restart/multi-worker topologies
                pass
            else:
                logger.error("Failed to initialize consumer group: %s", exc)
                raise RedisStreamError(f"Failed to create consumer group: {exc}") from exc

    async def publish_dispatch(self, payload: TaskDispatchPayload) -> str:
        """Publish a task dispatch notification to Redis Streams (XADD)."""
        client = await self.get_client()
        try:
            fields = {
                "dispatch_id": str(payload.dispatch_id),
                "task_id": str(payload.task_id),
                "mission_id": str(payload.mission_id),
                "org_id": str(payload.org_id),
                "fencing_token": str(payload.fencing_token),
                "assigned_role": payload.assigned_role,
                "payload_json": payload.model_dump_json(),
            }
            message_id = await client.xadd(self.stream_key, fields)  # type: ignore[arg-type]
            logger.info(
                "Published dispatch message %s for task %s (fencing_token=%d)",
                message_id,
                payload.task_id,
                payload.fencing_token,
            )
            return str(message_id)
        except Exception as exc:
            logger.error("Failed to publish dispatch to Redis stream: %s", exc)
            raise RedisStreamError(f"Redis XADD failed: {exc}") from exc

    async def read_dispatches(
        self,
        consumer_name: str,
        count: int = 1,
        block_ms: int = 2000,
    ) -> list[tuple[str, TaskDispatchPayload]]:
        """Read batch of new unconsumed dispatch messages for a worker consumer (XREADGROUP)."""
        await self.ensure_consumer_group()
        client = await self.get_client()
        try:
            raw_entries: Any = await client.xreadgroup(
                groupname=self.consumer_group,
                consumername=consumer_name,
                streams={self.stream_key: ">"},
                count=count,
                block=block_ms,
            )

            dispatches: list[tuple[str, TaskDispatchPayload]] = []
            if not raw_entries:
                return dispatches

            for _stream_name, messages in raw_entries:
                for msg_id, fields in messages:
                    try:
                        if isinstance(fields, dict):
                            raw_payload = fields.get("payload_json")
                            if raw_payload:
                                payload = TaskDispatchPayload.model_validate_json(raw_payload)
                                dispatches.append((str(msg_id), payload))
                    except Exception as parse_exc:
                        logger.warning("Skipping malformed stream message %s: %s", msg_id, parse_exc)

            return dispatches
        except Exception as exc:
            logger.error("Failed to read dispatches from Redis stream: %s", exc)
            raise RedisStreamError(f"Redis XREADGROUP failed: {exc}") from exc

    async def acknowledge_dispatch(self, message_id: str) -> bool:
        """Acknowledge successful authoritative persistence and processing of a dispatch (XACK)."""
        client = await self.get_client()
        try:
            ack_count = await client.xack(self.stream_key, self.consumer_group, message_id)
            return bool(ack_count > 0)
        except Exception as exc:
            logger.error("Failed to acknowledge message %s: %s", message_id, exc)
            raise RedisStreamError(f"Redis XACK failed: {exc}") from exc

    async def reclaim_abandoned_messages(
        self,
        consumer_name: str,
        min_idle_ms: int = 60000,
        count: int = 10,
    ) -> list[tuple[str, TaskDispatchPayload]]:
        """Reclaim pending unacknowledged messages from stalled workers (XAUTOCLAIM)."""
        await self.ensure_consumer_group()
        client = await self.get_client()
        try:
            # xautoclaim returns (next_start_id, [(msg_id, fields), ...], [deleted_ids])
            result: Any = await client.xautoclaim(
                name=self.stream_key,
                groupname=self.consumer_group,
                consumername=consumer_name,
                min_idle_time=min_idle_ms,
                start_id="0-0",
                count=count,
            )
            reclaimed: list[tuple[str, TaskDispatchPayload]] = []
            if result and len(result) >= 2:
                for msg_id, fields in result[1]:
                    if isinstance(fields, dict):
                        raw_payload = fields.get("payload_json")
                        if raw_payload:
                            payload = TaskDispatchPayload.model_validate_json(raw_payload)
                            reclaimed.append((str(msg_id), payload))

            return reclaimed
        except Exception as exc:
            logger.error("Failed to autoclaim pending messages: %s", exc)
            raise RedisStreamError(f"Redis XAUTOCLAIM failed: {exc}") from exc
