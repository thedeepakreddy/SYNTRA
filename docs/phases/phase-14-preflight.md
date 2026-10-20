# SYNTRA Phase 14 Pre-Flight Audit & Baseline Report

**Date**: 2026-10-20  
**Repository**: `/Users/thedeepakreddy/SYNTRA`  
**Git HEAD**: `998c00c4a7384851667dd5ea648533eddf29b92d`  
**Git Branch**: `main`  
**Baseline Test Suite**: 593 passed, 7 skipped, 0 failures (121.30s duration)  
**Static Analysis**: Ruff 0 errors, Mypy 0 errors across 149 source files  
**Active Alembic Migration**: `0005_independent_verification`  
**Database Isolation Boundary**: `syntra_test` active; `syntra_dev` untouched and preserved.

---

## 1. Initial Working-Tree Status

All existing tracked and untracked modifications from Phases 10–13 are preserved intact without any resets, stashes, or overwrites:
- Untracked Phase 10–13 closeout reports and handoff documents (`docs/handoffs/`, `docs/phases/phase-*.md`, `docs/testing/`).
- Untracked Alembic migrations (`0003_memory_embeddings.py`, `0004_memory_feedback.py`, `0005_independent_verification.py`).
- Untracked source trees:
  - `src/syntra/benchmarks/` (Benchmark models, runner, collector, reporter)
  - `src/syntra/observability/` (Tracer, span processors, audit logger)
  - `src/syntra/verification/` (Protected test registry, hermetic verification runner)
  - `tests/fixtures/phase13_inventory/` (Target evaluation microservice)
  - Phase 11–13 test suites (`test_memory_*.py`, `test_secret_scrubber_*.py`, `test_benchmarks_*.py`).

---

## 2. Existing Backend Capabilities & Entry Points

