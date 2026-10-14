# SYNTRA Master Implementation Roadmap (Phases 0–13)

**SYNTRA: Synchronized Intelligence for Autonomous Engineering**  
*Master Specification & Gated Phase Milestones*

---

## 1. Executive Roadmap Matrix

| Phase | Phase Name | Focus Subsystems | Key Deliverables | Exit Gate |
|---|---|---|---|---|
| **Phase 0** | **System Architecture & Planning** | Architecture, Contracts, ADRs | Blueprints, DB DDL, State Machines, ADR-001..006 | Architecture approved; zero production code started |
| **Phase 1** | **Project Initialization** | Environment & Infrastructure | Monorepo layout, Docker Compose, Scripts, Health Probes | Developer boots stack and doctor passes |
| **Phase 2** | **Database & Domain Foundation** | Persistence & Outbox | SQLAlchemy models, Alembic migrations, Repositories | Core domain operations testable with zero LLM |
| **Phase 3** | **API, Auth & Governance** | Control Plane & Approvals | `/v1/...` REST API, OIDC/Dev auth, Approval Service | Missions manageable via API headlessly |
| **Phase 4** | **MCP Infrastructure** | Tool Interoperability | MCP Client Manager, Tool Registry, Stdio/SSE Server | Authorized client calls SYNTRA MCP tools |
| **Phase 5** | **Skills & Capability Registry** | Specialized Knowledge | 16 Skill manifests, progressive loader, validator | Tasks load only required skills dynamically |
| **Phase 6** | **Model Runtime** | LLM Engine & Gemini | Google Gen AI SDK adapter, router, cost ledger | Structured Pydantic outputs from Gemini & mock |
| **Phase 7** | **LangGraph Workflow Engine** | Orchestration & FSM | 12-state Mission Graph, Task Graph, Checkpoints | Mission pauses for approval and resumes safely |
| **Phase 8** | **Task Scheduler & Leases** | Parallelism & Fencing | Deterministic DAG scheduler, leases, outbox dispatch | Multi-task DAG executes under worker contention |
| **Phase 9** | **Sandbox Execution** | Isolated Worker Plane | `SandboxProvider`, Git worktrees, patch collector | Worker modifies repo and outputs verified patch |
| **Phase 10** | **Autonomous Engineering Org** | 10 Specialized Agents | PM, Arch, EM, Backend, Frontend, QA, DevOps, Sec, Rev | Pipeline passes work through real handoffs |
| **Phase 11** | **Memory & Self-Correction** | Knowledge & Recovery | Memory stores, failure classifier, bounded replanner | Failure triggers corrective action automatically |
| **Phase 12** | **Verification & Observability** | Quality & Governance | Independent verifier, OpenTelemetry, audit trails | All deliverables backed by independent evidence |
| **Phase 13** | **End-to-End Benchmark** | Full System Proof | Real failing inventory repo fix, worker kill test | Real code fix delivered with reproducible benchmark |

---

## 2. Irreversible Architectural Decisions (Cannot Safely Be Postponed)

1. **Backend-First Modular Monolith with Isolated Workers**: Attempting to refactor a microservices mesh into a monolith or vice versa after implementing persistence and orchestration causes severe schema and deployment churn.
2. **PostgreSQL Relational Schema with Transactional Outbox**: Trying to introduce transactional outbox messaging or row-level lease fencing after building an ad-hoc queue guarantees race conditions and data corruption.
3. **Decoupling LangGraph Checkpoints from Authoritative State**: Treating LangGraph checkpoints as authoritative business entities causes state lock-in and prevents independent database auditing and migrations.
4. **Model Context Protocol (MCP) as Exclusive Tool Standard**: Inventing custom proprietary tool invocation contracts creates technical debt and prevents reuse of standard enterprise MCP tools.
5. **Cryptographic Approval Digests**: Post-hoc approval mechanisms leave systems vulnerable to payload tampering and replay attacks.

---

## 3. Comprehensive Phase Specifications (0 through 13)

### Phase 0: System Architecture and Technical Planning
- **Goal**: Produce a rigorous, implementable, and production-ready architectural blueprint across all subsystems.
- **Prerequisites**: Repository root initialized; Python 3.12+ and `uv` operational.
- **Implementation Components**: Technical architecture docs, PostgreSQL schema specifications, LangGraph FSM design, MCP specs, Agent & Skills specs, ADRs 001–006.
- **Required Interfaces**: System Architecture specifications and formal Pydantic contracts index (`docs/contracts/contract-index.md`).
- **Dependencies**: Official MCP specification `2024-11-05`, Google Gen AI SDK documentation.
- **Tests**: Validation of schema definitions, syntax verification of Mermaid diagrams, contract coherence review.
- **Acceptance Criteria**: All 10 Phase 0 acceptance gates satisfied; zero production service implementation; zero frontend implementation.
- **Expected Deliverables**: `AGENTS.md`, `docs/architecture/*.md`, `docs/decisions/ADR-*.md`, `docs/phases/roadmap.md`, `docs/phases/phase-00.md`.
- **Risks**: Architectural ambiguity leading to implementation rework in subsequent phases.
- **Exit Gate**: Formal Phase 0 verification report signed off.

