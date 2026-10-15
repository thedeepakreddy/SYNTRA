# Phase 8: Task Scheduling & Parallel Agent Coordination Manual Testing Guide

**Project**: SYNTRA (Synchronized Intelligence for Autonomous Engineering)  
**Document**: Phase 8 Manual Verification & Operator Runbook  
**Target Subsystems**: `src/syntra/scheduling`, `src/syntra/persistence`, `src/syntra/orchestration`  
**Execution Environment**: Python 3.12+ via `uv run python` with Live PostgreSQL 16 & Redis 8

---

## 1. Overview & Architecture Reference

This runbook provides operators, engineers, and quality assurance auditors with verified, executable scripts to test and validate SYNTRA's Task Scheduling & Parallel Agent Coordination subsystem (Phase 8).

Key architectural capabilities verified:
1. **DAG Readiness Evaluation**: 8-point precondition assessment (mission status, plan version, completed dependencies, artifact manifests, recognized agent roles, skill availability, budget headroom).
2. **Deterministic Priority Ranking**: Multi-factor topological ordering based on explicit priority, downstream dependents count, and resource reservations.
3. **Atomic Task Claiming**: Live PostgreSQL row-level locks using `SELECT ... FOR UPDATE SKIP LOCKED` guaranteeing mutual exclusivity and zero duplicate assignments under high concurrency.
4. **Worker Leases & Fencing Tokens**: Monotonically increasing fencing tokens preventing split-brain execution and rejecting stale/superseded worker turns.
5. **Redis Streams Task Dispatch**: Reliable event notification via `XADD`, `XREADGROUP`, `XACK`, and `XAUTOCLAIM` with Redis consumer groups (`syntra_workers`).
6. **Transactional Outbox Relay**: At-least-once outbox staging in PostgreSQL with background forwarder relaying events to Redis Streams.
7. **Reconciliation & Failure Recovery**: Automatic detection of expired worker leases, retry budget management, and cascading `BLOCKED` status propagation to downstream dependents upon permanent upstream failure.

All scenarios correspond to standalone executable scripts located in:
```
scripts/manual_tests/phase_08/
```

---

## 2. Prerequisites & Environment Setup

Verify background infrastructure services are running locally on loopback interfaces:

```bash
# Verify PostgreSQL 16
pg_isready -h localhost -p 5432

# Verify Redis 8
redis-cli -h localhost -p 6379 ping
```

Ensure Python dependencies are synced:
```bash
uv sync
```

Run the Phase 8 automated test suite to confirm baseline functionality:
```bash
uv run pytest tests/test_scheduling_phase8.py -v
```

---

## 3. Executable Manual Scenarios

### Scenario 1: Task DAG Creation and Topological Ordering
- **Script**: `scripts/manual_tests/phase_08/01_create_task_dag.py`
- **Objective**: Construct a multi-tier engineering task graph (Architecture -> DB Models -> REST API -> Acceptance Tests) and verify deterministic topological ordering using `TaskDAGEngine`.
- **Run Command**:
```bash
uv run python scripts/manual_tests/phase_08/01_create_task_dag.py
```
- **Verification Invariants**:
  - Topological sort produces cycle-free ordering where each dependency appears before its downstream dependents.

---

### Scenario 2: Dependency Validation & Cyclic Graph Rejection
- **Script**: `scripts/manual_tests/phase_08/02_validate_dependencies.py`
- **Objective**: Validate structural graph invariants and demonstrate rejection of invalid DAGs.
- **Run Command**:
```bash
uv run python scripts/manual_tests/phase_08/02_validate_dependencies.py
```
- **Verification Invariants**:
  - Direct and indirect circular dependencies (`A -> B -> C -> A`) raise `DAGValidationError`.
  - Self-dependencies (`A -> A`) raise `DAGValidationError`.
  - Dependencies referencing non-existent tasks raise `DAGValidationError`.

---

### Scenario 3: Parallel Execution of Independent Tasks
- **Script**: `scripts/manual_tests/phase_08/03_parallel_task_execution.py`
- **Objective**: Create 3 independent tasks without dependencies and verify parallel evaluation, dispatch, and completion.
- **Run Command**:
```bash
uv run python scripts/manual_tests/phase_08/03_parallel_task_execution.py
```
- **Verification Invariants**:
  - `TaskScheduler.schedule_ready_tasks` dispatches all 3 tasks in parallel in a single dispatch cycle.
  - Worker executes tasks concurrently via `asyncio.gather`.
  - All tasks transition to `COMPLETED` in the database.

---

