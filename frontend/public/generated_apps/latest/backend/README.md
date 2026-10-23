# System Full-Stack Backend Service

Autonomously engineered by the **SYNTRA Multi-Agent Engineering Organization**.

## System Overview
- **Framework**: FastAPI (async ASGI)
- **Database**: SQLite (aiosqlite driver) with SQLAlchemy 2.0 ORM
- **Validation**: Pydantic v2 schemas
- **Test Runner**: Pytest + pytest-asyncio + HTTPX ASGITransport
- **Mission Objective**: SYSTEM OBJECTIVE Build a production-ready, multi-tenant SaaS platform: [Insert SaaS Name & Core Value Prop]. # TECH STACK CONSTRAINTS (Strict) - Frontend: [e.g., Next.js 14+ (App Router), TypeScript, Tailwind CSS, shadcn/ui] - Backend: [e.g., FastAPI (Python 3.11+) or Node.js/Express, TypeScript] - Database & ORM: [e.g., PostgreSQL 16, Prisma / SQLAlchemy, Redis for queues] - Auth & Billing: [e.g., Clerk/NextAuth + Stripe Webhook mocks] - Infrastructure: Docker & Docker Compose (must spin up with a single `docker compose up --build`) # AGENT ORCHESTRATION & HANDOFF RULES 1. PM Agent: Output user stories, RBAC matrix, and edge-case constraints before any architecture begins. 2. Architect Agent: Produce `openapi.yaml`, `schema.prisma` (or SQL DDL), and directory tree. Code agents MUST NOT deviate from these contracts. 3. Backend & Frontend Agents: Build strictly against the OpenAPI spec and DB schema. No mocked hardcoded arrays in the UI; all state must persist to the DB. 4. QA/DevOps Agent: Write integration tests (Pytest/Playwright), validate container builds, and reject PRs/merges if tests fail or endpoints return 500s. # CORE FUNCTIONAL MODULES [Insert specific feature requirements from the payloads below] # DEFINITION OF DONE (DoD) - Zero hardcoded secrets (use `.env.example`). - Database migrations and seed script execute automatically on container startup. - Minimum 80% test coverage on core business logic and tenant isolation. - End-to-end user flow works cleanly from signup -> core action -> billing limit enforcement.

## Quickstart

```bash
# 1. Install dependencies
pip install fastapi uvicorn sqlalchemy aiosqlite pydantic pytest pytest-asyncio httpx

# 2. Run the application
uvicorn main:app --reload --port 8000

# 3. Access Swagger OpenAPI Docs
open http://localhost:8000/docs

# 4. Run automated test suite
pytest test_api.py -v
```

## REST API Specification
- `GET /health` — Service health probe
- `GET /api/v1/systems` — Search, filter, and paginate records
- `GET /api/v1/systems/stats` — Real-time telemetry and aggregation metrics
- `GET /api/v1/systems/{id}` — Fetch single record by UUID
- `POST /api/v1/systems` — Create a new validated record
- `PUT /api/v1/systems/{id}` — Update record
- `DELETE /api/v1/systems/{id}` — Delete record
