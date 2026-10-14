# ADR-001: Backend-First Modular Monolith with Isolated Execution Workers

- **Status**: ACCEPTED
- **Date**: 2026-10-15
- **Deciders**: Principal Software Architect, Core Engineering Team

---

## 1. Context & Problem Statement
SYNTRA coordinates multiple specialized AI agents executing complex engineering workflows involving requirements analysis, architectural planning, task scheduling, coding, testing, and verification. We must choose an architectural deployment model that balances maintainability, testability, distributed worker execution, operational simplicity, and security.

Microservices meshes introduce distributed transaction coordination overhead, network latency, and operational complexity. Pure monolithic architectures risk host compromise if untrusted agent code runs inside the main server process.

---

## 2. Decision Drivers
- **Operational Simplicity**: Minimize operational complexity during initial development and deployment.
- **Security & Blast Radius**: Untrusted, agent-generated code must never execute in the control plane process.
- **Transactional Consistency**: Relational database operations (missions, tasks, leases, audits) must maintain strict ACID guarantees.
- **Performance**: Low-latency inter-module communication within the control plane.

---

## 3. Considered Options
1. **Option A: Distributed Microservices Mesh** (Separate services for API, Orchestrator, Scheduler, Agents, Memory).
2. **Option B: Pure Monolith** (All services and code execution inside a single Python process).
3. **Option C: Modular Monolith with Isolated Execution Workers** (Control plane as a cohesive modular monolith in FastAPI/LangGraph; code execution strictly delegated to ephemeral worker sandboxes).

---

## 4. Decision Outcome
**Chosen Option**: **Option C: Modular Monolith with Isolated Execution Workers**.

### Key Architectural Rules:
- The Control Plane (API, Orchestrator, Scheduler, Model Adapter, Tool Registry, Persistence) is deployed as a modular monolith.
- Clean module boundaries are enforced using Python packages (`domain/`, `contracts/`, `persistence/`, `agents/`, etc.).
- Execution Workers operate in separate, isolated processes managed by `SandboxProvider` with non-root privileges and Git worktree isolation.
- Domain logic must never import FastAPI or LangGraph.

### Tradeoffs:
- **Pros**:
  - High performance, in-memory function calls for control plane operations.
  - Zero dual-write inconsistencies across internal boundaries.
  - Complete process and filesystem isolation for untrusted agent-executed code.
  - Simple local development via Docker Compose or single binary CLI.
- **Cons**:
  - Requires discipline to prevent leaky abstractions between internal modules.
  - Worker supervision requires dedicated lease management and heartbeat mechanisms.
