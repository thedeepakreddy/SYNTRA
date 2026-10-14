# DevSwarm Master Implementation Roadmap (Phases 0–13)

This roadmap outlines the complete 14-phase development program for DevSwarm in accordance with the DevSwarm Master Build Specification.

---

## Phase Overview Matrix

| Phase | Phase Name | Focus Area | Key Deliverables |
|---|---|---|---|
| **Phase 0** | **Architecture and Implementation Planning** | Blueprint & Contracts | Architecture docs, schemas, ADRs, Phase 0 report |
| **Phase 1** | **Project Initialization** | Environment & Infrastructure | Monorepo structure, Compose, Redis, MinIO, Makefile |
| **Phase 2** | **Database and Domain Foundation** | Core Domain & PostgreSQL | SQLAlchemy models, Alembic migrations, Outbox, Repos |
| **Phase 3** | **API, Authentication, and Governance** | Control Plane & Approvals | `/v1/` REST API, OIDC/Dev auth, Budgets, Approvals |
| **Phase 4** | **MCP Infrastructure** | Tool Interoperability | MCP Client Manager, Tool Registry, Stdio/HTTP Server |
| **Phase 5** | **Skills and Capability Registry** | Reusable Engineering Skills | 16 Skill packages, Manifest validator, Progressive loading |
| **Phase 6** | **Model Runtime** | LLM Engine & Gemini | Google Gen AI SDK adapter, Router, Token/Cost ledger |
| **Phase 7** | **LangGraph Workflow Engine** | Orchestration & State Machine | Mission & Task Graphs, PostgreSQL Checkpoints |
| **Phase 8** | **Task Scheduler & Collaboration** | Dependency DAG & Leases | Deterministic scheduler, Concurrency, Leases, Heartbeats |
| **Phase 9** | **Sandbox Execution** | Isolated Worker Plane | SandboxProvider, Worktrees, Resource limits, Patches |
| **Phase 10** | **Autonomous Engineering Organization** | 10 Specialized Agents | PM, Arch, EM, Backend, Frontend, QA, DevOps, Sec, Review |
| **Phase 11** | **Memory and Self-Correction** | Knowledge & Recovery | Execution/Project/Org Memory, Failure classifier |
| **Phase 12** | **Verification, Security, Observability**| Quality & Governance | Independent verifier, Protected suites, Tracing |
| **Phase 13** | **End-to-End Integration & Benchmark** | Full System Proof | Real failing inventory repo fix, Failure injection test |

---

## Detailed Phase Specifications

### Phase 0: Architecture and Implementation Planning
- **Goal**: Produce a detailed, implementable backend blueprint and contract specifications.
- **Tasks**: Architecture documents, ERD, LangGraph state machine design, MCP design, Agent design, Security model.
- **Exit Criteria**: Every subsystem has a documented owner, all contracts defined, no frontend code started.

### Phase 1: Project Initialization
- **Goal**: Create a reproducible backend development environment.
- **Tasks**: Monorepo scaffolding, `pyproject.toml`, `uv.lock`, Docker Compose (PostgreSQL, Redis, MinIO), `scripts/bootstrap.sh`, `scripts/doctor.sh`, Makefile targets.
- **Exit Criteria**: Developer can bootstrap and run health checks from clean clone.

### Phase 2: Database and Domain Foundation
- **Goal**: Implement authoritative application state and transactional outbox.
- **Tasks**: SQLAlchemy 2.x models, Alembic migrations, domain entities, task DAG validation (reject cycles), tenant isolation.
- **Exit Criteria**: Core domain operations testable with zero LLM invocations.

### Phase 3: API, Authentication, and Governance
- **Goal**: Create the secure backend control plane.
- **Tasks**: `/v1/projects`, `/v1/missions`, `/v1/approvals`, OIDC/Dev auth, budget reservations, action digest verification.
- **Exit Criteria**: Missions and approvals completely manageable via REST API without frontend.

### Phase 4: MCP Infrastructure
- **Goal**: Implement secure MCP tool interoperability.
- **Tasks**: MCP Client Manager, Server Registry, Tool Registry, Capability Policy Gateway, Stdio/HTTP transports.
- **Exit Criteria**: Authorized test client can discover and call DevSwarm MCP tools.

### Phase 5: Skills and Capability Registry
- **Goal**: Create reusable, discoverable engineering skills.
- **Tasks**: 16 initial skill manifests, on-demand loader, capability validation, evaluation runner.
- **Exit Criteria**: Tasks dynamically load only required skills via progressive disclosure.

### Phase 6: Model Runtime
- **Goal**: Build reliable structured AI execution with Google Gen AI SDK.
- **Tasks**: Provider adapter, Gemini client, Mock provider, Pydantic structured output validation, cost ledger.
- **Exit Criteria**: Validated structured outputs obtained from Gemini and deterministic mock.

### Phase 7: LangGraph Workflow Engine
- **Goal**: Implement durable mission orchestration.
- **Tasks**: Mission Graph, Task Execution Graph, PostgreSQL checkpointing, human approval pause/resume.
- **Exit Criteria**: Mission can pause for approval and resume safely without state loss.

### Phase 8: Task Scheduler and Collaboration
- **Goal**: Coordinate parallel tasks safely.
- **Tasks**: Deterministic DAG scheduler, critical-path estimation, leases, heartbeats, outbox dispatch.
- **Exit Criteria**: Multi-task DAG executes under contention with stale worker detection.

### Phase 9: Sandbox Execution
- **Goal**: Allow agents to execute real engineering work in isolation.
- **Tasks**: SandboxProvider, Git worktree isolation, non-root execution, timeout enforcement, patch collection.
- **Exit Criteria**: Worker modifies isolated repository, runs tests, and produces patch without altering host.

### Phase 10: Autonomous Engineering Organization
- **Goal**: Implement the actual 10-agent team with real handoffs.
- **Tasks**: Product Manager, Architect, EM, Backend, Frontend, QA, DevOps, Security, Reviewer, Debugger.
- **Exit Criteria**: Multi-agent pipeline passes work through real handoffs to produce verified code.

### Phase 11: Memory and Self-Correction
- **Goal**: Make DevSwarm context-aware and recoverable.
- **Tasks**: Execution, project, and organizational memory; failure classifier; bounded replanning.
- **Exit Criteria**: Controlled failure triggers automatic corrective action without manual intervention.

### Phase 12: Verification, Security, Observability
- **Goal**: Establish engineering quality, independent verification, and distributed observability.
- **Tasks**: Independent verification service, regression test runner, OpenTelemetry, audit logging.
- **Exit Criteria**: All successful mission deliverables backed by independent verification evidence.

### Phase 13: End-to-End Integration and Benchmark
- **Goal**: Prove DevSwarm as a complete autonomous software engineering platform.
- **Tasks**: Real inventory backend bug-fix mission, worker kill failure test, benchmark comparison against baseline.
- **Exit Criteria**: DevSwarm completes real engineering work, survives worker failure, and produces reproducible evidence.
