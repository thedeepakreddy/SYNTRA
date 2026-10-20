# SYNTRA Phase 14: Control Center Feature Inventory

**SYNTRA: Synchronized Intelligence for Autonomous Engineering**  
*Document Version: 1.0.0 | Date: October 20, 2026*  
*Classification: Functional Specification & Feature Inventory*

---

## 1. Executive Summary

Phase 14 delivers a production-grade, highly responsive web application in `frontend/` backed by FastAPI REST endpoints in `src/syntra/api/`. The system adheres strictly to the core operating principle: **No fake controls, no hidden features, no fabricated agent activity, no silent failures, and no dead buttons.** Every control presented in the UI communicates with active backend endpoints, responds to user actions, and displays unambiguous feedback or error states.

---

## 2. The 13 Navigation Destinations

| # | Destination | Route Path | Primary Components | Backend Endpoints Wired | Functional Capabilities |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Overview** | `/overview` | `OverviewPage.tsx`, `StatusBadge.tsx` | `GET /v1/system/overview` | High-level KPI summary cards (Projects, Missions, Pending Approvals, Agents), token consumption ledger, USD spend, system health status, quick access action cards. |
| **2** | **Projects** | `/projects` | `ProjectsPage.tsx`, `Modal.tsx` | `GET /v1/projects`, `POST /v1/projects` | Target repository catalog, search/filter by name or slug, registration modal with input validation (name, slug, description, branch), tenant-scoped isolation. |
| **3** | **Missions & Tasks** | `/missions` | `MissionsPage.tsx`, `Modal.tsx` | `GET /v1/missions`, `POST /v1/missions`, `GET /v1/missions/{id}/tasks`, `GET /v1/missions/{id}/events`, `GET /v1/missions/{id}/usage` | Mission orchestration dashboard, status filter tabs (PENDING, PLANNING, EXECUTING, AWAITING_APPROVAL, COMPLETED, FAILED), mission launcher modal with autonomy mode selection, task DAG inspector, chronological event timeline, per-mission financial ledger. |
| **4** | **Agents & Teams** | `/agents` | `AgentsPage.tsx` | `GET /v1/agents` | Authoritative display of the 10 canonical engineering personas (`AGENTS.md`), mandate descriptions, allowed tools tags, forbidden actions alerts, primary inputs and authoritative outputs, anti-collusion governance rules. |
| **5** | **Approvals** | `/approvals` | `ApprovalsPage.tsx`, `Modal.tsx` | `GET /v1/approvals`, `GET /v1/approvals/{id}`, `POST /v1/approvals/{id}/respond` | Cryptographic human delivery gate, filtering by decision status (PENDING, APPROVED, REJECTED), inspection of target resources and HMAC-SHA256 signature digests, interactive review modal to authorize or reject tickets with responder identity and audit justification. |
| **6** | **Model Routing** | `/model-routing` | `ModelRoutingPage.tsx`, `StatusBadge.tsx` | `GET /v1/models`, `GET /v1/models/routing`, `POST /v1/models/routing/simulate` | Model catalog with context window sizes and pricing, role-to-tier default policy matrix, live interactive routing decision simulator evaluating persona mandates, task classification, and explicit model overrides. |
| **7** | **Usage & Budgets** | `/usage-budgets` | `UsageBudgetsPage.tsx` | `GET /v1/system/overview`, `GET /v1/missions`, `GET /v1/missions/{id}/usage` | Aggregate token consumption (prompt vs completion), USD financial spend, hard ceiling budget governance status, per-mission selector with granular model invocation table (input tokens, output tokens, total tokens, cost USD, timestamp). |
| **8** | **Runs & Logs** | `/runs-logs` | `RunsLogsPage.tsx` | `GET /v1/audit`, `GET /v1/missions` | Real-time execution log feed, multi-criteria filtering by event type, mission ID, and free text, expandable structured JSON payload viewer with credential scrubbing confirmation. |
| **9** | **Artifacts & Results** | `/artifacts` | `ArtifactsPage.tsx` | `GET /v1/missions`, `GET /v1/missions/{id}/artifacts` | Catalog of immutable software artifacts (Unified Diffs, Architecture Specs, PRDs, Verification Runs), storage path, file size, content SHA-256 hash display with one-click clipboard copy. |
| **10** | **Benchmarks & Quality** | `/benchmarks` | `BenchmarksPage.tsx`, `StatusBadge.tsx` | `GET /v1/benchmarks`, `GET /v1/benchmarks/{run_id}` | Quantitative evaluation run history, mode indicators (Mode A Hermetic Deterministic, Mode B Persistence, Mode D Fault Recovery), detailed view of the 6 canonical evaluation metrics against hard thresholds, run manifest and verification integrity. |
| **11** | **Audit History** | `/audit-history` | `AuditHistoryPage.tsx` | `GET /v1/audit` | Authoritative append-only audit trail, tamper-evident hash chaining indicators, event type filtering, mission/task correlation, expandable payload viewer. |
| **12** | **System Health** | `/system-health` | `SystemHealthPage.tsx`, `StatusBadge.tsx` | `GET /v1/system/overview` | Platform diagnostic health across core architectural boundaries (Persistence Engine, Worker Sandbox Isolation, OTel Telemetry, Human Delivery Gate, Model Routing, Audit Outbox), live latency probe button measuring round-trip API time. |
| **13** | **Settings & Config** | `/settings` | `SettingsPage.tsx` | Local Context & API Client Headers | Operator identity configuration (User UUID, Org UUID, Email), live Role Switcher (`admin`, `developer`, `viewer`) for dynamic RBAC permission testing, display of security redactor, isolation sandboxes, and OTel exporter settings. |

---

## 3. Persistent Layout & Navigation Controls

1. **Brand & Version Indicator**: Displays SYNTRA brand identity with Phase 14 indicator.
2. **Sidebar Navigation**:
   - 13 distinct labeled items with dedicated Lucide React icons.
   - Pending Approvals badge dynamically reflects active ticket count.
   - Accessible collapse/expand toggle (`isCollapsed`) preserving full keyboard navigability.
   - Direct `data-testid` attributes on all navigation targets for automated testing.
3. **TopBar**:
   - Contextual Route Title and System Health indicator.
   - Environment Badge (`DEVELOPMENT` / `STAGING` / `PRODUCTION`).
   - Active Tenant / Org ID display.
   - Global Role Switcher: Dropdown allowing seamless switching between `admin`, `developer`, and `viewer` roles, automatically updating API client request headers.
   - Data Refresh Button: Triggers immediate re-fetch of system data.

---

## 4. Verification & Testing

- **Frontend Tests**: 12 unit and integration tests across 5 test suites (`vitest` + `@testing-library/react`), verifying navigation, approval review modals, model routing simulation, and API client auth header injection.
- **Production Build**: Built using Vite 6 + TypeScript 5.6 with zero warnings or errors.
- **Backend Tests**: 8 dedicated API route tests in `tests/test_phase14_api.py` verifying response contracts, idempotency, and multi-tenancy.
