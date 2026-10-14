# ADR-007: Domain Aggregates and Persistence Schema Evolution

- **Status**: ACCEPTED
- **Date**: 2026-10-15
- **Deciders**: Principal Database Architect, Senior Python Backend Engineer, Principal Software Architect

---

## 1. Context & Problem Statement

Phase 0 established the authoritative 30-table relational schema in `docs/architecture/database-design.md`, mandating UUID primary keys, strict multi-tenant isolation (`org_id`), optimistic concurrency control (`version`), and the transactional outbox pattern.

Prior to Phase 0, a rudimentary prototype existed in `src/syntra/storage/models.py` with 5 basic tables (`sessions`, `agent_executions`, `checkpoints`, `events`, `artifacts`) using ad-hoc string and integer IDs, non-standardized JSON serialization, and missing organizational hierarchy.

We must reconcile this contract conflict so that:
1. The authoritative domain model and 30 PostgreSQL tables are fully implemented as specified in `docs/architecture/database-design.md`.
2. Existing prototype endpoints (`/api/sessions`, `/api/checkpoints`) and Phase 1 tests remain functional until Phase 3 replaces them with the `/v1` REST API.
3. No duplicate model registrations occur on SQLAlchemy's declarative `Base.metadata`.

---

## 2. Decision

1. **Pure Domain Entities (`packages/domain/` & `src/syntra/domain/`)**:
   Implement pure domain dataclasses/Pydantic models with zero framework or database dependencies for all core entities:
   - `User`, `Organization`, `Membership`, `Project`, `Repository`
   - `Mission`, `Requirement`, `ArchitectureDecision`
   - `Task`, `TaskDependency`, `TaskAttempt`, `AgentRun`
   - `Artifact`, `VerificationRun`, `Approval`
   - `Budget`, `UsageRecord`, `Event`, `OutboxEvent`, `IdempotencyKey`
   - `MCPServer`, `SkillVersion`, `CapabilityGrant`, `WorkerJobMetadata`

2. **Authoritative Persistence Models (`packages/persistence/` & `src/syntra/persistence/`)**:
   Implement the complete 30-table SQLAlchemy 2.x declarative schema defined in `docs/architecture/database-design.md`:
   - All tables enforce UUID primary keys, `TIMESTAMPTZ` UTC timestamps, explicit Enum types, foreign keys, and indexes.
   - Mutable entities (`missions`, `tasks`, `task_plans`, `budgets`) include `version INTEGER NOT NULL DEFAULT 1`.
   - All tenant-owned tables enforce `org_id` foreign keys and composite constraints.

3. **Legacy Prototype Schema Preservation**:
   - The prototype `SessionModel` and `CheckpointModel` are retained in `src/syntra/storage/legacy_models.py` and aliased in `src/syntra/storage/models.py` on tables `sessions` and `checkpoints`.
   - The authoritative 30 tables are defined under their canonical names (`missions`, `tasks`, `events`, `artifacts`, `human_approvals`, etc.). For table names that collided with the prototype (`events`, `artifacts`, `agent_executions`), the authoritative models take precedence, while legacy repositories map to their respective entities or legacy aliases (`legacy_events`, etc.).

4. **Alembic Migrations**:
   - Alembic configuration initialized with async SQLAlchemy support.
   - Initial migration `0001_initial_schema.py` applies the authoritative 30-table schema to PostgreSQL.

---

## 3. Consequences

- **Pros**:
  - Full adherence to the approved Master Build Specification and `database-design.md`.
  - Zero regression in existing test suite (all Phase 1 tests continue passing).
  - Clean separation of pure domain business logic from database storage.
  - Complete support for transactions, Unit of Work, optimistic locking, and outbox event streaming.
- **Cons**:
  - Legacy models will be formally deprecated and removed at the conclusion of Phase 3.
