"""Background Reconciliation Worker for Fault Recovery and Lease Reclaiming.

Detects expired leases, abandoned worker attempts, stalled dispatches, and
propagates failure cascades to protect graph integrity.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from syntra.domain.entities import AttemptState, MissionState, TaskState
from syntra.scheduling.models import ReconciliationSummary

logger = logging.getLogger(__name__)


class SchedulerReconciler:
    """Detects and resolves anomalies in distributed task execution."""

    def __init__(self, uow_factory: Any) -> None:
        self.uow_factory = uow_factory

    async def reconcile_mission(self, mission_id: UUID, org_id: UUID) -> ReconciliationSummary:
        """Run an authoritative reconciliation sweep for an individual mission."""
        expired_count = 0
        recovered_count = 0
        failed_count = 0
        blocked_count = 0
        details: list[str] = []

        now = datetime.now(UTC)

        async with self.uow_factory() as uow:
            mission = await uow.missions.get_by_id_for_org(mission_id=mission_id, org_id=org_id)
            all_tasks, _, _ = await uow.tasks.list_for_mission(mission_id=mission_id, org_id=org_id, limit=500)
            task_map = {t.id: t for t in all_tasks}

            # 1. Mission cancellation check: if cancelled, transition non-terminal tasks to CANCELLED
            if mission.state == MissionState.CANCELLED:
                for t in all_tasks:
                    if t.state not in {TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED}:
                        t.state = TaskState.CANCELLED
                        t.updated_at = now
                        await uow.tasks.release_lease(task_id=t.id, worker_id="system")
                        details.append(f"Cancelled task {t.identifier} due to mission cancellation.")
                await uow.commit()
                return ReconciliationSummary(
                    swept_at=now,
                    details=details,
                )

            # 2. Inspect expired leases
            expired_leases = await uow.tasks.get_expired_leases(cutoff=now)
            mission_expired = [lease_obj for lease_obj in expired_leases if lease_obj.task_id in task_map]

            for lease in mission_expired:
                expired_count += 1
                task = task_map[lease.task_id]

                # Update latest attempt to TIMED_OUT
                latest_attempt = await uow.tasks.get_latest_attempt(task_id=task.id)
                if latest_attempt and latest_attempt.state in {AttemptState.INITIALIZING, AttemptState.RUNNING}:
                    await uow.tasks.update_attempt_state(
                        attempt_id=latest_attempt.id,
                        state=AttemptState.TIMED_OUT,
                        error_message="Worker lease expired without result submission.",
                    )

                if task.attempt_count < task.max_attempts:
                    # Recoverable: reset task to READY for re-scheduling
                    task.state = TaskState.READY
                    task.updated_at = now
                    recovered_count += 1
                    details.append(
                        f"Recovered task {task.identifier} (attempt {task.attempt_count}/{task.max_attempts})."
                    )
                else:
                    # Max attempts exhausted: mark FAILED and cascade BLOCKED to dependents
                    task.state = TaskState.FAILED
                    task.updated_at = now
                    failed_count += 1
                    details.append(f"Failed task {task.identifier}: max attempts exhausted after lease expiry.")

                    for other in all_tasks:
                        deps = await uow.tasks.get_dependencies_for_task(other.id)
                        if task.id in deps and other.state in {TaskState.PENDING, TaskState.READY}:
                            other.state = TaskState.BLOCKED
                            other.updated_at = now
                            blocked_count += 1
                            details.append(f"Cascaded BLOCKED to task {other.identifier}.")

                # Release the expired lease
                await uow.tasks.release_lease(task_id=task.id, worker_id=lease.worker_id)

            await uow.commit()

        return ReconciliationSummary(
            swept_at=now,
            expired_leases_count=expired_count,
            recovered_attempts_count=recovered_count,
            abandoned_tasks_failed=failed_count,
            blocked_dependents_count=blocked_count,
            details=details,
        )
