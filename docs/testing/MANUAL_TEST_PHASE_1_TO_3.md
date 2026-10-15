# SYNTRA Manual Verification Guide: Phases 1, 2, and 3

**Synchronized Intelligence for Autonomous Engineering**  
*Manual Verification and Operator Walkthrough for Control Plane, Domain Persistence, and Environment*

---

## 1. Overview & Prerequisites

This runbook guides operators, architects, and developers through end-to-end manual verification of SYNTRA's foundational architecture implemented in **Phase 1 (Environment)**, **Phase 2 (Persistence & Domain)**, and **Phase 3 (Control Plane API & Governance)**.

### Prerequisites
- macOS or Linux terminal
- Python 3.12+ and `uv` package manager installed (`uv --version`)
- SYNTRA repository cloned and active working directory: `/Users/thedeepakreddy/SYNTRA`
- Local development database initialized (`syntra.db`)

### Authentication Schemes in Development Mode
SYNTRA supports two authentication mechanisms for local testing:
1. **Signed OIDC/JWT Bearer Token** (`Authorization: Bearer <JWT>`): Evaluated with signature validation, expiration, issuer, audience, and RBAC role claims.
2. **Local Development Headers** (active when `dev_auth_enabled=True`):
   - `X-Dev-User-Id: <UUID>`
   - `X-Dev-Org-Id: <UUID>`
   - `X-Dev-Role: <developer|admin|owner|viewer>`

---

## 2. Step-by-Step Manual Tests (Tests 1 through 14)

### TEST 1: Start the Backend Server
Start the SYNTRA FastAPI control plane on port 8000 using the `syntra` CLI.

**Terminal Command (Window 1):**
```bash
uv run syntra serve --host 127.0.0.1 --port 8000
```

**Expected Log Output:**
```
INFO:     Started server process [pid]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```
*Leave this terminal window running during all subsequent tests.*

---

### TEST 2: Check API Health & Liveness Probe
Verify that the FastAPI service is active, responsive, and reports operational telemetry.

**Command (Window 2):**
```bash
curl -s -i http://localhost:8000/v1/health
```

**Expected HTTP Status:** `200 OK`  
**Expected Response Body:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "gemini_configured": true,
  "autonomy_mode": "hybrid",
  "telemetry": {
    "total_requests": 1,
    "active_agents": 0,
    "uptime_seconds": 12.4
  }
}
```

---

### TEST 3: Verify Database Connection & Readiness Probe
Verify that the database connectivity probe executes `SELECT 1` and reports healthy persistence.

**Command:**
```bash
curl -s -i http://localhost:8000/health/ready
```

**Expected HTTP Status:** `200 OK`  
**Expected Response Body:**
```json
{
  "status": "ready",
  "timestamp": "2026-10-15T02:00:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "latency_ms": 1.25,
      "details": "local"
    }
  }
}
```

---

### TEST 4: Seed Development Organization & Users
Execute the idempotent seed utility to create standard test organizations, developer users, admin users, and pre-computed HMAC action digests.

**Command:**
```bash
uv run python scripts/seed_dev.py
```

**Expected Output:**
```
Existing Org found: SYNTRA Dev Org (00000000-0000-0000-0000-000000000002)
Existing Developer User found: developer@syntra.local (00000000-0000-0000-0000-000000000001)
Existing Admin User found: admin@syntra.local (00000000-0000-0000-0000-000000000003)
Created Demo Project: SYNTRA Demo Project (00000000-0000-0000-0000-000000000010)
Created Demo Mission: Verify human approval and budget governance (00000000-0000-0000-0000-000000000020)
Created Demo Budget for mission 00000000-0000-0000-0000-000000000020
Created Demo Pending Approval: 00000000-0000-0000-0000-000000000030

