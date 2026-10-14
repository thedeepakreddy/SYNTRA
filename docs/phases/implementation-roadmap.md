# DevSwarm Master Build Specification & Implementation Roadmap

## 1. Project Overview & Guiding Principles
**DevSwarm** is a production-oriented autonomous multi-agent software engineering platform built on Google Gemini through the supported Google Gen AI SDK (`google-genai`). DevSwarm coordinates specialized AI agents (Architect, Planner, Coder, Reviewer, Tester, Security, Orchestrator) under a hybrid autonomy governance model with strict workspace sandboxing and deterministic execution guarantees.

### Guiding Principles:
1. **Backend-First Modular Monolith**: Clear domain boundaries, zero premature microservice fragmentation, sub-millisecond in-process eventing.
2. **Deterministic State Graphs**: Workflows execute as deterministic, cyclic, stateful graphs with rigorous termination bounds and self-healing feedback cycles.
3. **Hybrid Autonomy**: Multi-tier autonomy levels with risk-evaluated checkpoint gates for human-in-the-loop oversight.
4. **Isolated Sandbox Execution**: Strict directory boundaries, path traversal guards, command whitelists, and timeout enforcement.
5. **Standardized Protocols**: Native support for Google Gen AI SDK, OpenAPI 3.1, and Model Context Protocol (MCP).

---

## 2. Phase-by-Phase Roadmap

### Phase 0: Foundation, Baseline Contracts, Master Tracking & Tooling Setup
- [x] **0.1 Master Specification & Progress Tracking**: Create `docs/phases/implementation-roadmap.md` and `docs/phases/progress.md`.
- [x] **0.2 Core Environment Verification**: Verify Python 3.12, `uv` packaging, virtual environment, and dependency lockfile integrity.
- [x] **0.3 Baseline Domain Contracts**: Verify configuration validation, exception hierarchies, telemetry, and event bus pub-sub.
- [x] **0.4 MCP Protocol Server Subsystem**: Implement a full Model Context Protocol (MCP) server (`devswarm.mcp`) exposing standard engineering tools via stdio JSON-RPC.
- [x] **0.5 Verification & Acceptance**: Establish 100% test pass rate across baseline test suites.

### Phase 1: LLM Engine & Google Gemini Provider Integration
- Core integration with official `google-genai` SDK.
- Structured output validation with Pydantic schemas.
- Model routing across Gemini tiers (`gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.0-flash-lite`).
- Resilient retry logic with exponential backoff and rate limit handling.
- Deterministic `MockLLMClient` for offline test suites.

### Phase 2: Execution Sandbox & Workspace Worker Subsystem
- Safe filesystem workspace manager with strict path traversal defenses.
- Subprocess execution runner with timeout and buffer limit guards.
- Command safety validator and environment variable sanitizer.
- Unified diff generation and surgical text patcher.

### Phase 3: Agent Framework & Specialized Engineering Roles
- ReAct reasoning loops, context window compaction, and durable memory store.
- Tool registry with schema generation and MCP interoperability.
- Specialized roles: Architect, Planner, Senior Coder, Reviewer, Tester, Security, and Orchestrator.

### Phase 4: Hybrid Autonomy & Checkpoint Governance Engine
- Multi-tier autonomy modes (`autonomous`, `semi_autonomous`, `supervised`, `strict_approval`).
- Dynamic risk assessment engine (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- Checkpoint state machine with async pause-and-resume semantics and feedback channels.

### Phase 5: Swarm Orchestration Engine & Workflow Execution
- Deterministic StateGraph execution engine with conditional routing.
- Feature development workflow with self-healing feedback loop (Coder <-> Tester <-> Reviewer).
- Swarm state / blackboard synchronization.

### Phase 6: Persistence Layer & Data Storage
- Async SQLAlchemy 2.0 with PostgreSQL (`asyncpg`) and SQLite (`aiosqlite`) drivers.
- Relational schema for sessions, executions, checkpoints, events, and artifacts.
- Repository pattern isolating data persistence operations.

### Phase 7: Production API & Real-time WebSocket Streaming
- FastAPI REST endpoints for sessions, checkpoints, workspace files, and telemetry.
- WebSocket `/ws/events` streaming live events to connected clients.
- OpenAPI specification and health endpoints.

### Phase 8: Production CLI & Developer Experience
- Typer CLI with Rich terminal formatting (`devswarm run`, `devswarm serve`, `devswarm status`, `devswarm session`, `devswarm checkpoint`).
- Interactive checkpoint approvals in terminal.

### Phase 9: Production Packaging, Validation & Release Hardening
- Multi-stage Dockerfile and Docker Compose with PostgreSQL 16.
- Comprehensive end-to-end evaluation suite.
- Production deployment guides and operational documentation.