| Capability | Module / Source Files | Current Status |
|---|---|---|
| **FastAPI App Factory** | [`src/syntra/api/app.py`](file:///Users/thedeepakreddy/SYNTRA/src/syntra/api/app.py) | Configured with CORS (`*`), correlation IDs, trace propagation, problem details (RFC 7807), and routers. |
| **Authentication & RBAC** | [`src/syntra/api/auth/`](file:///Users/thedeepakreddy/SYNTRA/src/syntra/api/auth/) | Supports Bearer JWT (OIDC) and dev headers (`X-Dev-User-Id`, `X-Dev-Org-Id`, `X-Dev-Role`) in development environment. Roles: `VIEWER`, `DEVELOPER`, `ADMIN`, `OWNER`. |
| **Projects API** | [`src/syntra/api/v1/routes/projects.py`](file:///Users/thedeepakreddy/SYNTRA/src/syntra/api/v1/routes/projects.py) | `POST /v1/projects`, `GET /v1/projects`, `GET /v1/projects/{project_id}`. |
| **Missions API** | [`src/syntra/api/v1/routes/missions.py`](file:///Users/thedeepakreddy/SYNTRA/src/syntra/api/v1/routes/missions.py) | `POST /v1/missions`, `GET /v1/missions/{id}`, `GET /v1/missions/{id}/plan`, `GET /v1/missions/{id}/tasks`, `GET /v1/missions/{id}/events`, `GET /v1/missions/{id}/artifacts`, `GET /v1/missions/{id}/usage`. |
| **Tasks API** | [`src/syntra/api/v1/routes/tasks.py`](file:///Users/thedeepakreddy/SYNTRA/src/syntra/api/v1/routes/tasks.py) | `GET /v1/tasks/{task_id}`. |
| **Approvals API** | [`src/syntra/api/v1/routes/approvals.py`](file:///Users/thedeepakreddy/SYNTRA/src/syntra/api/v1/routes/approvals.py) | `POST /v1/approvals/{id}/decision` (resolves approval checkpoints with cryptographic digests and idempotency). |
| **Health & Telemetry** | [`src/syntra/api/routes/health.py`](file:///Users/thedeepakreddy/SYNTRA/src/syntra/api/routes/health.py) | `GET /v1/health`, `GET /v1/ready`, `GET /telemetry`. |
| **Model Routing** | [`src/syntra/llm/router.py`](file:///Users/thedeepakreddy/SYNTRA/src/syntra/llm/router.py), [`src/syntra/llm/config.py`](file:///Users/thedeepakreddy/SYNTRA/src/syntra/llm/config.py) | `ModelRouter` maps 10 specialist personas to tiers (`FAST`, `BALANCED`, `REASONING`). Backed by [`config/models.yaml`](file:///Users/thedeepakreddy/SYNTRA/config/models.yaml). |
| **Budget & Cost Ledger** | [`src/syntra/persistence/repositories.py`](file:///Users/thedeepakreddy/SYNTRA/src/syntra/persistence/repositories.py) | `BudgetRepository` tracks token allocations, cost limits, concurrency, and duration limits. |
| **Audit Logging** | [`src/syntra/observability/audit_logger.py`](file:///Users/thedeepakreddy/SYNTRA/src/syntra/observability/audit_logger.py) | Thread-safe, fail-closed JSONL logger computing SHA-256 digests over redacted payloads for 11 canonical security events. |
| **Benchmarks** | [`src/syntra/benchmarks/`](file:///Users/thedeepakreddy/SYNTRA/src/syntra/benchmarks/) | Benchmark runner, metric collector (7 metrics), and reporter emitting `manifest.json`, `summary.json`, `audit.jsonl`, `verification.json`. |

---

## 3. Gaps Requiring API Extensions for Control Center

To support the 13 required Control Center destinations without fabricating mock data or bypassing backend invariants, the following endpoints must be added to the FastAPI backend:

1. **Approvals Inbox**:
   - `GET /v1/approvals`: List all pending and historical approval requests filtered by status (`PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`) with tenant isolation.
   - `GET /v1/approvals/{approval_id}`: Retrieve full details for a single approval request, including target resource, version, action digest, and requesting mission.
2. **Global Missions Explorer**:
   - `GET /v1/missions`: List missions across projects with state filtering (`RUNNING`, `AWAITING_APPROVAL`, `COMPLETED`, `FAILED`, etc.), pagination, and sort order.
3. **Agent Registry & Specialist Roster**:
   - `GET /v1/agents`: List the 10 specialized engineering personas from [`AGENTS.md`](file:///Users/thedeepakreddy/SYNTRA/AGENTS.md), including allowed tools, capability profiles, assigned model tiers, and operational status.
4. **Model Routing & Policy Governance**:
   - `GET /v1/models`: List registered models, provider specifications, lifecycle status, context windows, and verified pricing from [`config/models.yaml`](file:///Users/thedeepakreddy/SYNTRA/config/models.yaml).
   - `GET /v1/models/routing`: Retrieve the active routing policy matrix mapping personas to model tiers.
   - `POST /v1/models/routing/simulate`: Simulate a routing decision for an arbitrary role/complexity/budget request to provide real-time decision traceability in the UI.
5. **System Overview & Diagnostic Aggregation**:
   - `GET /v1/system/overview`: Consolidated operational overview (active mission counts by state, pending approvals, total budget vs spend, agent status, and subsystem health check summary).
6. **Benchmark & Evaluation Explorer**:
   - `GET /v1/benchmarks`: List completed benchmark evaluation runs from `benchmarks/results/` with summary status, duration, and metrics.
   - `GET /v1/benchmarks/{run_id}`: Retrieve detailed run artifacts (`manifest.json`, `summary.json`, `verification.json`).
7. **Audit Trail Explorer**:
   - `GET /v1/audit`: Query historical cryptographic audit events with filtering by `event_type`, `mission_id`, and outcome.

---

## 4. Frontend Architecture & Technology Stack

- **Framework**: Modern React 19 + TypeScript with Vite build tooling located in [`frontend/`](file:///Users/thedeepakreddy/SYNTRA/frontend/).
- **Routing**: Client-side routing with clean URL routing supporting all 13 required views.
- **Styling & Design System**: Tailwind CSS with engineering-grade design tokens (monospace numerals, distinct semantic badge styles, WCAG AA contrast ratios, dark/light aware, visible keyboard focus indicators).
- **Icons & Affordances**: Lucide React icons paired with explicit text labels. No mystery icon-only buttons for primary actions.
- **State & Data Fetching**: Standardized typed API client (`frontend/src/api/client.ts`) with request validation, dev auth header injection, error handling, and structured state representations (loading, empty, partial, stale, error).
- **Zero Mock Policy**: Every control calls real backend endpoints. If a dependency is offline, a clear `Unavailable` card explaining the prerequisite is displayed.

---

## 5. Security & Multi-Tenancy Boundary Rules

1. **Authentication Enforcement**: Every request to `/v1/` routes passes through `get_current_user` dependency, enforcing tenant isolation via `user.org_id`.
2. **Secret Scrubbing**: Frontend never receives or stores raw API keys or provider secrets. Passwords and credentials are scrubbed server-side via `SecretRedactor`.
3. **Approval Integrity**: Approval decisions require cryptographic action digests (`action_digest`) matching the registered checkpoint.
4. **No Destructive DB Operations**: Read/write operations use standard SQLAlchemy unit-of-work repositories. No raw SQL injection vectors or arbitrary shell executions.

---

## 6. Phase 14 Staged Implementation Workflow

- **Stage A**: Pre-Flight Audit & Baseline Verification (`docs/phases/phase-14-preflight.md`) $\longrightarrow$ Gate A.
- **Stage B**: Backend API Contracts & Endpoints (`docs/phases/phase-14-api-contracts.md`) $\longrightarrow$ Gate B.
- **Stage C**: Frontend Project Scaffolding & Navigation (`frontend/`) $\longrightarrow$ Gate C.
- **Stage D**: Core Operational Pages (Overview, Projects, Missions, Approvals, Runs, Benchmarks, Audit, Health) $\longrightarrow$ Gate D.
- **Stage E**: Model Routing, Policy Visibility & Budget Controls (`docs/phases/phase-14-model-routing.md`) $\longrightarrow$ Gate E.
- **Stage F**: Integration Testing, Feature Inventory & User Journeys (`docs/phases/phase-14-feature-inventory.md`, `docs/phases/phase-14-testing.md`, `docs/phases/phase-14-security-review.md`) $\longrightarrow$ Gate F.
- **Stage G**: Final Regression, Full Verification & Phase 14 Closeout Report (`docs/phases/phase-14.md`) $\longrightarrow$ Gate G (`PHASE_14_PASSED`).
