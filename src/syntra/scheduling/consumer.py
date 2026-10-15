"""Redis notifications enter the existing authoritative scheduler and sandbox adapter."""

import asyncio
from contextlib import suppress
from typing import Any

from syntra.scheduling.exceptions import StaleLeaseError
from syntra.scheduling.models import TaskDispatchPayload, TaskExecutionResult
from syntra.scheduling.reconciliation import SchedulerReconciler
from syntra.scheduling.redis_dispatcher import RedisTaskDispatcher
from syntra.scheduling.scheduler import TaskScheduler


class SandboxWorkerConsumer:
    def __init__(
        self,
        scheduler: TaskScheduler,
        dispatcher: RedisTaskDispatcher,
        adapter: Any,
        worker_id: str,
        heartbeat_seconds: float = 5.0,
    ) -> None:
        if adapter.worker_id != worker_id:
            raise ValueError("Adapter identity must match consumer identity")
        self.scheduler, self.dispatcher, self.adapter = scheduler, dispatcher, adapter
        self.worker_id, self.heartbeat_seconds = worker_id, heartbeat_seconds

    async def process(self, message_id: str, dispatch: TaskDispatchPayload, **trusted_options: Any) -> bool:
        accepts = getattr(self.adapter, "can_accept_dispatch", None)
        if accepts is not None and not await accepts(dispatch):
            return False
        if not await self.scheduler.begin_dispatch(dispatch, self.worker_id):
            # Reclaim can legitimately arrive after the notification's lease.
            # Persist recovery and its new outbox dispatch before ACKing the old
            # message, rather than leaving an ASSIGNED task without a wakeup.
            recovery = await SchedulerReconciler(self.scheduler.uow_factory).reconcile_mission(
                dispatch.mission_id, dispatch.org_id
            )
            if recovery.recovered_attempts_count:
                await self.scheduler.schedule_ready_tasks(dispatch.mission_id, dispatch.org_id)
            await self.dispatcher.acknowledge_dispatch(message_id)
            return False

        async def guard() -> None:
            await self.scheduler.assert_dispatch_active(dispatch, self.worker_id)

        async def heartbeat() -> None:
            while True:
                await asyncio.sleep(self.heartbeat_seconds)
                await self.scheduler.assert_dispatch_active(dispatch, self.worker_id, renew=True)

        runner = asyncio.create_task(self.adapter.execute_task(dispatch, before_effect=guard, **trusted_options))
        watchdog = asyncio.create_task(heartbeat())
        result = None
        settled = False
        try:
            done, _ = await asyncio.wait({runner, watchdog}, return_when=asyncio.FIRST_COMPLETED)
            if watchdog in done:
                await watchdog  # Revoked ownership interrupts execution and triggers sandbox finally cleanup.
            result = await runner
            await guard()
            await self.scheduler.handle_task_completion(dispatch.mission_id, dispatch.org_id, result)
            settled = True
            await self.dispatcher.acknowledge_dispatch(message_id)
            return True
        except StaleLeaseError:
            return False
        finally:
            for job in (runner, watchdog):
                job.cancel()
                with suppress(asyncio.CancelledError, StaleLeaseError):
                    completed = await job
                    if job is runner and isinstance(completed, TaskExecutionResult):
                        result = completed
            if result is not None and not settled:
                await self.scheduler.record_aborted_completion(dispatch.mission_id, dispatch.org_id, result)
                await self.dispatcher.acknowledge_dispatch(message_id)

    async def run_once(self, block_ms: int = 1000) -> int:
        messages = await self.dispatcher.read_dispatches(self.worker_id, count=1, block_ms=block_ms)
        return sum([int(await self.process(mid, payload)) for mid, payload in messages])

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            # Pending messages are safe to redeliver: PostgreSQL start CAS prevents duplicate effects.
            reclaimed = await self.dispatcher.reclaim_abandoned_messages(self.worker_id)
            for mid, payload in reclaimed:
                await self.process(mid, payload)
            await self.run_once()