### Phase 1: Project Initialization
- **Goal**: Establish a reproducible, containerized local development and execution environment.
- **Prerequisites**: Phase 0 verified and approved.
- **Implementation Components**: Monorepo layout (`apps/`, `packages/`, `skills/`), `compose.yaml` (PostgreSQL 16, Redis 7, MinIO S3), `scripts/bootstrap.sh`, `scripts/doctor.sh`, `scripts/smoke-test.sh`, `Makefile`.
- **Required Interfaces**: Liveness probe (`GET /health`) and readiness probe (`GET /health/ready`).
- **Dependencies**: Docker, Docker Compose, `uv`, Python 3.12+.
- **Tests**: Bootstrap script execution, doctor diagnostics, smoke tests, health probe tests.
- **Acceptance Criteria**: New developer can clone repository, execute `make bootstrap`, and pass `make doctor` with clean health status.
- **Expected Deliverables**: Scaffolded directories, operational scripts, CI workflow (`.github/workflows/ci.yml`), updated `README.md`.
- **Risks**: Environment inconsistencies across macOS, Linux, and Windows platforms.
- **Exit Gate**: `scripts/doctor.sh` and automated initialization test suite passing.

### Phase 2: Database and Domain Foundation
- **Goal**: Implement authoritative domain entities, SQLAlchemy 2.x models, and transactional outbox persistence.
- **Prerequisites**: Phase 1 verified.
- **Implementation Components**: 30 PostgreSQL table models, Alembic migrations, repository classes, domain entity validations, task DAG cycle detection.
- **Required Interfaces**: Repository protocols (`MissionRepository`, `TaskRepository`, `OutboxRepository`).
- **Dependencies**: PostgreSQL 16, SQLAlchemy 2.x, `asyncpg`, Alembic.
- **Tests**: Fresh migration apply/rollback tests, foreign key constraint tests, DAG cycle rejection tests, optimistic concurrency tests.
- **Acceptance Criteria**: All core domain operations testable with 100% test pass rate without invoking any external LLM.
- **Expected Deliverables**: SQLAlchemy model classes, Alembic migration scripts, domain repositories, repository unit tests.
- **Risks**: Schema design flaws requiring breaking migrations in later phases.
- **Exit Gate**: Migrations run cleanly from zero, and repository test suite passes.

### Phase 3: API, Authentication, and Governance
- **Goal**: Construct the secure backend control plane exposing REST and WebSocket endpoints.
- **Prerequisites**: Phase 2 verified.
- **Implementation Components**: FastAPI routes for `/v1/projects`, `/v1/missions`, `/v1/approvals`, OIDC/Dev auth, budget reservations, action digest verification.
- **Required Interfaces**: REST API schemas and WebSocket event streams.
- **Dependencies**: FastAPI, Pydantic v2, PyJWT.
- **Tests**: Endpoint authentication tests, cross-tenant isolation tests, approval digest verification tests, budget reservation tests.
- **Acceptance Criteria**: Missions, task plans, and approvals completely manageable via HTTP requests without requiring a GUI.
- **Expected Deliverables**: FastAPI application routes, OpenAPI 3.1 schema, authentication middleware, API integration tests.
- **Risks**: Broken tenant isolation or authentication bypasses.
- **Exit Gate**: All API endpoints verified by automated integration tests.

### Phase 4: MCP Infrastructure
- **Goal**: Implement standardized Model Context Protocol (MCP) tool integration.
- **Prerequisites**: Phase 3 verified.
- **Implementation Components**: `MCPServer`, `MCPClientManager`, `ToolRegistry`, `CapabilityPolicyEngine`, stdio and HTTP/SSE transports.
- **Required Interfaces**: JSON-RPC 2.0 MCP protocol endpoints (`tools/list`, `tools/call`).
- **Dependencies**: Official `mcp` Python SDK (`mcp>=1.1.2`, current `2.3.0`).
- **Tests**: Tool discovery tests, schema validation tests, capability authorization tests, timeout enforcement tests.
- **Acceptance Criteria**: Authorized MCP test client can discover SYNTRA tools and execute sandboxed operations.
- **Expected Deliverables**: MCP server implementation, client session manager, tool registry, MCP integration tests.
- **Risks**: Process leaks from uncollected stdio subprocesses.
- **Exit Gate**: MCP test client executes all standard SYNTRA tools successfully.