============================================================
🔑 Generated Manual Testing Tokens & Seed IDs:
============================================================
ORG ID:          00000000-0000-0000-0000-000000000002
DEV USER ID:     00000000-0000-0000-0000-000000000001
ADMIN USER ID:   00000000-0000-0000-0000-000000000003
DEMO PROJECT ID: 00000000-0000-0000-0000-000000000010
DEMO MISSION ID: 00000000-0000-0000-0000-000000000020
APPROVAL ID:     00000000-0000-0000-0000-000000000030
ACTION DIGEST:   1f422a586ac4b73bc1fbcebb5ff1b49ca2b4ebc5e94be047086f3c83bf0e4b55
------------------------------------------------------------
```

---

### TEST 5: Authenticate via Bearer JWT or Development Headers
Verify that the authentication middleware accepts both dev headers and valid signed JWT tokens.

**Method A: Using Development Headers**
```bash
curl -s -i http://localhost:8000/v1/projects \
  -H "X-Dev-User-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Dev-Org-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Dev-Role: developer"
```

**Method B: Using Bearer JWT**
```bash
DEV_TOKEN=$(uv run python -c "
import jwt, datetime
from syntra.core.config import get_settings
s = get_settings()
print(jwt.encode({
    'sub': '00000000-0000-0000-0000-000000000001',
    'org_id': '00000000-0000-0000-0000-000000000002',
    'role': 'developer',
    'iss': 'https://auth.syntra.io',
    'aud': 'syntra-api',
    'exp': datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1)
}, s.jwt_secret_key, algorithm='HS256'))
")

curl -s -i http://localhost:8000/v1/projects \
  -H "Authorization: Bearer $DEV_TOKEN"
```

**Expected HTTP Status:** `200 OK` (returns list of organization projects).

---

### TEST 6: Create a Project (`POST /v1/projects`)
Create a new project in the organization and verify slug generation and default settings.

**Command:**
```bash
curl -s -i -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -H "X-Dev-User-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Dev-Org-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Dev-Role: developer" \
  -d '{
    "name": "Cloud Microservice Fleet",
    "description": "Distributed microservices platform"
  }'
```

**Expected HTTP Status:** `201 Created`  
**Expected Response Body:**
```json
{
  "id": "<UUID>",
  "org_id": "00000000-0000-0000-0000-000000000002",
  "name": "Cloud Microservice Fleet",
  "slug": "cloud-microservice-fleet",
  "description": "Distributed microservices platform",
  "default_branch": "main",
  "created_at": "<ISO-8601-TIMESTAMP>"
}
```
*Note the returned `id` as `PROJECT_ID`.*

---

### TEST 7: Retrieve Project & List Projects (`GET /v1/projects/{id}`)
Fetch the created project by its unique identifier and list all projects in the organization.

**Command:**
```bash
# Replace with your PROJECT_ID or use demo project ID:
PROJECT_ID="00000000-0000-0000-0000-000000000010"

curl -s -i http://localhost:8000/v1/projects/$PROJECT_ID \
  -H "X-Dev-User-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Dev-Org-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Dev-Role: developer"
```

**Expected HTTP Status:** `200 OK`  
**Expected Response Body:**
```json
{
  "id": "00000000-0000-0000-0000-000000000010",
  "org_id": "00000000-0000-0000-0000-000000000002",
  "name": "SYNTRA Demo Project",
  "slug": "syntra-demo-project",
  "description": "Seeded project for manual verification",
  "default_branch": "main",
  "created_at": "<ISO-8601-TIMESTAMP>"
}
```

---

### TEST 8: Create a Mission (`POST /v1/missions`)
Create an engineering mission under the project with token and cost budget bounds.

**Command:**
```bash
curl -s -i -X POST http://localhost:8000/v1/missions \
  -H "Content-Type: application/json" \
  -H "X-Dev-User-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Dev-Org-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Dev-Role: developer" \
  -d '{
    "project_id": "00000000-0000-0000-0000-000000000010",
    "title": "Build Distributed Rate Limiting",
    "objective": "Implement Redis token bucket rate limiting middleware",
    "autonomy_mode": "hybrid",
    "budget_max_tokens": 500000,
    "budget_max_cost_usd": "25.00",
    "max_concurrency": 4
  }'
