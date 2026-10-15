"""Unit of Work pattern managing database transactions, repositories, and transactional outbox staging."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from syntra.persistence.repositories import (
    ApprovalRepository,
    ArtifactRepository,
    BudgetRepository,
    IdempotencyRepository,
    MCPRepository,
    MissionRepository,
    OrganizationRepository,
    OutboxRepository,
    ProjectRepository,
    TaskRepository,
    VerificationRepository,
)


class SqlAlchemyUnitOfWork:
    """Async Unit of Work ensuring all repository mutations and outbox events commit atomically."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        session: AsyncSession | None = None,
    ) -> None:
        self.session_factory = session_factory
        self._session = session
        self._owns_session = session is None

        # Repositories initialized when session is active
        self._organizations: OrganizationRepository | None = None
        self._projects: ProjectRepository | None = None
        self._missions: MissionRepository | None = None
        self._tasks: TaskRepository | None = None
        self._budgets: BudgetRepository | None = None
        self._artifacts: ArtifactRepository | None = None
        self._approvals: ApprovalRepository | None = None
        self._outbox: OutboxRepository | None = None
        self._idempotency: IdempotencyRepository | None = None
        self._verifications: VerificationRepository | None = None
        self._mcp: MCPRepository | None = None

        if self._session is not None:
            self._init_repositories(self._session)

    def _init_repositories(self, session: AsyncSession) -> None:
        self._organizations = OrganizationRepository(session)
        self._projects = ProjectRepository(session)
        self._missions = MissionRepository(session)
        self._tasks = TaskRepository(session)
        self._budgets = BudgetRepository(session)
        self._artifacts = ArtifactRepository(session)
        self._approvals = ApprovalRepository(session)
        self._outbox = OutboxRepository(session)
        self._idempotency = IdempotencyRepository(session)
        self._verifications = VerificationRepository(session)
        self._mcp = MCPRepository(session)

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("Unit of Work is not active. Use 'async with uow:' context manager.")
        return self._session

    @property
    def organizations(self) -> OrganizationRepository:
        assert self._organizations is not None
        return self._organizations

    @property
    def projects(self) -> ProjectRepository:
        assert self._projects is not None
        return self._projects

    @property
    def missions(self) -> MissionRepository:
        assert self._missions is not None
        return self._missions

    @property
    def tasks(self) -> TaskRepository:
        assert self._tasks is not None
        return self._tasks

    @property
    def budgets(self) -> BudgetRepository:
        assert self._budgets is not None
        return self._budgets

    @property
    def artifacts(self) -> ArtifactRepository:
        assert self._artifacts is not None
        return self._artifacts

    @property
    def approvals(self) -> ApprovalRepository:
        assert self._approvals is not None
        return self._approvals

    @property
    def outbox(self) -> OutboxRepository:
        assert self._outbox is not None
        return self._outbox

    @property
    def idempotency(self) -> IdempotencyRepository:
        assert self._idempotency is not None
        return self._idempotency

    @property
    def verifications(self) -> VerificationRepository:
        assert self._verifications is not None
        return self._verifications

    @property
    def mcp(self) -> MCPRepository:
        assert self._mcp is not None
        return self._mcp

    def publish_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Stage an event into the transactional outbox table within the active transaction."""
        self.outbox.stage_event(event_type=event_type, payload=payload)

    async def commit(self) -> None:
        """Commit the active database transaction."""
        if self._session:
            await self._session.commit()

    async def rollback(self) -> None:
        """Roll back all uncommitted mutations in the active transaction."""
        if self._session:
            await self._session.rollback()

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        if self._owns_session:
            self._session = self.session_factory()
            self._init_repositories(self._session)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            await self.rollback()
        if self._owns_session and self._session:
            await self._session.close()
            self._session = None
            self._organizations = None
            self._projects = None
            self._missions = None
            self._tasks = None
            self._budgets = None
            self._artifacts = None
            self._approvals = None
            self._outbox = None
            self._idempotency = None