### Phase 5: Skills and Capability Registry
- **Goal**: Implement reusable, discoverable engineering skill packages with progressive disclosure.
- **Prerequisites**: Phase 4 verified.
- **Implementation Components**: 16 standardized skill packages, manifest validator, progressive skill loader, evaluation test runner.
- **Required Interfaces**: `SkillRegistry.get_skill()`, `SkillRegistry.get_instructions()`.
- **Dependencies**: PyYAML, Pydantic v2.
- **Tests**: Manifest schema validation tests for all 16 skills, role compatibility tests, progressive loading tests.
- **Acceptance Criteria**: Agent invocations load only explicitly required skills; skills cannot grant permissions independently.
- **Expected Deliverables**: 16 validated skill packages in `skills/`, skill loader module, evaluation runner.
- **Risks**: Prompt token bloat from oversized skill instructions.
- **Exit Gate**: All 16 skill manifests pass schema validation and automated test checks.

### Phase 6: Model Runtime
- **Goal**: Build reliable, structured AI model execution powered by the Google Gen AI SDK.
- **Prerequisites**: Phase 5 verified.
- **Implementation Components**: `GeminiClient` adapter, deterministic `MockModelAdapter`, model router, structured output parser, token/cost ledger.
- **Required Interfaces**: `ModelAdapterInterface.generate_structured()`, `ModelAdapterInterface.generate_text()`.
- **Dependencies**: Google Gen AI SDK (`google-genai>=2.30.0`).
- **Tests**: Pydantic structured output validation tests, retry and rate-limit backoff tests, cost accounting tests, mock provider determinism tests.
- **Acceptance Criteria**: Structured outputs reliably parsed and validated against Pydantic schemas under both live Gemini and mock providers.
- **Expected Deliverables**: Gemini adapter module, mock adapter, model router, model test suite.
- **Risks**: Google Gemini API breaking changes or transient quota exhaustion.
- **Exit Gate**: Model adapter tests pass with both live Gemini (when key present) and mock provider.

### Phase 7: LangGraph Workflow Engine
- **Goal**: Implement durable mission orchestration with cyclic state graphs and checkpointing.
- **Prerequisites**: Phase 6 verified.
- **Implementation Components**: 12-state Mission State Graph, Task Execution Graph, PostgreSQL checkpointer, human approval interrupt/resume handlers.
- **Required Interfaces**: `MissionWorkflow.run()`, `MissionWorkflow.resume()`.
- **Dependencies**: LangGraph, PostgreSQL Checkpointer.
- **Tests**: State transition tests, approval interrupt tests, rejection and replanning tests, process crash resume tests.
- **Acceptance Criteria**: Mission can pause for human approval, resume upon decision, and survive process termination without state loss.
- **Expected Deliverables**: LangGraph workflow graphs, checkpointing integration, state transition tests.
- **Risks**: Graph state desynchronization with PostgreSQL authoritative state.
- **Exit Gate**: Mission graph executes from DRAFT to COMPLETED with deterministic mock agents.

### Phase 8: Task Scheduler and Collaboration
- **Goal**: Coordinate parallel, dependency-aware task execution safely.
- **Prerequisites**: Phase 7 verified.
- **Implementation Components**: Deterministic DAG scheduler, critical path calculator, worker lease manager, heartbeats, stale lease reaper, outbox event dispatcher.
- **Required Interfaces**: `TaskScheduler.schedule_next_ready_tasks()`, `WorkerLeaseManager.acquire_lease()`.
- **Dependencies**: Redis Streams, PostgreSQL.
- **Tests**: Dependency ordering tests, concurrent worker claim tests, lease expiration and reclamation tests, outbox delivery tests.
- **Acceptance Criteria**: Multi-task DAG executes correctly under worker contention, network latency, and worker death.
- **Expected Deliverables**: Scheduler service, lease manager, worker heartbeat loop, scheduler test suite.
- **Risks**: Race conditions in lease acquisition or deadlocks in task graph.
- **Exit Gate**: Concurrent scheduler tests pass with zero duplicate claims or missed tasks.

