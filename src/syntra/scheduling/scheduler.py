"""Deterministic TaskScheduler Service for SYNTRA.

Governs task eligibility, multi-factor priority ranking, concurrency capacity limits,
atomic budget reservations, and transactional dispatch staging.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select

from syntra.domain.entities import AgentRole, ArtifactType, AttemptState, MissionState, TaskPlanStatus, TaskState
from syntra.domain.exceptions import CrossTenantAccessError
from syntra.persistence.models import MissionModel, TaskAttemptModel, TaskModel, TaskPlanModel, WorkerLeaseModel
from syntra.scheduling.dag_engine import TaskDAGEngine
from syntra.scheduling.exceptions import (
    StaleLeaseError,
)
from syntra.scheduling.models import (
    EngineeringTaskSpecification,
    TaskDispatchPayload,
    TaskExecutionResult,
)

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Core deterministic scheduling and dispatch service."""

    DEFAULT_ESTIMATED_TOKENS = 8192
    DEFAULT_ESTIMATED_COST = Decimal("0.0500")
    DEFAULT_LEASE_DURATION_SECONDS = 60

    DEFAULT_ROLE_CONCURRENCY_LIMITS: dict[str, int] = {
        AgentRole.PRODUCT_MANAGER.value: 1,
        AgentRole.SOFTWARE_ARCHITECT.value: 1,
        AgentRole.ENGINEERING_MANAGER.value: 1,
        AgentRole.BACKEND_ENGINEER.value: 2,
        AgentRole.FRONTEND_ENGINEER.value: 2,
        AgentRole.QA_ENGINEER.value: 2,
        AgentRole.DEVOPS_ENGINEER.value: 1,
        AgentRole.SECURITY_REVIEWER.value: 1,
        AgentRole.CODE_REVIEWER.value: 1,
        AgentRole.DEBUGGING_SPECIALIST.value: 1,
    }

    def __init__(
        self,
        uow_factory: Any,
        dag_engine: TaskDAGEngine | None = None,
        role_concurrency_limits: dict[str, int] | None = None,
        default_role_limit: int = 2,
    ) -> None:
        self.uow_factory = uow_factory
        self.dag_engine = dag_engine or TaskDAGEngine()
        self.role_concurrency_limits = {
            **self.DEFAULT_ROLE_CONCURRENCY_LIMITS,
            **(role_concurrency_limits or {}),
        }
        self.default_role_limit = default_role_limit

    def reservation_for(self, task: TaskModel) -> tuple[int, Decimal]:
        if task.description and task.description.startswith("{"):
            data = json.loads(task.description)
            if data.get("phase10_task"):
                spec = EngineeringTaskSpecification.model_validate(data)
                return spec.estimated_tokens, spec.estimated_cost_usd
        return self.DEFAULT_ESTIMATED_TOKENS, self.DEFAULT_ESTIMATED_COST

    async def schedule_ready_tasks(
        self,
        mission_id: UUID,
        org_id: UUID,
        worker_id: str = "scheduler-dispatcher",
        max_dispatch: int | None = None,
    ) -> list[TaskDispatchPayload]:
        """Evaluate task eligibility, rank by deterministic priority, reserve budgets, and stage dispatches."""
        dispatches: list[TaskDispatchPayload] = []

        async with self.uow_factory() as uow:
            # 1. Authoritative mission inspection with capacity serialization lock
            # We lock the MissionModel row with FOR UPDATE to serialize capacity allocation across concurrent schedulers
            stmt_m = (
                select(MissionModel)
                .where(MissionModel.id == mission_id, MissionModel.org_id == org_id)
                .with_for_update()
            )
            res_m = await uow.session.execute(stmt_m)
            mission = res_m.scalar_one_or_none()
            if not mission:
                raise CrossTenantAccessError(f"Mission {mission_id} not found.")

            if mission.state not in {MissionState.RUNNING, MissionState.READY}:
                logger.warning("Mission %s is in state %s. Scheduling rejected.", mission_id, mission.state.value)
                return []

            plan = await uow.tasks.get_plan_for_mission(mission_id=mission_id, org_id=org_id)
            if not plan:
                logger.warning("No task plan found for mission %s", mission_id)
                return []

            # 2. Inspect budget, active capacity, and per-role concurrency
            budget = await uow.budgets.get_for_mission(mission_id=mission_id)
            max_concurrency = budget.max_concurrency if budget else 4

            all_tasks, _, _ = await uow.tasks.list_for_mission(mission_id=mission_id, org_id=org_id, limit=500)
            task_map = {t.id: t for t in all_tasks}

            # Count currently active running tasks (ASSIGNED or IN_PROGRESS or REVIEW or VERIFYING)
            active_states = {TaskState.ASSIGNED, TaskState.IN_PROGRESS, TaskState.REVIEW, TaskState.VERIFYING}
            active_running_count = sum(1 for t in all_tasks if t.state in active_states)

            active_role_counts: dict[str, int] = defaultdict(int)
            for t in all_tasks:
                if t.state in active_states:
                    active_role_counts[t.assigned_role] += 1

            available_slots = max(0, max_concurrency - active_running_count)
            if max_dispatch is not None:
                available_slots = min(available_slots, max_dispatch)

            if available_slots <= 0:
                logger.info(
                    "Mission %s at concurrency limit (%d active / %d max).",
                    mission_id,
                    active_running_count,
                    max_concurrency,
                )
                return []

            # 3. Evaluate PENDING tasks for readiness
            pending_tasks = [t for t in all_tasks if t.state == TaskState.PENDING]
            for t in pending_tasks:
                dep_ids = await uow.tasks.get_dependencies_for_task(t.id)
                upstream = [task_map[d_id] for d_id in dep_ids if d_id in task_map]
                readiness = self.dag_engine.evaluate_task_readiness(
                    task=t,
                    mission=mission,
                    plan=plan,
                    upstream_dependencies=upstream,
                    budget=budget,
                )
                if readiness.is_ready:
                    t.state = TaskState.READY
                    t.updated_at = datetime.now(UTC)

            # 4. Deterministic priority ranking among all READY tasks
            ready_tasks = [t for t in all_tasks if t.state == TaskState.READY]
            if not ready_tasks:
                await uow.commit()
                return []

            # Extract dependencies for graph ranking
            raw_deps = []
            for t in all_tasks:
                d_ids = await uow.tasks.get_dependencies_for_task(t.id)
                for d_id in d_ids:
                    raw_deps.append({"task_id": t.id, "depends_on_task_id": d_id})

            scores = self.dag_engine.compute_priority_scores(ready_tasks, raw_deps)

            # 5. Filter selected tasks by mission slots AND per-role concurrency limits
            selected_task_ids: list[UUID] = []
            for s in scores:
                if available_slots <= 0:
                    break
                t = task_map[s.task_id]
                role_limit = self.role_concurrency_limits.get(t.assigned_role, self.default_role_limit)
                if active_role_counts[t.assigned_role] >= role_limit:
                    continue
                selected_task_ids.append(t.id)
                available_slots -= 1
                active_role_counts[t.assigned_role] += 1

            if not selected_task_ids:
                await uow.commit()
                return []

            # 6. Dispatch selected tasks: row locking, budget reservation, attempt creation, lease assignment, outbox staging
            now = datetime.now(UTC)

            for t_id in selected_task_ids:
                # Lock specific task row to guarantee atomic claim
                stmt_t = select(TaskModel).where(TaskModel.id == t_id).with_for_update()
                res_t = await uow.session.execute(stmt_t)
                task = res_t.scalar_one_or_none()
                if not task or task.state != TaskState.READY:
                    continue
                reserved_tokens, reserved_cost = self.reservation_for(task)

                # Atomic budget reservation
                if budget:
                    await uow.budgets.reserve(
                        mission_id=mission_id,
                        tokens=reserved_tokens,
                        cost_usd=reserved_cost,
                    )

                task.state = TaskState.ASSIGNED
                task.attempt_count += 1
                task.updated_at = now

                # Create attempt record atomically
                attempt = await uow.tasks.create_attempt(
                    task_id=task.id,
                    attempt_number=task.attempt_count,
                    state=AttemptState.INITIALIZING,
                )

                # Acquire / renew worker lease with monotonically increasing fencing token
                lease = await uow.tasks.claim_lease(
                    task_id=task.id,
                    worker_id=worker_id,
                    fencing_token=task.attempt_count,
                    duration_seconds=self.DEFAULT_LEASE_DURATION_SECONDS,
                )

                # Build dispatch payload
                dispatch = TaskDispatchPayload(
                    task_id=task.id,
                    mission_id=mission_id,
                    org_id=org_id,
                    attempt_number=task.attempt_count,
                    assigned_role=task.assigned_role,
                    fencing_token=lease.fencing_token,
                    lease_expires_at=lease.lease_expires_at,
                    specification=task.description or task.title,
                    plan_version=plan.plan_version,
                    task_attempt_id=attempt.id,
                    budget_reserved_tokens=reserved_tokens,
                    budget_reserved_cost_usd=reserved_cost,
                )

                # Stage in transactional outbox
                uow.publish_event(
                    event_type="TASK_DISPATCHED",
                    payload=dispatch.model_dump(mode="json"),
                )
                dispatches.append(dispatch)

            await uow.commit()

        return dispatches

    async def _validate_dispatch(self, uow: Any, dispatch: TaskDispatchPayload, worker_id: str) -> Any:
        mission = (
            await uow.session.execute(
                select(MissionModel)
                .where(
                    MissionModel.id == dispatch.mission_id,
                    MissionModel.org_id == dispatch.org_id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if not mission or mission.state not in {MissionState.READY, MissionState.RUNNING}:
            raise StaleLeaseError("Mission is not authorized for execution")
        task = (
            await uow.session.execute(
                select(TaskModel)
                .where(
                    TaskModel.id == dispatch.task_id,
                    TaskModel.org_id == dispatch.org_id,
                    TaskModel.mission_id == dispatch.mission_id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if not task or task.state not in {TaskState.ASSIGNED, TaskState.IN_PROGRESS}:
            raise StaleLeaseError("Task is not assigned to an active worker")
        plan = await uow.session.get(TaskPlanModel, task.task_plan_id)
        attempt = await uow.tasks.get_latest_attempt(task.id)
        lease = (
            await uow.session.execute(
                select(WorkerLeaseModel)
                .where(
                    WorkerLeaseModel.task_id == task.id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if (
            not plan
            or plan.plan_version != mission.active_plan_version
            or plan.plan_version != dispatch.plan_version
            or plan.status not in {TaskPlanStatus.APPROVED, TaskPlanStatus.ACTIVE}
            or task.assigned_role != dispatch.assigned_role
            or (task.description or task.title) != dispatch.specification
            or not attempt
            or attempt.attempt_number != dispatch.attempt_number
            or (dispatch.task_attempt_id and attempt.id != dispatch.task_attempt_id)
            or task.attempt_count != dispatch.attempt_number
            or not lease
            or lease.fencing_token != dispatch.fencing_token
            or lease.worker_id not in {worker_id, "scheduler-dispatcher", "unassigned"}
        ):
            raise StaleLeaseError("Dispatch does not match authoritative task, plan, attempt or lease")
        reserved_tokens, reserved_cost = self.reservation_for(task)
        if dispatch.budget_reserved_tokens != reserved_tokens or dispatch.budget_reserved_cost_usd != reserved_cost:
            raise StaleLeaseError("Dispatch budget does not match authoritative reservation")
        expires = (
            lease.lease_expires_at.replace(tzinfo=UTC) if not lease.lease_expires_at.tzinfo else lease.lease_expires_at
        )
        if expires <= datetime.now(UTC):
            raise StaleLeaseError("Worker lease has expired")
        return task, attempt, lease

    async def begin_dispatch(self, dispatch: TaskDispatchPayload, worker_id: str) -> bool:
        """Atomically consume INITIALIZING once; duplicate Redis messages cannot execute."""
        try:
            async with self.uow_factory() as uow:
                task, attempt, lease = await self._validate_dispatch(uow, dispatch, worker_id)
                if attempt.state != AttemptState.INITIALIZING or task.state != TaskState.ASSIGNED:
                    return False
                lease.worker_id = worker_id
                await uow.idempotency.record(
                    f"phase10:started:{attempt.id}",
                    dispatch.org_id,
                    200,
                    {"worker_id": worker_id, "fencing_token": dispatch.fencing_token},
                )
                attempt.state = AttemptState.RUNNING
                task.state = TaskState.IN_PROGRESS
                uow.publish_event(
                    "WORKER_STARTED",
                    {
                        "task_id": str(task.id),
                        "attempt_id": str(attempt.id),
                        "org_id": str(dispatch.org_id),
                        "mission_id": str(dispatch.mission_id),
                        "worker_id": worker_id,
                    },
                )
                await uow.commit()
                return True
        except StaleLeaseError:
            return False

    async def assert_dispatch_active(self, dispatch: TaskDispatchPayload, worker_id: str, renew: bool = False) -> None:
        """Fail closed before tool effects and during heartbeat; never resurrect expired ownership."""
        async with self.uow_factory() as uow:
            _, attempt, lease = await self._validate_dispatch(uow, dispatch, worker_id)
            if attempt.state != AttemptState.RUNNING or lease.worker_id != worker_id:
                raise StaleLeaseError("Worker does not own a running attempt")
            if renew:
                lease.lease_expires_at = datetime.now(UTC) + timedelta(seconds=self.DEFAULT_LEASE_DURATION_SECONDS)
                await uow.commit()

    async def _settle_usage(
        self, uow: Any, task: TaskModel, attempt: TaskAttemptModel, result: TaskExecutionResult
    ) -> None:
        key = f"phase10:usage:{attempt.id}"
        if await uow.idempotency.get(key, task.org_id):
            return
        reserved_tokens, reserved_cost = self.reservation_for(task)
        await uow.budgets.commit_usage(
            task.mission_id,
            result.actual_prompt_tokens + result.actual_completion_tokens,
            result.actual_cost_usd,
            reserved_tokens=reserved_tokens,
            reserved_cost_usd=reserved_cost,
        )
        await uow.budgets.add_usage_record(
            task.org_id,
            task.mission_id,
            "agent-task-aggregate",
            result.actual_prompt_tokens,
            result.actual_completion_tokens,
            result.actual_cost_usd,
            task.id,
        )
        await uow.idempotency.record(
            key,
            task.org_id,
            200,
            {
                "tokens": result.actual_prompt_tokens + result.actual_completion_tokens,
                "cost_usd": str(result.actual_cost_usd),
                "classification": result.cost_classification,
            },
        )

    async def record_aborted_completion(self, mission_id: UUID, org_id: UUID, result: TaskExecutionResult) -> None:
        """Account previously authorized work after revocation without accepting its task outcome."""
        async with self.uow_factory() as uow:
            mission = await uow.missions.get_by_id_for_org(mission_id, org_id)
            await uow.session.refresh(mission, with_for_update=True)
            task = await uow.tasks.get_by_id_for_org(result.task_id, org_id)
            if task.mission_id != mission_id:
                raise StaleLeaseError("Cannot settle cross-mission usage")
            attempt = (
                await uow.session.execute(
                    select(TaskAttemptModel).where(
                        TaskAttemptModel.task_id == task.id,
                        TaskAttemptModel.attempt_number == result.attempt_number,
                    )
                )
            ).scalar_one_or_none()
            if not attempt:
                raise StaleLeaseError("Cannot settle an unknown attempt")
            proof = await uow.idempotency.get(f"phase10:started:{attempt.id}", org_id)
            if not proof or proof.response_body != {
                "worker_id": result.worker_id,
                "fencing_token": result.fencing_token,
            }:
                raise StaleLeaseError("Usage does not match the recorded worker start")
            await self._settle_usage(uow, task, attempt, result)
            await uow.commit()

    async def handle_task_completion(
        self,
        mission_id: UUID,
        org_id: UUID,
        result: TaskExecutionResult,
    ) -> TaskModel:
        """Process authoritative result submitted by a worker with strict fencing token validation."""
        async with self.uow_factory() as uow:
            mission = (
                await uow.session.execute(
                    select(MissionModel)
                    .where(
                        MissionModel.id == mission_id,
                        MissionModel.org_id == org_id,
                    )
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if not mission or mission.state not in {MissionState.READY, MissionState.RUNNING}:
                raise StaleLeaseError("Mission no longer permits task results")
            task = await uow.tasks.get_by_id_for_org(task_id=result.task_id, org_id=org_id)
            # Serialize duplicate completions and require exact mission/attempt ownership.
            await uow.session.refresh(task, with_for_update=True)
            plan = await uow.session.get(TaskPlanModel, task.task_plan_id)
            latest_attempt = await uow.tasks.get_latest_attempt(task.id)
            if (
                task.mission_id != mission_id
                or not plan
                or plan.plan_version != mission.active_plan_version
                or task.state not in {TaskState.ASSIGNED, TaskState.IN_PROGRESS}
                or not latest_attempt
                or latest_attempt.attempt_number != result.attempt_number
            ):
                raise StaleLeaseError("Result rejected: stale fencing token, attempt or cross-mission task result")

            # 1. Fencing token validation (Rejects superseded workers)
            is_valid_lease = await uow.tasks.validate_worker_lease(
                task_id=task.id,
                worker_id=result.worker_id,
                fencing_token=result.fencing_token,
            )
            if not is_valid_lease:
                raise StaleLeaseError(
                    f"Result rejected: Worker '{result.worker_id}' submitted with stale fencing token {result.fencing_token} for task {task.id}."
                )

            from syntra.persistence.artifact_store import store_artifact

            reserved_tokens, reserved_cost = self.reservation_for(task)
            if (
                task.description
                and task.description.startswith("{")
                and json.loads(task.description).get("phase10_task")
                and result.status == AttemptState.SUCCEEDED
            ):
                from syntra.agents.handoffs import validate_task_reviews

                await validate_task_reviews(uow, task, latest_attempt, result.unified_diff or "")
            await self._settle_usage(uow, task, latest_attempt, result)
            if result.unified_diff:
                await store_artifact(
                    uow,
                    mission_id=mission_id,
                    org_id=org_id,
                    task_id=task.id,
                    title=f"Patch attempt {result.attempt_number}",
                    content=result.unified_diff,
                    type=ArtifactType.UNIFIED_DIFF,
                )
            await store_artifact(
                uow,
                mission_id=mission_id,
                org_id=org_id,
                task_id=task.id,
                title=f"Execution attempt {result.attempt_number}",
                content=json.dumps(result.model_dump(mode="json"), sort_keys=True),
                type=ArtifactType.TEST_REPORT,
            )

            # 2. Update latest attempt
            latest_attempt = await uow.tasks.get_latest_attempt(task_id=task.id)
            if latest_attempt:
                await uow.tasks.update_attempt_state(
                    attempt_id=latest_attempt.id,
                    state=result.status,
                    exit_code=result.exit_code,
                    error_message=result.error_message,
                )

            # 3. Handle outcome branches
            if result.status == AttemptState.SUCCEEDED:
                task.state = TaskState.COMPLETED
                task.updated_at = datetime.now(UTC)

                # Reconcile budget: commit actuals and release unneeded reservation

                # Release lease
                await uow.tasks.release_lease(task_id=task.id, worker_id=result.worker_id)

                # Stage completion event
                uow.publish_event(
                    event_type="TASK_COMPLETED",
                    payload={"task_id": str(task.id), "mission_id": str(mission_id), "status": "COMPLETED"},
                )

            else:
                # Failed attempts also consumed model resources.
                # Failure branch: check remaining retry attempts
                if task.attempt_count < task.max_attempts:
                    task.state = TaskState.READY  # Re-queue
                    task.updated_at = datetime.now(UTC)
                    await uow.tasks.release_lease(task_id=task.id, worker_id=result.worker_id)
                    # Release unused reservation so it can be re-reserved on next attempt
                else:
                    task.state = TaskState.FAILED
                    task.updated_at = datetime.now(UTC)
                    await uow.tasks.release_lease(task_id=task.id, worker_id=result.worker_id)

                    # Propagate failure: mark downstream dependents as BLOCKED
                    all_tasks, _, _ = await uow.tasks.list_for_mission(mission_id=mission_id, org_id=org_id, limit=500)
                    for other in all_tasks:
                        deps = await uow.tasks.get_dependencies_for_task(other.id)
                        if task.id in deps and other.state in {TaskState.PENDING, TaskState.READY}:
                            other.state = TaskState.BLOCKED
                            other.updated_at = datetime.now(UTC)

                    uow.publish_event(
                        event_type="TASK_FAILED",
                        payload={
                            "task_id": str(task.id),
                            "mission_id": str(mission_id),
                            "reason": result.error_message,
                        },
                    )

            await uow.commit()
            return task