### Scenario 4: Concurrency Limit Enforcement
- **Script**: `scripts/manual_tests/phase_08/04_concurrency_limits.py`
- **Objective**: Enforce per-mission concurrency bounds (`max_concurrency=2`) when 5 tasks are ready for execution.
- **Run Command**:
```bash
uv run python scripts/manual_tests/phase_08/04_concurrency_limits.py
```
- **Verification Invariants**:
  - Cycle 1 dispatches exactly 2 tasks.
  - Saturated scheduling re-evaluation dispatches 0 tasks.
  - Completing 1 task immediately frees a slot, allowing exactly 1 task to be dispatched on the next cycle.

---

### Scenario 5: Duplicate Claim Prevention with PostgreSQL Row Locks
- **Script**: `scripts/manual_tests/phase_08/05_duplicate_claim_prevention.py`
- **Objective**: Verify atomic task claiming against live PostgreSQL using `SELECT ... FOR UPDATE SKIP LOCKED`.
- **Run Command**:
```bash
uv run python scripts/manual_tests/phase_08/05_duplicate_claim_prevention.py
```
- **Verification Invariants**:
  - Two concurrent workers simultaneously claiming tasks receive disjoint, mutually exclusive tasks.
  - No task is ever claimed more than once.

---

### Scenario 6: Lease Expiration Detection & Automatic Re-queuing
- **Script**: `scripts/manual_tests/phase_08/06_lease_expiration.py`
- **Objective**: Verify `SchedulerReconciler` detects expired worker leases and safely re-queues tasks.
- **Run Command**:
```bash
uv run python scripts/manual_tests/phase_08/06_lease_expiration.py
```
- **Verification Invariants**:
  - Stale attempt transitions to `TIMED_OUT`.
  - Task resets to `READY` state.
  - Expired worker lease is cleared from PostgreSQL.

---

### Scenario 7: Worker Failure Recovery & Cascading Failure Propagation
- **Script**: `scripts/manual_tests/phase_08/07_worker_failure_recovery.py`
- **Objective**: Verify bounded retry management and cascading failure propagation to downstream dependents.
- **Run Command**:
```bash
uv run python scripts/manual_tests/phase_08/07_worker_failure_recovery.py
```
- **Verification Invariants**:
  - Attempt 1 failure re-queues task to `READY` with incremented attempt count.
  - Attempt 2 failure exhausts `max_attempts=2` and transitions task to `FAILED`.
  - Downstream dependent task (`T2`) automatically cascades to `BLOCKED`.

---

### Scenario 8: Budget Exhaustion & Headroom Invariant Enforcement
- **Script**: `scripts/manual_tests/phase_08/08_budget_exhaustion.py`
- **Objective**: Verify budget reservation limits prevent scheduling when headroom is insufficient.
- **Run Command**:
```bash
uv run python scripts/manual_tests/phase_08/08_budget_exhaustion.py
```
- **Verification Invariants**:
  - `TaskDAGEngine.evaluate_task_readiness` marks task not ready with explanation `Insufficient token budget headroom`.
  - Scheduler holds task in `PENDING` state.
  - Manual over-allocation raises `BudgetExceededError`.

---

### Scenario 9: Mission Cancellation & In-Flight Task Abort
- **Script**: `scripts/manual_tests/phase_08/09_mission_cancellation.py`
- **Objective**: Verify administrative mission cancellation aborts active tasks and releases worker leases.
- **Run Command**:
```bash
uv run python scripts/manual_tests/phase_08/09_mission_cancellation.py
```
- **Verification Invariants**:
  - Active/in-flight tasks transition to `CANCELLED`.
  - Active worker leases are deleted.
  - Previously completed tasks remain immutable in `COMPLETED` state.

---

### Scenario 10: Transactional Outbox Relay & Redis Event Stream Verification
- **Script**: `scripts/manual_tests/phase_08/10_scheduler_event_history.py`
- **Objective**: Validate the full transactional outbox relay loop with Redis Streams.
- **Run Command**:
```bash
uv run python scripts/manual_tests/phase_08/10_scheduler_event_history.py
```
- **Verification Invariants**:
  - `TASK_DISPATCHED` is written to PostgreSQL transactional outbox.
  - `OutboxRelay` publishes notification to Redis Streams (`XADD`).
  - Worker consumer group reads message (`XREADGROUP`) and acknowledges (`XACK`).
  - Worker completion writes `TASK_COMPLETED` audit event.

---

## 4. Full Verification Suite Command

To execute all 10 scenarios sequentially in a single batch:

```bash
for s in scripts/manual_tests/phase_08/*.py; do
    echo "=== Running $s ==="
    uv run python "$s" || exit 1
done
```

All 10 scenarios pass with exit code `0`.
