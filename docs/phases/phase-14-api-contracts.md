# SYNTRA Phase 14 API Contract Specification
**Control Center & End-to-End Product Integration**

**Date**: 2026-10-20  
**Status**: `APPROVED_SPECIFICATION`  
**Base Path**: `/v1`  
**Security & RBAC**: Strict multi-tenancy enforced on every request via `get_current_user` (`user.org_id`). Roles: `VIEWER`, `DEVELOPER`, `ADMIN`, `OWNER`.

---

## 1. Authentication & Multi-Tenancy

Every API request requires one of:
1. `Authorization: Bearer <JWT>` containing verified tenant claims (`org_id`, `sub`, `role`).
2. Development headers (only permitted when `environment == "development"`):
   - `X-Dev-User-Id`: UUID string
   - `X-Dev-Org-Id`: UUID string
   - `X-Dev-Role`: `viewer` | `developer` | `admin` | `owner`
   - `X-Dev-Email`: User email address

---

## 2. API Endpoints Matrix

### 2.1 Overview & System Diagnostics
- **`GET /v1/system/overview`**
  - **Min Role**: `VIEWER`
  - **Description**: Returns consolidated statistics for the Control Center Overview dashboard.
  - **Response (200 OK)**:
    ```json
    {
      "org_id": "00000000-0000-0000-0000-000000000002",
      "projects_count": 3,
      "missions_count": 8,
      "missions_by_state": {
        "DRAFT": 1,
        "RUNNING": 2,
        "AWAITING_APPROVAL": 1,
        "COMPLETED": 3,
        "FAILED": 1
      },
      "pending_approvals_count": 1,
      "active_agents_count": 10,
      "total_tokens_consumed": 18450,
      "total_cost_usd": 0.0452,
      "system_health": "HEALTHY",
      "timestamp": "2026-10-20T17:00:00Z"
    }
    ```

### 2.2 Projects Management
- **`POST /v1/projects`**: Create a new project. Min Role: `DEVELOPER`.
- **`GET /v1/projects`**: List all projects for tenant. Min Role: `VIEWER`.
- **`GET /v1/projects/{project_id}`**: Get project details. Min Role: `VIEWER`.

### 2.3 Missions & Tasks
- **`POST /v1/missions`**: Create a new mission with budget limits. Min Role: `DEVELOPER`.
- **`GET /v1/missions`**: List missions for tenant (with optional `project_id`, `state` filters). Min Role: `VIEWER`.
- **`GET /v1/missions/{mission_id}`**: Get mission details, version, and autonomy mode. Min Role: `VIEWER`.
- **`GET /v1/missions/{mission_id}/plan`**: Get validated task DAG. Min Role: `VIEWER`.
- **`GET /v1/missions/{mission_id}/tasks`**: List tasks with attempts and dependencies. Min Role: `VIEWER`.
- **`GET /v1/missions/{mission_id}/events`**: List mission state transition events. Min Role: `VIEWER`.
- **`GET /v1/missions/{mission_id}/artifacts`**: List produced artifacts (diffs, specs, logs). Min Role: `VIEWER`.
- **`GET /v1/missions/{mission_id}/usage`**: Get token and cost usage summary. Min Role: `VIEWER`.
- **`GET /v1/tasks/{task_id}`**: Get task details and dependencies. Min Role: `VIEWER`.

### 2.4 Approvals & Governance Inbox
- **`GET /v1/approvals`**: List approval requests for tenant (optional `decision` filter: `PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`). Min Role: `VIEWER`.
- **`GET /v1/approvals/{approval_id}`**: Get single approval details with action digest. Min Role: `VIEWER`.
- **`POST /v1/approvals/{approval_id}/decision`**: Submit human approval decision (`APPROVE` or `REJECT`) with cryptographic digest match and single-use idempotency. Min Role: `ADMIN`.

### 2.5 Agents & Specialist Roster
- **`GET /v1/agents`**: List the 10 specialized engineering personas from `AGENTS.md` (Product Manager, Software Architect, Engineering Manager, Backend Engineer, Frontend Engineer, QA Engineer, DevOps Engineer, Security Reviewer, Code Reviewer, Debugging Specialist) with mandates, allowed tools, model tiers, and operational status. Min Role: `VIEWER`.

### 2.6 Model Routing & Policy Configuration
- **`GET /v1/models`**: List registered models from `config/models.yaml` (ID, tier, status, context window, pricing rates, capabilities). Min Role: `VIEWER`.
- **`GET /v1/models/routing`**: Get current persona-to-tier mappings and default models. Min Role: `VIEWER`.
- **`POST /v1/models/routing/simulate`**: Simulate model routing decision for given role and task complexity, returning resolved model, tier, and policy rationale. Min Role: `VIEWER`.

### 2.7 Benchmarks & Quality Explorer
- **`GET /v1/benchmarks`**: List all benchmark evaluation runs from `benchmarks/results/` with status, duration, and metrics. Min Role: `VIEWER`.
- **`GET /v1/benchmarks/{run_id}`**: Get detailed benchmark run artifacts (`manifest.json`, `summary.json`, `verification.json`). Min Role: `VIEWER`.

### 2.8 Audit History
- **`GET /v1/audit`**: List recent cryptographic audit events with server-side secret scrubbing. Min Role: `VIEWER`.

---

## 3. Error Handling Contract (RFC 7807)

All endpoints adhere to RFC 7807 Problem Details:
```json
{
  "type": "https://syntra.io/errors/unauthorized-approval",
  "title": "Unauthorized Approval Decision",
  "status": 403,
  "detail": "User with role 'viewer' is not authorized to resolve governance checkpoints. Requires admin or owner role.",
  "instance": "/v1/approvals/c2b535d8-c70a-4fa0-8ef5-9a849206b0b3/decision",
  "code": "UNAUTHORIZED_APPROVAL",
  "correlation_id": "7f9a1b2c-3d4e-5f6a-7b8c-9d0e1f2a3b4c"
}
```
