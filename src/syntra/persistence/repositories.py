"""Domain and persistence repositories with strict multi-tenant isolation and optimistic concurrency."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from syntra.domain.entities import (
    ApprovalDecision,
    ArtifactType,
    AttemptState,
    MCPTransportType,
    MissionState,
    OutboxStatus,
    TaskPlanStatus,
    TaskState,
    VerificationVerdict,
    compute_action_digest,
    verify_action_digest,
)
from syntra.domain.exceptions import (
    ApprovalExpiredError,
    ApprovalReplayError,
    ApprovalTamperedError,
    ArtifactOwnershipError,
    BudgetExceededError,
    CrossTenantAccessError,
    DigestMismatchError,
    DuplicateIdempotencyKeyError,
    OptimisticLockError,
)
from syntra.persistence.models import (
    ArtifactModel,
    ArtifactVersionModel,
    BudgetModel,
    EventRecordModel,
    HumanApprovalModel,
    IdempotencyKeyModel,
    MCPInvocationModel,
    MCPServerModel,
    MCPToolVersionModel,
    MissionModel,
    OrganizationModel,
    ProjectModel,
    TaskAttemptModel,
    TaskDependencyModel,
    TaskModel,
    TaskPlanModel,
    TransactionalOutboxModel,
    UsageRecordModel,
    VerificationRunModel,
    WorkerLeaseModel,
)


class OrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, org_id: UUID, name: str, slug: str) -> OrganizationModel:
        org = OrganizationModel(id=org_id, name=name, slug=slug)
        self.session.add(org)
        await self.session.flush()
        return org

    async def get_by_id(self, org_id: UUID) -> OrganizationModel | None:
        stmt = select(OrganizationModel).where(OrganizationModel.id == org_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        project_id: UUID,
        org_id: UUID,
        name: str,
        slug: str,
        description: str | None = None,
    ) -> ProjectModel:
        project = ProjectModel(
            id=project_id,
            org_id=org_id,
            name=name,
            slug=slug,
            description=description,
        )
        self.session.add(project)
        await self.session.flush()
        return project

    async def get_by_id_for_org(self, project_id: UUID, org_id: UUID) -> ProjectModel:
        stmt = select(ProjectModel).where(ProjectModel.id == project_id)
        res = await self.session.execute(stmt)
        project = res.scalar_one_or_none()
        if not project:
            raise CrossTenantAccessError(f"Project {project_id} not found.")
        if project.org_id != org_id:
            raise CrossTenantAccessError(
                f"Unauthorized cross-tenant access: project {project_id} does not belong to org {org_id}."
            )
        return project

    async def list_for_org(self, org_id: UUID, limit: int = 50) -> list[ProjectModel]:
        stmt = (
            select(ProjectModel)
            .where(ProjectModel.org_id == org_id)
            .order_by(ProjectModel.created_at.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class MissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        mission_id: UUID,
        org_id: UUID,
        project_id: UUID,
        objective: str,
        repository_id: UUID | None = None,
        autonomy_mode: str = "semi_autonomous",
    ) -> MissionModel:
        mission = MissionModel(
            id=mission_id,
            org_id=org_id,
            project_id=project_id,
            repository_id=repository_id,
            objective=objective,
            autonomy_mode=autonomy_mode,
            state=MissionState.DRAFT,
            version=1,
        )
        self.session.add(mission)
        await self.session.flush()
        return mission

    async def get_by_id_for_org(self, mission_id: UUID, org_id: UUID) -> MissionModel:
        stmt = select(MissionModel).where(MissionModel.id == mission_id)
        res = await self.session.execute(stmt)
        mission = res.scalar_one_or_none()
        if not mission:
            raise CrossTenantAccessError(f"Mission {mission_id} not found.")
        if mission.org_id != org_id:
            raise CrossTenantAccessError(
                f"Unauthorized cross-tenant access: mission {mission_id} does not belong to org {org_id}."
            )
        return mission

    async def update_objective(
        self,
        mission_id: UUID,
        org_id: UUID,
        expected_version: int,
        new_objective: str,
    ) -> MissionModel:
        # Optimistic concurrency update
        stmt = (
            update(MissionModel)
            .where(
                MissionModel.id == mission_id,
                MissionModel.org_id == org_id,
                MissionModel.version == expected_version,
            )
            .values(
                objective=new_objective,
                version=expected_version + 1,
                updated_at=datetime.now(UTC),
            )
        )
        result = await self.session.execute(stmt)
        rowcount = getattr(result, "rowcount", -1)
        if rowcount == 0:
            # Check if mission exists with different version
            stmt_check = select(MissionModel).where(MissionModel.id == mission_id, MissionModel.org_id == org_id)
            res_check = await self.session.execute(stmt_check)
            existing = res_check.scalar_one_or_none()
            if existing and existing.version != expected_version:
                raise OptimisticLockError(
                    f"Optimistic lock failure on mission {mission_id}: expected version {expected_version}, found {existing.version}."
                )
            raise CrossTenantAccessError(f"Mission {mission_id} not found for org {org_id}.")

        return await self.get_by_id_for_org(mission_id=mission_id, org_id=org_id)


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_plan(
        self,
        plan_id: UUID,
        mission_id: UUID,
        version: int = 1,
        status: TaskPlanStatus = TaskPlanStatus.DRAFT,
    ) -> TaskPlanModel:
        plan = TaskPlanModel(
            id=plan_id,
            mission_id=mission_id,
            plan_version=version,
            status=status,
        )
        self.session.add(plan)
        await self.session.flush()
        return plan

    async def create_task(
        self,
        task_id: UUID,
        task_plan_id: UUID,
        mission_id: UUID,
        org_id: UUID,
        identifier: str,
        title: str,
        description: str,
        assigned_role: str,
        priority: int = 0,
        max_attempts: int = 3,
    ) -> TaskModel:
        task = TaskModel(
            id=task_id,
            task_plan_id=task_plan_id,
            mission_id=mission_id,
            org_id=org_id,
            identifier=identifier,
            title=title,
            description=description,
            assigned_role=assigned_role,
            state=TaskState.PENDING,
            priority=priority,
            max_attempts=max_attempts,
            version=1,
        )
        self.session.add(task)
        await self.session.flush()
        return task

    async def add_dependency(self, task_id: UUID, depends_on_task_id: UUID) -> TaskDependencyModel:
        dep = TaskDependencyModel(task_id=task_id, depends_on_task_id=depends_on_task_id)
        self.session.add(dep)
        await self.session.flush()
        return dep

    async def get_by_id(self, task_id: UUID) -> TaskModel | None:
        stmt = select(TaskModel).where(TaskModel.id == task_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_id_for_org(self, task_id: UUID, org_id: UUID) -> TaskModel:
        stmt = select(TaskModel).where(TaskModel.id == task_id)
        res = await self.session.execute(stmt)
        task = res.scalar_one_or_none()
        if not task:
            raise CrossTenantAccessError(f"Task {task_id} not found.")
        if task.org_id != org_id:
            raise CrossTenantAccessError(
                f"Unauthorized cross-tenant access: task {task_id} does not belong to org {org_id}."
            )
        return task

    async def list_for_mission(
        self,
        mission_id: UUID,
        org_id: UUID,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[TaskModel], str | None, bool]:
        stmt_m = select(MissionModel).where(MissionModel.id == mission_id)
        res_m = await self.session.execute(stmt_m)
        mission = res_m.scalar_one_or_none()
        if not mission:
            raise CrossTenantAccessError(f"Mission {mission_id} not found.")
        if mission.org_id != org_id:
            raise CrossTenantAccessError(
                f"Unauthorized cross-tenant access: mission {mission_id} does not belong to org {org_id}."
            )

        query = select(TaskModel).where(
            TaskModel.mission_id == mission_id,
            TaskModel.org_id == org_id,
        )
        if cursor:
            try:
                cursor_dt = datetime.fromisoformat(cursor)
                query = query.where(TaskModel.created_at > cursor_dt)
            except ValueError:
                pass

        query = query.order_by(TaskModel.created_at.asc()).limit(limit + 1)
        res = await self.session.execute(query)
        items = list(res.scalars().all())
        has_more = len(items) > limit
        if has_more:
            items = items[:limit]
            next_cursor = items[-1].created_at.isoformat() if items else None
        else:
            next_cursor = None
        return items, next_cursor, has_more

    async def get_dependencies_for_task(self, task_id: UUID) -> list[UUID]:
        stmt = select(TaskDependencyModel.depends_on_task_id).where(TaskDependencyModel.task_id == task_id)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_plan_for_mission(self, mission_id: UUID, org_id: UUID) -> TaskPlanModel | None:
        stmt_m = select(MissionModel).where(MissionModel.id == mission_id)
        res_m = await self.session.execute(stmt_m)
        mission = res_m.scalar_one_or_none()
        if not mission:
            raise CrossTenantAccessError(f"Mission {mission_id} not found.")
        if mission.org_id != org_id:
            raise CrossTenantAccessError(
                f"Unauthorized cross-tenant access: mission {mission_id} does not belong to org {org_id}."
            )

        stmt = (
            select(TaskPlanModel)
            .where(TaskPlanModel.mission_id == mission_id)
            .order_by(TaskPlanModel.plan_version.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_plan_by_version(self, mission_id: UUID, plan_version: int) -> TaskPlanModel | None:
        stmt = (
            select(TaskPlanModel)
            .where(
                TaskPlanModel.mission_id == mission_id,
                TaskPlanModel.plan_version == plan_version,
            )
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def claim_lease(
        self,
        task_id: UUID,
        worker_id: str,
        fencing_token: int,
        duration_seconds: int = 60,
    ) -> WorkerLeaseModel:
        expires_at = datetime.now(UTC) + timedelta(seconds=duration_seconds)
        stmt = select(WorkerLeaseModel).where(WorkerLeaseModel.task_id == task_id).with_for_update()
        res = await self.session.execute(stmt)
        lease = res.scalar_one_or_none()

        if lease:
            lease.worker_id = worker_id
            lease.fencing_token = fencing_token
            lease.lease_expires_at = expires_at
        else:
            lease = WorkerLeaseModel(
                task_id=task_id,
                worker_id=worker_id,
                fencing_token=fencing_token,
                lease_expires_at=expires_at,
            )
            self.session.add(lease)

        await self.session.flush()
        return lease

    async def update_status(
        self,
        task_id: UUID,
        new_state: TaskState,
        reason: str | None = None,
    ) -> TaskModel:
        stmt = select(TaskModel).where(TaskModel.id == task_id).with_for_update()
        res = await self.session.execute(stmt)
        task = res.scalar_one_or_none()
        if not task:
            raise ValueError(f"Task {task_id} not found.")
        task.state = new_state
        task.updated_at = datetime.now(UTC)
        await self.session.flush()
        return task

    async def create_attempt(
        self,
        task_id: UUID,
        attempt_number: int,
        state: AttemptState = AttemptState.INITIALIZING,
    ) -> TaskAttemptModel:
        attempt = TaskAttemptModel(
            id=uuid4(),
            task_id=task_id,
            attempt_number=attempt_number,
            state=state,
            started_at=datetime.now(UTC),
        )
        self.session.add(attempt)
        await self.session.flush()
        return attempt

    async def get_latest_attempt(self, task_id: UUID) -> TaskAttemptModel | None:
        stmt = (
            select(TaskAttemptModel)
            .where(TaskAttemptModel.task_id == task_id)
            .order_by(TaskAttemptModel.attempt_number.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def update_attempt_state(
        self,
        attempt_id: UUID,
        state: AttemptState,
        exit_code: int | None = None,
        error_message: str | None = None,
    ) -> TaskAttemptModel:
        stmt = select(TaskAttemptModel).where(TaskAttemptModel.id == attempt_id).with_for_update()
        res = await self.session.execute(stmt)
        attempt = res.scalar_one_or_none()
        if not attempt:
            raise ValueError(f"TaskAttempt {attempt_id} not found.")
        attempt.state = state
        if exit_code is not None:
            attempt.exit_code = exit_code
        if error_message is not None:
            attempt.error_message = error_message
        if state in {AttemptState.SUCCEEDED, AttemptState.FAILED, AttemptState.TIMED_OUT}:
            attempt.completed_at = datetime.now(UTC)
        await self.session.flush()
        return attempt

    async def claim_ready_tasks_atomic(
        self,
        mission_id: UUID,
        limit: int,
        worker_id: str,
        lease_duration_seconds: int = 60,
    ) -> list[tuple[TaskModel, WorkerLeaseModel]]:
        bind = self.session.bind
        dialect_name = bind.dialect.name if bind else "postgresql"
        if dialect_name == "postgresql":
            stmt = (
                select(TaskModel)
                .where(
                    TaskModel.mission_id == mission_id,
                    TaskModel.state == TaskState.READY,
                )
                .order_by(TaskModel.priority.desc(), TaskModel.created_at.asc())
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        else:
            stmt = (
                select(TaskModel)
                .where(
                    TaskModel.mission_id == mission_id,
                    TaskModel.state == TaskState.READY,
                )
                .order_by(TaskModel.priority.desc(), TaskModel.created_at.asc())
                .limit(limit)
                .with_for_update()
            )

        res = await self.session.execute(stmt)
        claimed_tasks = list(res.scalars().all())
        results: list[tuple[TaskModel, WorkerLeaseModel]] = []

        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=lease_duration_seconds)

        for task in claimed_tasks:
            task.state = TaskState.ASSIGNED
            task.attempt_count += 1
            task.updated_at = now

            # Atomically create authoritative task attempt record
            attempt = TaskAttemptModel(
                id=uuid4(),
                task_id=task.id,
                attempt_number=task.attempt_count,
                state=AttemptState.INITIALIZING,
                started_at=now,
            )
            self.session.add(attempt)

            stmt_lease = select(WorkerLeaseModel).where(WorkerLeaseModel.task_id == task.id).with_for_update()
            res_lease = await self.session.execute(stmt_lease)
            lease = res_lease.scalar_one_or_none()

            new_token = task.attempt_count
            if lease:
                lease.worker_id = worker_id
                lease.fencing_token = new_token
                lease.lease_expires_at = expires_at
                lease.acquired_at = now
            else:
                lease = WorkerLeaseModel(
                    task_id=task.id,
                    worker_id=worker_id,
                    fencing_token=new_token,
                    lease_expires_at=expires_at,
                    acquired_at=now,
                )
                self.session.add(lease)

            results.append((task, lease))

        await self.session.flush()
        return results

    async def renew_lease(
        self,
        task_id: UUID,
        worker_id: str,
        fencing_token: int,
        extension_seconds: int = 60,
    ) -> WorkerLeaseModel:
        stmt = select(WorkerLeaseModel).where(WorkerLeaseModel.task_id == task_id).with_for_update()
        res = await self.session.execute(stmt)
        lease = res.scalar_one_or_none()
        if not lease:
            raise ValueError(f"No lease found for task {task_id}")
        if lease.worker_id != worker_id or lease.fencing_token != fencing_token:
            from syntra.scheduling.exceptions import StaleLeaseError

            raise StaleLeaseError(
                f"Lease for task {task_id} superseded: active worker={lease.worker_id}, token={lease.fencing_token}, provided token={fencing_token}"
            )
        lease.lease_expires_at = datetime.now(UTC) + timedelta(seconds=extension_seconds)
        await self.session.flush()
        return lease

    async def validate_worker_lease(
        self,
        task_id: UUID,
        worker_id: str,
        fencing_token: int,
    ) -> bool:
        stmt = select(WorkerLeaseModel).where(WorkerLeaseModel.task_id == task_id)
        res = await self.session.execute(stmt)
        lease = res.scalar_one_or_none()
        if not lease:
            return False
        now = datetime.now(UTC)
        expires = (
            lease.lease_expires_at if lease.lease_expires_at.tzinfo else lease.lease_expires_at.replace(tzinfo=UTC)
        )
        if now > expires:
            return False
        if lease.worker_id in (worker_id, "scheduler-dispatcher", "unassigned"):
            if lease.worker_id != worker_id:
                lease.worker_id = worker_id
            return bool(lease.fencing_token == fencing_token)
        return False

    async def release_lease(self, task_id: UUID, worker_id: str) -> bool:
        stmt = select(WorkerLeaseModel).where(WorkerLeaseModel.task_id == task_id).with_for_update()
        res = await self.session.execute(stmt)
        lease = res.scalar_one_or_none()
        if lease and lease.worker_id in (worker_id, "scheduler-dispatcher", "unassigned"):
            await self.session.delete(lease)
            await self.session.flush()
            return True
        return False

    async def get_expired_leases(self, cutoff: datetime | None = None) -> list[WorkerLeaseModel]:
        cutoff_dt = cutoff or datetime.now(UTC)
        stmt = select(WorkerLeaseModel).where(WorkerLeaseModel.lease_expires_at < cutoff_dt)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_tasks_by_states(
        self,
        mission_id: UUID,
        states: list[TaskState],
    ) -> list[TaskModel]:
        stmt = select(TaskModel).where(
            TaskModel.mission_id == mission_id,
            TaskModel.state.in_(states),
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class BudgetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        org_id: UUID,
        mission_id: UUID | None,
        max_tokens: int = 1_000_000,
        max_cost_usd: Decimal = Decimal("50.0000"),
        max_concurrency: int = 4,
        max_task_attempts: int = 3,
        max_mission_duration_seconds: int = 3600,
    ) -> BudgetModel:
        budget = BudgetModel(
            org_id=org_id,
            mission_id=mission_id,
            max_tokens=max_tokens,
            max_cost_usd=max_cost_usd,
            max_concurrency=max_concurrency,
            max_task_attempts=max_task_attempts,
            max_mission_duration_seconds=max_mission_duration_seconds,
            reserved_tokens=0,
            consumed_tokens=0,
            reserved_cost_usd=Decimal("0.0000"),
            consumed_cost_usd=Decimal("0.0000"),
            version=1,
        )
        self.session.add(budget)
        await self.session.flush()
        return budget

    async def get_for_mission(self, mission_id: UUID) -> BudgetModel | None:
        stmt = select(BudgetModel).where(BudgetModel.mission_id == mission_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def reserve(
        self,
        mission_id: UUID,
        tokens: int = 0,
        cost_usd: Decimal = Decimal("0.0000"),
    ) -> BudgetModel:
        stmt = select(BudgetModel).where(BudgetModel.mission_id == mission_id).with_for_update()
        res = await self.session.execute(stmt)
        budget = res.scalar_one_or_none()
        if not budget:
            raise ValueError(f"No budget found for mission {mission_id}")

        if budget.consumed_tokens + budget.reserved_tokens + tokens > budget.max_tokens:
            raise BudgetExceededError(
                f"Budget token limit exceeded: max {budget.max_tokens}, currently committed/reserved "
                f"{budget.consumed_tokens + budget.reserved_tokens}, requested additional {tokens}."
            )

        if budget.consumed_cost_usd + budget.reserved_cost_usd + cost_usd > budget.max_cost_usd:
            raise BudgetExceededError(
                f"Budget cost limit exceeded: max ${budget.max_cost_usd}, currently committed/reserved "
                f"${budget.consumed_cost_usd + budget.reserved_cost_usd}, requested additional ${cost_usd}."
            )

        budget.reserved_tokens += tokens
        budget.reserved_cost_usd += cost_usd
        budget.version += 1
        await self.session.flush()
        return budget

    async def commit_usage(
        self,
        mission_id: UUID,
        tokens: int = 0,
        cost_usd: Decimal = Decimal("0.0000"),
        reserved_tokens: int | None = None,
        reserved_cost_usd: Decimal | None = None,
    ) -> BudgetModel:
        stmt = select(BudgetModel).where(BudgetModel.mission_id == mission_id).with_for_update()
        res = await self.session.execute(stmt)
        budget = res.scalar_one_or_none()
        if not budget:
            raise ValueError(f"No budget found for mission {mission_id}")

        budget.reserved_tokens = max(
            0, budget.reserved_tokens - (tokens if reserved_tokens is None else reserved_tokens)
        )
        budget.consumed_tokens += tokens
        budget.reserved_cost_usd = max(
            Decimal("0.0000"), budget.reserved_cost_usd - (cost_usd if reserved_cost_usd is None else reserved_cost_usd)
        )
        budget.consumed_cost_usd += cost_usd
        budget.version += 1
        await self.session.flush()
        return budget

    async def release_reservation(
        self,
        mission_id: UUID,
        tokens: int = 0,
        cost_usd: Decimal = Decimal("0.0000"),
    ) -> BudgetModel:
        stmt = select(BudgetModel).where(BudgetModel.mission_id == mission_id).with_for_update()
        res = await self.session.execute(stmt)
        budget = res.scalar_one_or_none()
        if not budget:
            raise ValueError(f"No budget found for mission {mission_id}")

        budget.reserved_tokens = max(0, budget.reserved_tokens - tokens)
        budget.reserved_cost_usd = max(Decimal("0.0000"), budget.reserved_cost_usd - cost_usd)
        budget.version += 1
        await self.session.flush()
        return budget

    async def add_usage_record(
        self,
        org_id: UUID,
        mission_id: UUID,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: Decimal,
        task_id: UUID | None = None,
    ) -> UsageRecordModel:
        record = UsageRecordModel(
            org_id=org_id,
            mission_id=mission_id,
            task_id=task_id,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def list_usage_records(
        self,
        mission_id: UUID,
        org_id: UUID,
        limit: int = 100,
    ) -> list[UsageRecordModel]:
        stmt = (
            select(UsageRecordModel)
            .where(
                UsageRecordModel.mission_id == mission_id,
                UsageRecordModel.org_id == org_id,
            )
            .order_by(UsageRecordModel.created_at.asc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class ApprovalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_request(
        self,
        approval_id: UUID,
        org_id: UUID,
        mission_id: UUID,
        action_type: str,
        target_resource: str,
        mission_version: int,
        expires_at: datetime,
        secret_key: str,
        task_id: UUID | None = None,
        feedback: str | None = None,
    ) -> HumanApprovalModel:
        digest = compute_action_digest(
            secret=secret_key,
            mission_id=mission_id,
            action_type=action_type,
            target_resource=target_resource,
            mission_version=mission_version,
            expires_at=expires_at,
        )
        approval = HumanApprovalModel(
            id=approval_id,
            org_id=org_id,
            mission_id=mission_id,
            task_id=task_id,
            action_type=action_type,
            target_resource=target_resource,
            action_digest=digest,
            mission_version=mission_version,
            decision=ApprovalDecision.PENDING,
            feedback=feedback,
            expires_at=expires_at,
        )
        self.session.add(approval)
        await self.session.flush()
        return approval

    async def get_by_id_for_org(self, approval_id: UUID, org_id: UUID) -> HumanApprovalModel:
        stmt = select(HumanApprovalModel).where(HumanApprovalModel.id == approval_id)
        res = await self.session.execute(stmt)
        approval = res.scalar_one_or_none()
        if not approval:
            raise CrossTenantAccessError(f"Approval request {approval_id} not found.")
        if approval.org_id != org_id:
            raise CrossTenantAccessError(
                f"Unauthorized cross-tenant access: approval {approval_id} does not belong to org {org_id}."
            )
        return approval

    async def resolve_decision(
        self,
        approval_id: UUID,
        org_id: UUID,
        user_id: UUID,
        decision: ApprovalDecision,
        feedback: str | None,
        secret_key: str,
        current_mission_version: int,
        provided_digest: str | None = None,
    ) -> HumanApprovalModel:
        approval = await self.get_by_id_for_org(approval_id, org_id)

        # 1. Provided digest check
        if provided_digest and provided_digest != approval.action_digest:
            raise DigestMismatchError(
                f"Action digest mismatch: provided digest '{provided_digest}' does not match registered digest '{approval.action_digest}'."
            )

        # 2. Single-use check: replay prevention
        if approval.decision != ApprovalDecision.PENDING:
            raise ApprovalReplayError(
                f"Approval request {approval_id} has already been resolved with decision {approval.decision.value}."
            )

        # 2. Expiration check: time-limited
        now = datetime.now(UTC)
        expires_at = approval.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if now > expires_at:
            approval.decision = ApprovalDecision.EXPIRED
            approval.resolved_at = now
            await self.session.flush()
            raise ApprovalExpiredError(f"Approval request {approval_id} expired at {expires_at.isoformat()}.")

        # 3. Material modifications / version check
        if current_mission_version != approval.mission_version:
            raise ApprovalTamperedError(
                f"Mission state has been modified: approval version {approval.mission_version} does not match current version {current_mission_version}."
            )

        # 4. Canonical action digest check
        valid = verify_action_digest(
            secret=secret_key,
            expected_digest=approval.action_digest,
            mission_id=approval.mission_id,
            action_type=approval.action_type,
            target_resource=approval.target_resource,
            mission_version=approval.mission_version,
            expires_at=approval.expires_at,
        )
        if not valid:
            raise DigestMismatchError(
                f"Action digest verification failed for approval {approval_id}: payload tampered or secret mismatch."
            )

        approval.decision = decision
        approval.feedback = feedback
        approval.resolved_by = user_id
        approval.resolved_at = now
        await self.session.flush()
        return approval

    async def verify_and_consume_for_execution(
        self,
        approval_id: UUID,
        org_id: UUID,
        mission_id: UUID,
        action_type: str,
        provided_digest: str,
        secret_key: str,
        current_mission_version: int,
        target_resource: str | None = None,
    ) -> HumanApprovalModel:
        """Verify that an approval is valid, approved, unexpired, matches action and mission,
        and atomically consume it under the one-time-use policy.
        """
        approval = await self.get_by_id_for_org(approval_id, org_id)

        # 1. Mission boundary check
        if approval.mission_id != mission_id:
            raise CrossTenantAccessError(
                f"Approval {approval_id} is bound to mission {approval.mission_id}, not {mission_id}."
            )

        # 2. Decision state: Must be APPROVED, and not PENDING, REJECTED, EXPIRED, or already CONSUMED
        if approval.decision == ApprovalDecision.PENDING:
            raise ApprovalReplayError(
                f"Approval request {approval_id} is still PENDING and has not been approved by an authorized user."
            )
        if approval.decision == ApprovalDecision.CONSUMED:
            raise ApprovalReplayError(
                f"Approval request {approval_id} has already been consumed (replay attack blocked)."
            )
        if approval.decision != ApprovalDecision.APPROVED:
            raise ApprovalReplayError(f"Approval request {approval_id} has invalid status {approval.decision.value}.")

        # 3. Approver principal check: must have been approved by a human principal
        if approval.resolved_by is None:
            raise ApprovalTamperedError(f"Approval {approval_id} has no recorded resolving principal.")

        # 4. Action and resource match
        if approval.action_type != action_type and not (
            action_type.startswith(approval.action_type) or approval.action_type.startswith(action_type)
        ):
            raise ApprovalTamperedError(
                f"Approval {approval_id} action '{approval.action_type}' does not match requested action '{action_type}'."
            )
        if target_resource and approval.target_resource and approval.target_resource != target_resource:
            raise ApprovalTamperedError(
                f"Approval {approval_id} target '{approval.target_resource}' does not match requested resource '{target_resource}'."
            )

        # 5. Expiration check
        now = datetime.now(UTC)
        expires_at = approval.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if now > expires_at:
            approval.decision = ApprovalDecision.EXPIRED
            approval.resolved_at = now
            await self.session.flush()
            raise ApprovalExpiredError(f"Approval request {approval_id} expired at {expires_at.isoformat()}.")

        # 6. Mission version lock
        if current_mission_version != approval.mission_version:
            raise ApprovalTamperedError(
                f"Mission state modified: approval version {approval.mission_version} does not match current version {current_mission_version}."
            )

        # 7. Action digest check
        if provided_digest != approval.action_digest:
            raise DigestMismatchError("Action digest mismatch: provided digest does not match registered digest.")

        valid = verify_action_digest(
            secret=secret_key,
            expected_digest=approval.action_digest,
            mission_id=approval.mission_id,
            action_type=approval.action_type,
            target_resource=approval.target_resource,
            mission_version=approval.mission_version,
            expires_at=approval.expires_at,
        )
        if not valid:
            raise DigestMismatchError(f"Cryptographic verification failed for approval {approval_id}.")

        # 8. Atomically consume the approval (one-time use) with concurrency lock
        stmt = (
            update(HumanApprovalModel)
            .where(
                HumanApprovalModel.id == approval_id,
                HumanApprovalModel.decision == ApprovalDecision.APPROVED,
            )
            .values(
                decision=ApprovalDecision.CONSUMED,
                resolved_at=now,
            )
        )
        update_res = await self.session.execute(stmt)
        rowcount = getattr(update_res, "rowcount", 0)
        if rowcount == 0:
            raise ApprovalReplayError(
                f"Approval request {approval_id} has already been consumed (concurrent race condition prevented)."
            )
        await self.session.flush()
        approval.decision = ApprovalDecision.CONSUMED
        approval.resolved_at = now
        return approval


class ArtifactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        mission_id: UUID,
        title: str,
        type: ArtifactType = ArtifactType.PRD,
        task_id: UUID | None = None,
    ) -> ArtifactModel:
        # Invariant 10: Artifact ownership consistency
        if task_id is not None:
            stmt = select(TaskModel).where(TaskModel.id == task_id)
            res = await self.session.execute(stmt)
            task = res.scalar_one_or_none()
            if not task:
                raise ArtifactOwnershipError(f"Task {task_id} referenced by artifact does not exist.")
            if task.mission_id != mission_id:
                raise ArtifactOwnershipError(
                    f"Artifact ownership conflict: task {task_id} belongs to mission {task.mission_id}, not {mission_id}."
                )

        artifact = ArtifactModel(
            mission_id=mission_id,
            task_id=task_id,
            type=type,
            title=title,
            current_version=1,
        )
        self.session.add(artifact)
        await self.session.flush()
        return artifact

    async def add_version(
        self,
        artifact_id: UUID,
        version: int,
        storage_path: str,
        sha256_checksum: str,
        size_bytes: int,
    ) -> ArtifactVersionModel:
        ver = ArtifactVersionModel(
            artifact_id=artifact_id,
            version=version,
            storage_path=storage_path,
            sha256_checksum=sha256_checksum,
            size_bytes=size_bytes,
        )
        self.session.add(ver)
        await self.session.flush()
        return ver

    async def list_for_mission(
        self,
        mission_id: UUID,
        org_id: UUID,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[tuple[ArtifactModel, ArtifactVersionModel | None]], str | None, bool]:
        stmt_m = select(MissionModel).where(MissionModel.id == mission_id)
        res_m = await self.session.execute(stmt_m)
        mission = res_m.scalar_one_or_none()
        if not mission:
            raise CrossTenantAccessError(f"Mission {mission_id} not found.")
        if mission.org_id != org_id:
            raise CrossTenantAccessError(
                f"Unauthorized cross-tenant access: mission {mission_id} does not belong to org {org_id}."
            )

        query = (
            select(ArtifactModel, ArtifactVersionModel)
            .outerjoin(
                ArtifactVersionModel,
                (ArtifactModel.id == ArtifactVersionModel.artifact_id)
                & (ArtifactModel.current_version == ArtifactVersionModel.version),
            )
            .where(ArtifactModel.mission_id == mission_id)
        )
        if cursor:
            try:
                cursor_dt = datetime.fromisoformat(cursor)
                query = query.where(ArtifactModel.created_at > cursor_dt)
            except ValueError:
                pass

        query = query.order_by(ArtifactModel.created_at.asc()).limit(limit + 1)
        res = await self.session.execute(query)
        items: list[tuple[ArtifactModel, ArtifactVersionModel | None]] = [(row[0], row[1]) for row in res.all()]
        has_more = len(items) > limit
        if has_more:
            items = items[:limit]
            next_cursor = items[-1][0].created_at.isoformat() if items else None
        else:
            next_cursor = None
        return items, next_cursor, has_more

    async def get_by_id(
        self,
        artifact_id: UUID,
    ) -> tuple[ArtifactModel, ArtifactVersionModel | None] | None:
        query = (
            select(ArtifactModel, ArtifactVersionModel)
            .outerjoin(
                ArtifactVersionModel,
                (ArtifactModel.id == ArtifactVersionModel.artifact_id)
                & (ArtifactModel.current_version == ArtifactVersionModel.version),
            )
            .where(ArtifactModel.id == artifact_id)
        )
        res = await self.session.execute(query)
        row = res.first()
        if not row:
            return None
        return row[0], row[1]


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def stage_event(self, event_type: str, payload: dict[str, Any]) -> TransactionalOutboxModel:
        outbox_event = TransactionalOutboxModel(
            event_type=event_type,
            payload=payload,
            status=OutboxStatus.PENDING,
            retry_count=0,
        )
        self.session.add(outbox_event)
        return outbox_event

    async def get_pending_events(self, limit: int = 50) -> list[TransactionalOutboxModel]:
        stmt = (
            select(TransactionalOutboxModel)
            .where(TransactionalOutboxModel.status == OutboxStatus.PENDING)
            .order_by(TransactionalOutboxModel.created_at.asc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def record_event(
        self,
        org_id: UUID,
        event_type: str,
        payload: dict[str, Any],
        mission_id: UUID | None = None,
    ) -> EventRecordModel:
        event = EventRecordModel(
            org_id=org_id,
            mission_id=mission_id,
            event_type=event_type,
            payload=payload,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_events_for_mission(
        self,
        mission_id: UUID,
        org_id: UUID,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[EventRecordModel], str | None, bool]:
        stmt_m = select(MissionModel).where(MissionModel.id == mission_id)
        res_m = await self.session.execute(stmt_m)
        mission = res_m.scalar_one_or_none()
        if not mission:
            raise CrossTenantAccessError(f"Mission {mission_id} not found.")
        if mission.org_id != org_id:
            raise CrossTenantAccessError(
                f"Unauthorized cross-tenant access: mission {mission_id} does not belong to org {org_id}."
            )

        query = select(EventRecordModel).where(
            EventRecordModel.mission_id == mission_id,
            EventRecordModel.org_id == org_id,
        )
        if cursor:
            try:
                cursor_dt = datetime.fromisoformat(cursor)
                query = query.where(EventRecordModel.created_at > cursor_dt)
            except ValueError:
                pass

        query = query.order_by(EventRecordModel.created_at.asc()).limit(limit + 1)
        res = await self.session.execute(query)
        items = list(res.scalars().all())
        has_more = len(items) > limit
        if has_more:
            items = items[:limit]
            next_cursor = items[-1].created_at.isoformat() if items else None
        else:
            next_cursor = None
        return items, next_cursor, has_more


class IdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, key: str, org_id: UUID) -> IdempotencyKeyModel | None:
        stmt = select(IdempotencyKeyModel).where(
            IdempotencyKeyModel.key == key,
            IdempotencyKeyModel.org_id == org_id,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def record(
        self,
        key: str,
        org_id: UUID,
        response_code: int,
        response_body: dict[str, Any],
        payload_hash: str | None = None,
        ttl_seconds: int = 86400,
    ) -> IdempotencyKeyModel:
        stmt = select(IdempotencyKeyModel).where(IdempotencyKeyModel.key == key)
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            if existing.payload_hash and payload_hash and existing.payload_hash != payload_hash:
                raise DuplicateIdempotencyKeyError(
                    f"Idempotency key '{key}' already executed with different payload hash ({existing.payload_hash} vs {payload_hash})."
                )
            return existing

        now = datetime.now(UTC)
        record = IdempotencyKeyModel(
            key=key,
            org_id=org_id,
            response_code=response_code,
            response_body=response_body,
            payload_hash=payload_hash,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        self.session.add(record)
        await self.session.flush()
        return record


class VerificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(
        self,
        task_id: UUID,
        artifact_version_id: UUID,
        verdict: VerificationVerdict = VerificationVerdict.PASS,
        tests_passed: int = 0,
        tests_failed: int = 0,
        coverage_percentage: Decimal | None = None,
        raw_output: str | None = None,
    ) -> VerificationRunModel:
        run = VerificationRunModel(
            task_id=task_id,
            artifact_version_id=artifact_version_id,
            verdict=verdict,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            coverage_percentage=coverage_percentage,
            raw_output=raw_output,
        )

        self.session.add(run)
        await self.session.flush()
        return run

    async def get_latest_for_task(self, task_id: UUID) -> VerificationRunModel | None:
        stmt = (
            select(VerificationRunModel)
            .where(VerificationRunModel.task_id == task_id)
            .order_by(VerificationRunModel.verified_at.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()


class MCPRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register_server(
        self,
        id: UUID,
        name: str,
        transport: MCPTransportType | str,
        command_or_url: str,
        is_enabled: bool = True,
        trust_classification: str = "LOCAL_TRUSTED",
        auth_policy: str = "NONE",
        allowed_capabilities: list[str] | None = None,
        version: str = "1.0.0",
        verification_status: str = "VERIFIED",
    ) -> MCPServerModel:
        transport_enum = (
            transport if isinstance(transport, MCPTransportType) else MCPTransportType(str(transport).lower())
        )
        stmt = select(MCPServerModel).where(MCPServerModel.name == name)
        res = await self.session.execute(stmt)
        server = res.scalar_one_or_none()
        if server:
            server.transport = transport_enum
            server.command_or_url = command_or_url
            server.is_enabled = is_enabled
            server.trust_classification = trust_classification
            server.auth_policy = auth_policy
            server.allowed_capabilities = allowed_capabilities or []
            server.version = version
            server.verification_status = verification_status
        else:
            server = MCPServerModel(
                id=id,
                name=name,
                transport=transport_enum,
                command_or_url=command_or_url,
                is_enabled=is_enabled,
                trust_classification=trust_classification,
                auth_policy=auth_policy,
                allowed_capabilities=allowed_capabilities or [],
                version=version,
                verification_status=verification_status,
            )
            self.session.add(server)
        await self.session.flush()
        return server

    async def get_server(self, name: str) -> MCPServerModel | None:
        stmt = select(MCPServerModel).where(MCPServerModel.name == name)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_servers(self, enabled_only: bool = True) -> list[MCPServerModel]:
        stmt = select(MCPServerModel)
        if enabled_only:
            stmt = stmt.where(MCPServerModel.is_enabled.is_(True))
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def save_tool_version(
        self,
        id: UUID,
        server_id: UUID,
        tool_name: str,
        version: str = "1.0.0",
        input_schema: dict[str, Any] | None = None,
        description: str | None = None,
        action_classification: str = "READ_ONLY",
        sha256_checksum: str = "",
    ) -> MCPToolVersionModel:
        stmt = select(MCPToolVersionModel).where(
            MCPToolVersionModel.mcp_server_id == server_id,
            MCPToolVersionModel.tool_name == tool_name,
            MCPToolVersionModel.version == version,
        )
        res = await self.session.execute(stmt)
        tool_ver = res.scalar_one_or_none()
        if tool_ver:
            tool_ver.input_schema = input_schema or {}
            tool_ver.description = description
            tool_ver.action_classification = action_classification
            tool_ver.sha256_checksum = sha256_checksum
        else:
            tool_ver = MCPToolVersionModel(
                id=id,
                mcp_server_id=server_id,
                tool_name=tool_name,
                version=version,
                input_schema=input_schema or {},
                description=description,
                action_classification=action_classification,
                sha256_checksum=sha256_checksum,
            )
            self.session.add(tool_ver)
        await self.session.flush()
        return tool_ver

    async def record_invocation(
        self,
        id: UUID,
        org_id: UUID,
        mission_id: UUID | None,
        task_id: UUID | None,
        server_name: str,
        tool_name: str,
        caller_role: str,
        caller_user_id: UUID | None = None,
        arguments_scrubbed: dict[str, Any] | None = None,
    ) -> MCPInvocationModel:
        inv = MCPInvocationModel(
            id=id,
            org_id=org_id,
            mission_id=mission_id,
            task_id=task_id,
            server_name=server_name,
            tool_name=tool_name,
            caller_role=caller_role,
            caller_user_id=caller_user_id,
            arguments_scrubbed=arguments_scrubbed or {},
            status="PENDING",
        )
        self.session.add(inv)
        await self.session.flush()
        return inv

    async def complete_invocation(
        self,
        id: UUID,
        status: str,
        error_message: str | None = None,
        result_summary: str | None = None,
        result_hash: str | None = None,
        duration_ms: int = 0,
    ) -> MCPInvocationModel | None:
        stmt = select(MCPInvocationModel).where(MCPInvocationModel.id == id).with_for_update()
        res = await self.session.execute(stmt)
        inv = res.scalar_one_or_none()
        if inv:
            inv.status = status
            inv.error_message = error_message
            inv.result_summary = result_summary
            inv.result_hash = result_hash
            inv.duration_ms = duration_ms
            inv.completed_at = datetime.now(UTC)
            await self.session.flush()
        return inv