```

**Expected HTTP Status:** `201 Created`  
**Expected Response Body:**
```json
{
  "id": "<MISSION_ID>",
  "org_id": "00000000-0000-0000-0000-000000000002",
  "project_id": "00000000-0000-0000-0000-000000000010",
  "title": "Build Distributed Rate Limiting",
  "objective": "Implement Redis token bucket rate limiting middleware",
  "state": "DRAFT",
  "autonomy_mode": "hybrid",
  "version": 1,
  "created_at": "<ISO-8601-TIMESTAMP>",
  "updated_at": "<ISO-8601-TIMESTAMP>"
}
```

---

### TEST 9: Retrieve Mission & Verify Planning Capability (`POST /v1/missions/{id}/plan`)
Fetch the mission details, and then test the planning endpoint. Per architectural contract, Phase 3 returns HTTP 501 with a typed `PlanningCapabilityResponse` scheduling DAG synthesis for Phase 4.

**Step 9A: Retrieve Mission**
```bash
curl -s -i http://localhost:8000/v1/missions/00000000-0000-0000-0000-000000000020 \
  -H "X-Dev-User-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Dev-Org-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Dev-Role: developer"
```
**Expected HTTP Status:** `200 OK`

**Step 9B: Trigger Plan Synthesis Capability**
```bash
curl -s -i -X POST http://localhost:8000/v1/missions/00000000-0000-0000-0000-000000000020/plan \
  -H "X-Dev-User-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Dev-Org-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Dev-Role: developer"
```
**Expected HTTP Status:** `501 Not Implemented`  
**Expected Response Body:**
```json
{
  "mission_id": "00000000-0000-0000-0000-000000000020",
  "project_id": "00000000-0000-0000-0000-000000000010",
  "status": "CAPABILITY_SCHEDULED",
  "phase": "PHASE_3_API_CONTROL_PLANE",
  "target_phase": "PHASE_4_AGENT_EXECUTION_FABRIC",
  "message": "Autonomous multi-agent task planning and DAG synthesis capability begins in Phase 4."
}
```

---

### TEST 10: Test Invalid API Input & RFC 7807 Problem Details
Send an invalid payload (empty project name violating `min_length=1`) and verify the RFC 7807 problem details specification.

**Command:**
```bash
curl -s -i -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -H "X-Dev-User-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Dev-Org-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Dev-Role: developer" \
  -d '{"name": ""}'
```

**Expected HTTP Status:** `422 Unprocessable Entity`  
**Expected Header:** `Content-Type: application/problem+json`  
**Expected Response Body:**
```json
{
  "type": "https://syntra.io/problems/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Request validation failed.",
  "instance": "/v1/projects",
  "invalid_params": [
    {
      "name": "body.name",
      "reason": "String should have at least 1 character"
    }
  ]
}
```

---

### TEST 11: Test Unauthorized Access & RBAC Enforcement
Verify that unauthenticated callers are rejected with 401, and users with insufficient roles are rejected with 403.

**Step 11A: Missing Authentication**
```bash
curl -s -i -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Unauthorized Project"}'
```
**Expected HTTP Status:** `401 Unauthorized`  
**Expected Detail:** `"Authentication required"`

**Step 11B: Insufficient Role Permissions (Viewer attempting mutation)**
```bash
curl -s -i -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -H "X-Dev-User-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Dev-Org-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Dev-Role: viewer" \
  -d '{"name": "Viewer Project"}'
```
**Expected HTTP Status:** `403 Forbidden`  
**Expected Detail:** `"Insufficient role permissions. Requires developer role or above."`

---

### TEST 12: Test Human Approval Governance Workflow
Verify cryptographic human approval resolution using the seeded approval request, enforcing HMAC digest verification and Admin-only RBAC authority.

**Step 12A: Attempting approval as Developer (Must Fail)**
```bash
curl -s -i -X POST http://localhost:8000/v1/approvals/00000000-0000-0000-0000-000000000030/decision \
  -H "Content-Type: application/json" \
  -H "X-Dev-User-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Dev-Org-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Dev-Role: developer" \
  -d '{
    "decision": "APPROVED",
    "action_digest": "1f422a586ac4b73bc1fbcebb5ff1b49ca2b4ebc5e94be047086f3c83bf0e4b55",
    "reason": "Developer trying to self-approve"
  }'
