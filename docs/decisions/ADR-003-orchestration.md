# ADR-003: LangGraph Workflow State Graphs with PostgreSQL Checkpointing

- **Status**: ACCEPTED
- **Date**: 2026-10-15
- **Deciders**: Principal Software Architect, LangGraph Engineer

---

## 1. Context & Problem Statement
Autonomous multi-agent engineering workflows are not linear chains; they are cyclic graphs involving planning, approval pauses, iterative development, QA verification, failure detection, debugging, and replanning. We need a workflow engine that natively supports cyclic graphs, durable state persistence across process restarts, and clean human-in-the-loop interrupts.

---

## 2. Decision Drivers
- **Cyclic Execution**: Support for loops (e.g. Code $\to$ Test $\to$ Failure $\to$ Debug $\to$ Code).
- **Durable Checkpointing**: Ability to pause execution indefinitely and resume without loss of working state.
- **Human Interrupts**: Native mechanism to suspend graph execution for approval decisions.
- **Clear Separation**: Distinguish graph execution snapshots from authoritative business records in PostgreSQL.

---

## 3. Considered Options
1. **Option A: Custom While-Loop Engine**: Simple to write initially, but lacks durable state machines, resumption, and visualization.
2. **Option B: Temporal / Cadence**: Powerful distributed workflow engine, but adds heavy operational complexity (external cluster, Java/Go dependencies).
3. **Option C: LangGraph with PostgreSQL Checkpointing**: Native Python, designed specifically for cyclic multi-agent graphs, supports `interrupt()`, and checkpoints directly into PostgreSQL.

---

## 4. Decision Outcome
**Chosen Option**: **Option C: LangGraph with PostgreSQL Checkpointing**.

### Key Rules:
- The macro workflow is modeled as a 12-state Mission State Graph.
- Human approval pauses use LangGraph's native `interrupt()` function.
- Graph checkpoints stored in PostgreSQL checkpoint tables are treated as execution caches.
- Authoritative business state remains strictly in PostgreSQL domain tables (`missions`, `tasks`).

### Tradeoffs:
- **Pros**: Cyclic flow support, built-in human interrupt semantics, native Python async support.
- **Cons**: Care must be taken to prevent desynchronization between graph checkpoints and authoritative database records.
