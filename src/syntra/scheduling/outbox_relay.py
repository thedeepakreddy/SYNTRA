"""Transactional Outbox Relay for Task Dispatch Notifications.

Bridges PostgreSQL transactional state with Redis Streams delivery, guaranteeing
at-least-once delivery without dual-write inconsistencies.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from syntra.domain.entities import OutboxStatus
from syntra.persistence.models import TransactionalOutboxModel
from syntra.scheduling.models import TaskDispatchPayload
from syntra.scheduling.redis_dispatcher import RedisTaskDispatcher

logger = logging.getLogger(__name__)


class OutboxRelay:
    """Polls transactional outbox records and publishes dispatch notifications to Redis Streams."""

    MAX_RETRIES = 5

    def __init__(
        self,
        uow_factory: Any,
        dispatcher: RedisTaskDispatcher,
    ) -> None:
        self.uow_factory = uow_factory
        self.dispatcher = dispatcher

    async def relay_batch(self, batch_size: int = 50, limit: int | None = None) -> int:
        """Poll pending outbox events, publish to Redis Streams, and update status atomically."""
        effective_limit = limit if limit is not None else batch_size
        relayed_count = 0

        async with self.uow_factory() as uow:
            pending_events = list(
                (
                    await uow.session.execute(
                        select(TransactionalOutboxModel)
                        .where(
                            TransactionalOutboxModel.status == OutboxStatus.PENDING,
                            TransactionalOutboxModel.event_type == "TASK_DISPATCHED",
                        )
                        .order_by(TransactionalOutboxModel.created_at)
                        .limit(effective_limit)
                        .with_for_update(skip_locked=True)
                    )
                )
                .scalars()
                .all()
            )
            if not pending_events:
                return 0

            for event in pending_events:
                if not event.event_type.startswith("TASK_DISPATCH"):
                    continue

                try:
                    payload = TaskDispatchPayload.model_validate(event.payload)
                    await self.dispatcher.publish_dispatch(payload)

                    event.status = OutboxStatus.PROCESSED
                    event.processed_at = datetime.now(UTC)
                    relayed_count += 1

                except Exception as exc:
                    logger.error("Failed to relay outbox event %s: %s", event.id, exc)
                    event.retry_count += 1
                    if event.retry_count >= self.MAX_RETRIES:
                        event.status = OutboxStatus.FAILED
                        logger.error(
                            "Outbox event %s reached max retries (%d). Marked FAILED.", event.id, self.MAX_RETRIES
                        )

            await uow.commit()

        return relayed_count