```
**Expected HTTP Status:** `403 Forbidden` (`Requires admin or owner role.`)

**Step 12B: Authorizing checkpoint as Admin with HMAC Action Digest**
```bash
curl -s -i -X POST http://localhost:8000/v1/approvals/00000000-0000-0000-0000-000000000030/decision \
  -H "Content-Type: application/json" \
  -H "X-Dev-User-Id: 00000000-0000-0000-0000-000000000003" \
  -H "X-Dev-Org-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Dev-Role: admin" \
  -d '{
    "decision": "APPROVED",
    "action_digest": "1f422a586ac4b73bc1fbcebb5ff1b49ca2b4ebc5e94be047086f3c83bf0e4b55",
    "reason": "Authorized by Security Lead for Production Deployment"
  }'
```
**Expected HTTP Status:** `200 OK`  
**Expected Response Body:**
```json
{
  "id": "00000000-0000-0000-0000-000000000030",
  "mission_id": "00000000-0000-0000-0000-000000000020",
  "org_id": "00000000-0000-0000-0000-000000000002",
  "action_type": "deployment",
  "target_resource": "production-cluster",
  "mission_version": 1,
  "decision": "APPROVED",
  "action_digest": "1f422a586ac4b73bc1fbcebb5ff1b49ca2b4ebc5e94be047086f3c83bf0e4b55",
  "resolved_at": "<ISO-8601-TIMESTAMP>",
  "resolved_by": "00000000-0000-0000-0000-000000000003",
  "reason": "Authorized by Security Lead for Production Deployment"
}
```

**Step 12C: Replay Prevention (Single-Use Invariant)**
Rerunning the exact same command immediately returns `409 Conflict` (`Approval request is already resolved and cannot be modified.`).

---

### TEST 13: Verify Budget Rules & Financial Usage Ledger
Query the financial ledger and token consumption records bound to a mission.

**Command:**
```bash
curl -s -i http://localhost:8000/v1/missions/00000000-0000-0000-0000-000000000020/usage \
  -H "X-Dev-User-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Dev-Org-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Dev-Role: developer"
```

**Expected HTTP Status:** `200 OK`  
**Expected Response Body:**
```json
{
  "mission_id": "00000000-0000-0000-0000-000000000020",
  "total_tokens": 0,
  "total_cost_usd": "0.0000",
  "records": []
}
```

---

### TEST 14: Inspect Persisted Database State Safely
Directly inspect the authoritative SQLite database to confirm transactional integrity across organizations, users, projects, missions, and resolved approvals.

**Command:**
```bash
sqlite3 syntra.db "
SELECT 'ORGANIZATION:', id, name, slug FROM organizations;
SELECT 'USER:', id, email FROM users;
SELECT 'PROJECT:', id, name, slug FROM projects;
SELECT 'MISSION:', id, state, version, objective FROM missions;
SELECT 'APPROVAL:', id, action_type, decision, reason FROM human_approvals;
SELECT 'BUDGET:', mission_id, max_tokens, max_cost_usd, consumed_tokens FROM budgets;
"
```

**Expected Output:**
```
ORGANIZATION:|00000000000000000000000000000002|SYNTRA Dev Org|syntra-dev-org
USER:|00000000000000000000000000000001|developer@syntra.local
USER:|00000000000000000000000000000003|admin@syntra.local
PROJECT:|00000000000000000000000000000010|SYNTRA Demo Project|syntra-demo-project
MISSION:|00000000000000000000000000000020|DRAFT|1|Verify human approval and budget governance
APPROVAL:|00000000000000000000000000000030|deployment|APPROVED|Authorized by Security Lead for Production Deployment
BUDGET:|00000000000000000000000000000020|100000|10|0
```

---

## 3. Verification Completion & Next Actions

Once all 14 tests have been performed and the results match the documented contracts:
1. Verify automated test status via `uv run pytest`.
2. Inspect the retrospective verification report in `docs/testing/PHASE_1_TO_3_VERIFICATION_REPORT.md`.
3. Provide confirmation in chat to authorize initiating **Phase 4: Agent Execution Fabric and Multi-Agent DAG Orchestration**.
