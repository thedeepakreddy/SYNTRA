# Phase 2: PostgreSQL and Domain Foundation

## 1. Goal
Implement SYNTRA's authoritative application state and relational persistence layer using PostgreSQL 16, SQLAlchemy 2.x, and Alembic migrations. Deliver typed domain entities, deterministic lifecycle state machines, a pure DAG validator for engineering task graphs, multi-tenant isolation, optimistic concurrency control, and transactional outbox event publishing.

---

## 2. Prerequisites
- Phase 1 verified and complete (`docs/phases/phase-01.md`).
- Monorepo package directories (`packages/domain`, `packages/persistence`) operational.
- PostgreSQL 16 / SQLite engine configured and tested.

---

## 3. Scope of Implementation

### 3.1 Domain Entities (`src/syntra/domain/` & `packages/domain/`)
Pure Python domain models and value objects with zero framework dependencies:
- **Tenancy & Projects**: `User`, `Organization`, `Membership`, `Project`, `Repository`.
- **Planning & Decisions**: `Mission`, `Requirement`, `ArchitectureDecision`.
- **Tasks & Execution**: `TaskPlan`, `Task`, `TaskDependency`, `TaskAttempt`, `AgentRun`, `WorkerJobMetadata`, `WorkerLease`.
- **Artifacts & Verification**: `Artifact`, `ArtifactVersion`, `VerificationRun`.
- **Governance & Approvals**: `Approval`, `Budget`, `UsageRecord`.
- **Reliable Messaging & Observability**: `Event`, `OutboxEvent`, `IdempotencyKey`, `MemoryRecord`.
- **Tools & Skills**: `MCPServer`, `MCPToolVersion`, `Skill`, `SkillVersion`, `CapabilityGrant`.

### 3.2 Authoritative Persistence Schema (`src/syntra/persistence/` & `packages/persistence/`)
SQLAlchemy 2.x declarative models representing all 30 PostgreSQL tables specified in `docs/architecture/database-design.md`:
- UUID primary keys via `sqlalchemy.Uuid(as_uuid=True)`.
- Temporal standards: `TIMESTAMPTZ` recorded strictly in UTC (`datetime.now(UTC)`).
- Universal JSON compatibility supporting PostgreSQL `JSONB` and SQLite `JSON`.
- Explicit enum types for state and decision boundaries.
- Optimistic concurrency control (`version INTEGER DEFAULT 1`) on mutable entities (`missions`, `tasks`, `task_plans`, `budgets`).
- Foreign key constraints with cascading deletes or strict restrict policies.
- Database indexes on foreign keys, state filters, and unique tenant composite keys.

### 3.3 Alembic Migration Engine
- Configured `alembic.ini` and async migration environment `migrations/env.py`.
- Migration script `migrations/versions/0001_initial_schema.py` creating all 30 relational tables and preserving legacy prototype tables with reversible `downgrade()`.
- Verified migration execution on fresh database, schema inspection, and clean downgrade.

### 3.4 Domain State Machines & Invariants
- **Mission Lifecycle**: Deterministic transition function enforcing valid state progression (`DRAFT` -> `PLANNING` -> `AWAITING_APPROVAL` -> `READY` -> `RUNNING` -> `PAUSED` / `REPLANNING` / `VERIFYING` -> `AWAITING_DELIVERY_APPROVAL` -> `COMPLETED` / `FAILED` / `CANCELLED`). Enforces validated human approval decisions before advancing to `READY` or `COMPLETED`.
- **Task Lifecycle**: Enforces transition rules (`PENDING` -> `READY` -> `ASSIGNED` -> `IN_PROGRESS` -> `BLOCKED` / `REVIEW` / `VERIFYING` -> `COMPLETED` / `FAILED`). Enforces separation of powers: agents cannot mutate task states directly.
- **Task Attempt Lifecycle**: Enforces `INITIALIZING` -> `RUNNING` -> `AWAITING_TOOL` / `EVALUATING` -> `SUCCEEDED` / `FAILED` / `TIMED_OUT`.

### 3.5 Transaction Safety & Repositories
- **Unit of Work**: `SqlAlchemyUnitOfWork` context manager managing transactions, scoped repositories, and rollback on unhandled exceptions.
- **Transactional Outbox**: Outbox events staged atomically in `transactional_outbox` within the business transaction, preventing dual-write loss.
- **Optimistic Concurrency**: Repositories check `version = :expected_version` and increment `version + 1`, raising `OptimisticLockError` on collision.
- **Strict Tenant Scoping**: All queries filter by `org_id`, raising `CrossTenantAccessError` on unauthorized access.
- **Idempotency Registry**: Enforces unique idempotency keys with payload hash verification, rejecting duplicate executions.
- **Budget Governance**: Enforces hard token and cost limits, blocking reservations exceeding allocation.

### 3.6 Task DAG Validation
- Pure domain validator `validate_task_dag(tasks, dependencies)`:
  - Rejects circular dependencies using Kahn's topological sort algorithm.
  - Rejects self-dependencies (`task_id == depends_on_task_id`).
  - Rejects unknown task references in dependencies.
  - Rejects cross-mission dependencies.
  - Returns tasks in topological order.

---

## 4. Acceptance Criteria Checklist
- [x] Migrations work cleanly on an empty database (`tests/test_migrations.py`).
- [x] All 30 relational tables created with UUID primary keys, UTC timestamps, and foreign keys.
- [x] Domain operations are transaction-safe with atomic Unit of Work rollback (`test_transaction_rollback`).
- [x] Task graph cycles, self-dependencies, and cross-mission links are rejected (`test_cyclic_task_graphs`, `test_cross_mission_task_references`).
- [x] Invalid lifecycle state jumps are rejected (`test_invalid_mission_transitions`).
- [x] Multi-tenant isolation is strictly enforced across repositories (`test_cross_tenant_data_access`).
- [x] Duplicate commands with identical idempotency keys return cached responses; payload conflicts are rejected (`test_duplicate_idempotency_keys`).
- [x] Transactional outbox records commit atomically with domain entities (`test_outbox_consistency`).
- [x] Budget reservation and limits are enforced atomically (`test_budget_constraints`).
- [x] Artifact and task mission ownership consistency is enforced (`test_artifact_ownership_consistency`).
- [x] All 10 mandatory test-first scenarios pass without regression (63 passed, 3 skipped).
- [x] Zero graphical frontend code created.

---

## 5. Verification Results
- **Pytest Suite**: **63 passed, 3 skipped in 1.93s** (100% pass rate across all unit, domain, migration, and mock suites).
- **Alembic Migrations**: **PASS** (`tests/test_migrations.py` verifies upgrade to head, schema consistency across 30 tables, downgrade to base, and re-upgrade).
- **Type Checking**: `mypy src/syntra` **Success: no issues found in 67 source files**; `mypy packages` **Success: no issues found in 13 source files**.
- **Linting**: `ruff check .` **All checks passed!**
- **Doctor Diagnostic**: **8 Passed, 4 Warnings, 0 Failures** (`scripts/doctor.sh`).
- **Smoke Test**: **PASS** (`scripts/smoke-test.sh`).

---

## 6. Phase 2 Status
- **Status**: **VERIFIED_COMPLETE**
- **Next Phase**: **Phase 3 — Control Plane API, Authentication, and Governance**
