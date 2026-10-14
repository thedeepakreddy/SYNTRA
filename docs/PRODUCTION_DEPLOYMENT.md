# DevSwarm Production Deployment Guide

## 1. Prerequisites
- Docker Engine >= 24.0
- Docker Compose >= 2.20
- (Optional for Bare Metal / VMs) Python 3.12+ and `uv` package manager

---

## 2. Docker Compose Deployment (Recommended)

1. **Clone and Configure Environment**:
```bash
git clone <repository-url>
cd SYNTRA
cp .env.example .env
```

2. **Set your Gemini API Key in `.env`**:
```bash
GEMINI_API_KEY=AIzaSy...
DEVSWARM_AUTONOMY_MODE=semi_autonomous
```

3. **Launch Containers**:
```bash
docker compose up -d --build
```

4. **Verify Health**:
```bash
curl http://localhost:8000/api/health
```

---

## 3. Database Architecture (PostgreSQL vs SQLite)

DevSwarm uses Async SQLAlchemy 2.0 with driver abstraction:
- **Local Development**: `sqlite+aiosqlite:///./devswarm.db` (zero configuration required, WAL mode enabled).
- **Production Clustered**: `postgresql+asyncpg://devswarm:secret@postgres:5432/devswarm_db` (handles concurrent connections, connection pooling, and multi-worker API clusters).

Set `DEVSWARM_DATABASE_URL` in `.env` or container environment to switch seamlessly.

---

## 4. Security Hardening Checklist

1. **Non-Root Execution**: The production Docker image runs as dedicated UID 1000 `devswarm` user.
2. **Workspace Isolation**: The `WorkspaceManager` verifies canonical paths using `.resolve().relative_to()`. Any attempt to escape the workspace via directory traversal (`../`) raises `SandboxSecurityViolationError`.
3. **Subprocess Sanitization**: The `CommandSafetyValidator` actively scrubs dangerous command patterns and redacts sensitive environment keys (`GEMINI_API_KEY`, `AWS_SECRET_ACCESS_KEY`, etc.) from subprocess environments.
4. **Buffer & Timeout Guards**: Subprocess execution is capped at `DEVSWARM_SANDBOX_TIMEOUT_SECONDS=120` and buffer outputs truncated at `DEVSWARM_SANDBOX_MAX_OUTPUT_BYTES=1048576` (1MB).
