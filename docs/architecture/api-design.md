# DevSwarm API Architecture Specification

## 1. Overview
The DevSwarm Control Plane exposes a versioned, secure REST API under `/v1/...` and real-time streaming over WebSockets and Server-Sent Events (SSE). The system is designed to be 100% operable headlessly via API and CLI without requiring any graphical frontend.

---

## 2. API Endpoint Matrix

### 2.1 Project & Mission Management
| Method | Path | Description | Idempotent |
|---|---|---|---|
| `POST` | `/v1/projects` | Register a new software engineering project | Yes (with key) |
| `GET` | `/v1/projects/{id}` | Retrieve project metadata and repositories | Yes |
| `POST` | `/v1/missions` | Create a new mission from an objective string | Yes (with key) |
| `GET` | `/v1/missions/{id}` | Fetch current mission state and lifecycle stage | Yes |
| `POST` | `/v1/missions/{id}/plan` | Trigger autonomous planning (PM + Architect + EM) | No |
| `GET` | `/v1/missions/{id}/plan` | Inspect the generated PRD, architecture, and task DAG | Yes |
| `POST` | `/v1/missions/{id}/start` | Launch scheduled execution of the approved plan | No |
| `POST` | `/v1/missions/{id}/pause` | Pause active execution gracefully | Yes |
| `POST` | `/v1/missions/{id}/resume` | Resume paused execution | Yes |
| `POST` | `/v1/missions/{id}/cancel` | Cancel mission, revoking leases and killing workers | Yes |

### 2.2 Task Execution & Scheduling
| Method | Path | Description | Idempotent |
|---|---|---|---|
| `GET` | `/v1/missions/{id}/tasks` | List tasks in the DAG with dependency links | Yes |
| `GET` | `/v1/tasks/{id}` | Retrieve task status, assigned role, and input artifacts | Yes |
| `GET` | `/v1/tasks/{id}/attempts` | List execution attempts and worker logs | Yes |

### 2.3 Artifacts & Event Streaming
| Method | Path | Description | Idempotent |
|---|---|---|---|
| `GET` | `/v1/missions/{id}/artifacts` | List produced artifacts (diffs, reports, plans) | Yes |
| `GET` | `/v1/missions/{id}/events` | Query audit log events with cursor pagination | Yes |
| `GET` | `/v1/missions/{id}/events/stream`| WebSocket / SSE endpoint for live event streaming | Yes |

### 2.4 Governance & Financial Ledger
| Method | Path | Description | Idempotent |
|---|---|---|---|
| `POST` | `/v1/approvals/{id}/decision` | Approve, reject (with feedback), or modify checkpoint | Yes |
| `GET` | `/v1/missions/{id}/usage` | Fetch real-time token count and USD cost ledger | Yes |

### 2.5 Catalog & Introspection
| Method | Path | Description | Idempotent |
|---|---|---|---|
| `GET` | `/v1/skills` | List registered skills, versions, and manifests | Yes |
| `GET` | `/v1/tools` | List registered tools and JSON schemas | Yes |
| `GET` | `/v1/agents` | List available agent personas and capabilities | Yes |
| `GET` | `/v1/capabilities` | List platform capability permission grants | Yes |
| `GET` | `/v1/health` | Liveness health check | Yes |
| `GET` | `/v1/ready` | Readiness check (validates DB and Redis connections)| Yes |

---

## 3. Protocol & Contract Standards
1. **Pydantic v2 Contracts**: Every request body and response payload is strictly validated using Pydantic models.
2. **Idempotency**: Mutating requests accept an `Idempotency-Key` HTTP header. Repeated requests return cached responses without re-executing.
3. **Cursor-based Pagination**: Large collections (`events`, `tasks`, `artifacts`) use deterministic cursor pagination (`?limit=50&cursor=...`).
4. **Correlation IDs**: Every request carries an `X-Correlation-ID` header propagated to logs, traces, and worker jobs.