### Phase 9: Sandbox Execution
- **Goal**: Enable agents to perform genuine engineering work inside disposable isolated environments.
- **Prerequisites**: Phase 8 verified.
- **Implementation Components**: `SandboxProvider` implementation, Git worktree manager, process runner, timeout killer, unified patch extractor, artifact uploader.
- **Required Interfaces**: `SandboxInstance.execute_command()`, `SandboxInstance.get_unified_diff()`.
- **Dependencies**: Git CLI, POSIX process runner, MinIO S3 client.
- **Tests**: Command execution tests, path traversal prevention tests, timeout enforcement tests, patch generation tests.
- **Acceptance Criteria**: Worker modifies isolated repository, runs tests, and produces clean unified diff patch without altering host repo.
- **Expected Deliverables**: Sandbox provider module, Git worktree manager, security boundary tests.
- **Risks**: Host system resource starvation from rogue subprocesses.
- **Exit Gate**: Sandbox modifies sample repository and produces verifiable patch artifact.

### Phase 10: Autonomous Engineering Organization
- **Goal**: Implement the complete 10-agent team with verifiable artifact handoffs.
- **Prerequisites**: Phase 9 verified.
- **Implementation Components**: 10 specialized agent personas (PM, Architect, EM, Backend, Frontend, QA, DevOps, Security, Reviewer, Debugger).
- **Required Interfaces**: Structured agent invocation and result contracts.
- **Dependencies**: Agent Runtime, Model Adapter, Skills Registry, Tool Registry.
- **Tests**: Role contract validation tests, handoff integrity tests, self-review prohibition tests, reviewer rejection tests.
- **Acceptance Criteria**: Multi-agent pipeline passes work through real handoffs (Requirements $\to$ Architecture $\to$ Tasks $\to$ Code $\to$ Tests $\to$ Review) and produces verified code.
- **Expected Deliverables**: 10 agent role definitions, prompt templates, handoff validators, multi-agent test suite.
- **Risks**: Agent hallucination or loop divergence during peer review.
- **Exit Gate**: Multi-agent organization executes sample task and produces approved implementation artifact.

### Phase 11: Memory and Self-Correction
- **Goal**: Make SYNTRA context-aware, adaptive, and recoverable from failures.
- **Prerequisites**: Phase 10 verified.
- **Implementation Components**: Execution/Project/Organizational memory stores, failure classifier, root-cause diagnostic analyzer, bounded replanner.
- **Required Interfaces**: `MemoryService.store()`, `MemoryService.retrieve()`, `FailureClassifier.classify()`.
- **Dependencies**: PostgreSQL (`memory_records`), future pgvector.
- **Tests**: Memory retrieval tests, cross-tenant memory isolation tests, failure classification tests, bounded replanning retry tests.
- **Acceptance Criteria**: Controlled failure triggers automated root-cause analysis and surgical replanning without manual intervention.
- **Expected Deliverables**: Memory service, failure classifier, self-correction loop, recovery test suite.
- **Risks**: Poisoned memory records perpetuating faulty engineering strategies.
- **Exit Gate**: Simulated test failure triggers automatic fix proposal and verification.

### Phase 12: Verification, Security, Observability
- **Goal**: Establish rigorous quality governance, independent verification, and distributed observability.
- **Prerequisites**: Phase 11 verified.
- **Implementation Components**: Independent Verification Service, protected regression test runner, OpenTelemetry exporter, audit logger, secret scrubber.
- **Required Interfaces**: `VerificationService.verify_patch()`, `OpenTelemetry.tracer`.
- **Dependencies**: OpenTelemetry SDK, Pytest, MinIO S3.
- **Tests**: False success rejection tests, regression suite enforcement tests, secret scrubbing tests, trace correlation tests.
- **Acceptance Criteria**: Every successful mission deliverable is backed by immutable independent verification evidence.
- **Expected Deliverables**: Verification service, OpenTelemetry configuration, audit logging pipeline, security tests.
- **Risks**: Verification false positives from flaky test suites.
- **Exit Gate**: All deliverables validated by independent verification suite.

### Phase 13: End-to-End Integration and Benchmark
- **Goal**: Prove that SYNTRA functions as a complete, robust autonomous engineering platform.
- **Prerequisites**: Phase 12 verified.
- **Implementation Components**: Real test repository (FastAPI inventory backend with intentional defects), failure injection worker kill test, benchmark test harness.
- **Required Interfaces**: Complete SYNTRA REST API and CLI.
- **Dependencies**: Full containerized SYNTRA backend stack.
- **Tests**: End-to-end bug fix mission, worker process termination during execution, reproducible benchmark suite vs single-agent baseline.
- **Acceptance Criteria**: SYNTRA autonomously fixes failing inventory endpoint, survives worker termination, and produces reproducible benchmark report.
- **Expected Deliverables**: Benchmark reports, failure recovery verification log, end-to-end integration test suite.
- **Risks**: Unforeseen timing races during worker kill tests.
- **Exit Gate**: Complete end-to-end mission succeeds with verified patch and benchmark evidence.
