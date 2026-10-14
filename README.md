# SYNTRA

**Synchronized Intelligence for Autonomous Engineering**

> *One Vision. Multiple AI Agents. Autonomous Engineering.*

SYNTRA coordinates teams of specialized AI agents powered by Google Gemini (`google-genai` SDK) to autonomously architect, plan, write, review, test, and release production-quality code under a robust **hybrid autonomy** model with isolated execution sandboxes.

---

## Core Capabilities
- **Synchronized Multi-Agent Organization**: 10 specialized agent roles collaborating via explicit contracts and verified handoffs (Product Manager, Software Architect, Engineering Manager, Backend Engineer, Frontend Engineer, QA Engineer, DevOps Engineer, Security Reviewer, Code Reviewer, Debugging Specialist).
- **Primary Model Provider**: Google Gemini via the modern official `google-genai` Python SDK.
- **Hybrid Autonomy**: Tiered autonomy levels with human-in-the-loop checkpoint gates (Approve, Reject with corrective guidance, Modify).
- **Isolated Execution Sandboxes**: Safe process execution plane (`SandboxProvider`) with Git worktree isolation, environment scrubbing, path traversal guards, and timeout limits.
- **Model Context Protocol (MCP)**: Native MCP server (`syntra`) and client gateway supporting stdio and HTTP SSE transports.
- **Durable Workflow Orchestration**: LangGraph state machines with PostgreSQL checkpointing.
- **Headless-First Architecture**: Completely operable without a graphical frontend via FastAPI REST/WebSocket endpoints and the `syntra` CLI.

---

## Monorepo Layout

```
syntra/
|-- apps/                      # Application entry points
|   |-- api/                   # FastAPI REST & WebSocket control plane
|   |-- orchestrator/          # LangGraph mission coordinator daemon
|   |-- scheduler/             # Task DAG scheduler and lease manager
|   |-- worker-controller/     # Worker supervision daemon
|   |-- mcp-server/            # SYNTRA MCP server daemon
|
|-- packages/                  # Modular internal packages
|   |-- domain/                # Pure business logic and aggregates (zero framework dependencies)
|   |-- contracts/             # Pydantic v2 schemas and RPC contracts
|   |-- persistence/           # SQLAlchemy 2.x models, migrations, and repositories
|   |-- agents/                # Agent personas, prompt templates, and ReAct loops
|   |-- model-runtime/         # Google Gen AI SDK adapter, router, cost ledger
|   |-- mcp-gateway/           # MCP client manager and capability gateway
|   |-- tool-registry/         # Tool catalog and execution bindings
|   |-- skill-registry/        # Skill manifest loader and progressive disclosure
|   |-- sandbox/               # SandboxProvider and Git worktree manager
|   |-- memory/                # Execution, project, and organizational memory
|   |-- evaluation/            # Verification service and quality gates
|   |-- security/              # Secrets scrubber and cryptographic approval digests
|   |-- telemetry/             # OpenTelemetry metrics and structured logging
|
|-- skills/                    # 16 Specialized skill packages (manifest.yaml + SKILL.md)
|-- scripts/                   # Operational utilities (bootstrap.sh, doctor.sh, smoke-test.sh)
|-- tests/                     # Unit, integration, contract, security, and e2e tests
|-- compose.yaml               # PostgreSQL 16, Redis 7, MinIO S3, and Backend
|-- Makefile                   # Standardized development targets
```

---

## Quick Start

### 1. Bootstrap the Environment
```bash
# Clone the repository and run bootstrap
make bootstrap
# Or directly:
bash scripts/bootstrap.sh
```

### 2. Verify System Health
```bash
make doctor
# Or directly:
bash scripts/doctor.sh
```

### 3. Start Containerized Infrastructure (Optional)
```bash
# Starts PostgreSQL 16, Redis 7, and MinIO S3
make compose-up
```

### 4. Run Tests
```bash
make test
# With coverage report:
make test-cov
```

### 5. Launch the Backend API
```bash
make serve
# API interactive docs available at http://localhost:8000/docs
```

---

## Verification & Health Probes
- **Liveness Probe**: `GET /health` or `GET /api/health`
- **Readiness Probe**: `GET /health/ready` or `GET /api/health/ready` (checks Database, Redis, MinIO, and Sandbox writeability)
- **Telemetry & Metrics**: `GET /telemetry` or `GET /api/telemetry`

---

## Architecture Documentation
- [`docs/architecture/system-overview.md`](docs/architecture/system-overview.md): 7-Layer System Architecture
- [`docs/architecture/module-boundaries.md`](docs/architecture/module-boundaries.md): Monorepo Boundaries & Invariants
- [`docs/architecture/database-design.md`](docs/architecture/database-design.md): PostgreSQL Schema & ERD
- [`docs/architecture/workflow-design.md`](docs/architecture/workflow-design.md): LangGraph Mission & Task Graphs
- [`docs/architecture/mcp-design.md`](docs/architecture/mcp-design.md): MCP Server & Client Gateway
- [`docs/architecture/agent-design.md`](docs/architecture/agent-design.md): 10 Agent Personas & Invocations
- [`docs/architecture/security-design.md`](docs/architecture/security-design.md): Threat Model & Defense-in-Depth
- [`docs/phases/implementation-roadmap.md`](docs/phases/implementation-roadmap.md): Master 14-Phase Implementation Roadmap
