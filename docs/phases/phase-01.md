# Phase 1: Project Initialization

## 1. Goal
Create a reproducible, robust, and production-ready backend development and execution environment for SYNTRA. Establish the monorepo directory layout according to Section 24 of the Master Build Specification, complete containerized infrastructure definitions (PostgreSQL 16, Redis 7, MinIO S3), operational diagnostic scripts (`bootstrap.sh`, `doctor.sh`, `smoke-test.sh`), comprehensive health checks, and CI configuration.

---

## 2. Prerequisites
- Phase 0 verified and complete (`docs/phases/phase-00.md`).
- Project renamed to SYNTRA across all packages, documentation, and tests.
- Python 3.12+ and `uv` package manager operational.

---

## 3. Scope of Implementation

### 3.1 Monorepo Layout (Section 24 Specification)
Scaffold structured directories and package anchors (`__init__.py` and `py.typed`):
- `apps/`:
  - `api/`: FastAPI control plane application entry points.
  - `orchestrator/`: LangGraph mission coordinator service.
  - `scheduler/`: Task DAG scheduler and lease reconciliation worker.
  - `worker-controller/`: Sandbox execution worker controller.
  - `mcp-server/`: SYNTRA MCP server entry point.
- `packages/`:
  - `domain/`: Pure domain entities and aggregates (zero framework dependencies).
  - `contracts/`: Data schemas, events, and RPC contracts.
  - `persistence/`: SQLAlchemy models, migrations, and repositories.
  - `agents/`: Specialized agent implementations and prompts.
  - `model-runtime/`: Model adapters, router, token/cost ledger.
  - `mcp-gateway/`: MCP client manager and tool authorization gateway.
  - `tool-registry/`: Local and remote tool discovery and execution.
  - `skill-registry/`: Skill loader, parser, and manifest validator.
  - `sandbox/`: SandboxProvider, worktree management, isolated execution.
  - `memory/`: Execution, project, and organizational memory storage.
  - `evaluation/`: Independent verification, benchmarks, and scoring.
  - `security/`: Approval validation, cryptographic digests, credential scrubbing.
  - `telemetry/`: OpenTelemetry tracing, metrics, and structured logging.
- `skills/`:
  - Scaffold 16 standardized skill packages with validated `manifest.yaml` and `SKILL.md`:
    1. `requirements-analysis`
    2. `system-architecture`
    3. `task-decomposition`
    4. `backend-api-development`
    5. `frontend-development`
    6. `database-engineering`
    7. `test-driven-development`
    8. `debugging-and-root-cause-analysis`
    9. `code-review`
    10. `security-review`
    11. `git-workflow`
    12. `devops-and-ci`
    13. `api-contract-testing`
    14. `dependency-management`
    15. `integration-testing`
    16. `documentation-generation`
- Support directories:
  - `config/`: Environment profiles and global settings.
  - `migrations/`: Alembic database migration scripts.
  - `infra/`: Docker, Compose, and orchestration definitions.
  - `scripts/`: Operational utilities (`bootstrap.sh`, `doctor.sh`, `smoke-test.sh`).
  - `tests/`: Categorized test suites (`unit/`, `integration/`, `contract/`, `security/`, `e2e/`).
  - `benchmarks/`: Benchmark suites (`fixtures/`, `baselines/`, `reports/`).

### 3.2 Infrastructure & Dependencies
- Add infrastructure clients to `pyproject.toml`:
  - `redis>=5.2.0` (for task queuing and outbox streaming)
  - `minio>=7.2.10` (for S3 artifact storage)
- Update `uv.lock` with deterministic pinned hashes.
- Create `compose.yaml` (and maintain `docker-compose.yml`) containing:
  - `postgres` (PostgreSQL 16 with health check)
  - `redis` (Redis 7 Alpine with `redis-cli ping` health check)
  - `minio` (MinIO S3 storage with health check)
  - `backend` (SYNTRA FastAPI application)

### 3.3 Configuration & Health Checks
- Extend `src/syntra/core/config.py` with:
  - Redis configuration (`SYNTRA_REDIS_URL`)
  - MinIO / S3 configuration (`SYNTRA_S3_ENDPOINT`, `SYNTRA_S3_ACCESS_KEY`, `SYNTRA_S3_SECRET_KEY`, `SYNTRA_S3_BUCKET`, `SYNTRA_S3_SECURE`)
- Implement comprehensive health checks in `src/syntra/api/routes/health.py`:
  - `/health`: Liveness probe (200 OK)
  - `/health/ready`: Deep readiness probe verifying database connectivity, Redis responsiveness, MinIO availability, and sandbox filesystem writeability.

### 3.4 Operational Scripts & CI
- `scripts/bootstrap.sh`: Automates virtual environment setup, installs dependencies via `uv`, creates local storage directories, and prepares `.env`.
- `scripts/doctor.sh`: Diagnostic tool verifying Python runtime, `uv`, Git, PostgreSQL, Redis, MinIO, and file permissions.
- `scripts/smoke-test.sh`: Automated sanity verification covering package imports, health endpoints, CLI commands, and test suites.
- `.github/workflows/ci.yml`: Automated CI pipeline running linting, formatting checks, type checks, doctor diagnostics, and test suites.
- `Makefile`: Standardized operational targets (`bootstrap`, `doctor`, `smoke-test`, `up`, `down`, `test`, `test-cov`).

---

## 4. Acceptance Criteria Checklist
- [x] Monorepo directories (`apps/`, `packages/`, `skills/`, `config/`, `migrations/`, `infra/`, `scripts/`, `tests/`, `benchmarks/`) created and validated.
- [x] 16 skill packages populated with valid `manifest.yaml` and `SKILL.md`.
- [x] `redis` and `minio` dependencies added to `pyproject.toml` and pinned in `uv.lock`.
- [x] `compose.yaml` configured with healthy PostgreSQL, Redis, and MinIO services.
- [x] `src/syntra/core/config.py` loaded with Redis and MinIO settings.
- [x] `GET /health/ready` endpoint implemented and verified against PostgreSQL, Redis, and MinIO.
- [x] `scripts/bootstrap.sh`, `scripts/doctor.sh`, and `scripts/smoke-test.sh` created with executable permissions and verified.
- [x] `.github/workflows/ci.yml` created.
- [x] `Makefile` updated with all required operational targets.
- [x] All automated tests passing without requiring paid external API credentials (42/42 tests passing).
- [x] Zero frontend code created.

---

## 5. Verification Results
- `scripts/doctor.sh`: **8 Passed, 4 Warnings, 0 Failures** (clean health status).
- `scripts/smoke-test.sh`: **Passed** (package import, CLI help, 16 skill manifests, test suite).
- Pytest suite: **42 passed in 0.81s** (100% pass rate).
- Dependency lockfile: `uv.lock` synchronized and pinned with cryptographic hashes.

---

## 6. Phase 1 Status
- **Status**: **VERIFIED_COMPLETE**
- **Next Phase**: **Phase 2 — Database and Domain Foundation**
