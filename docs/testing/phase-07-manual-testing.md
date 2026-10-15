# Phase 7: LangGraph Workflow Orchestration Manual Testing Guide

**Project**: SYNTRA (Synchronized Intelligence for Autonomous Engineering)  
**Document**: Phase 7 Manual Verification & Operator Runbook  
**Target Subsystems**: `src/syntra/orchestration`, `src/syntra/domain`, `src/syntra/persistence`  
**Execution Environment**: Python 3.12+ via `uv run python`

---

## 1. Overview & Architecture Reference

This runbook provides operators and engineers with instructions and verified, runnable scripts to test and inspect SYNTRA's LangGraph Workflow Orchestration Engine, durable checkpoint state, cryptographic human-in-the-loop approval interrupts, replanning circuit breakers, and administrative lifecycle controls.

All scenarios described in this document have corresponding standalone executable test scripts located in:
```
scripts/manual_tests/phase_07/
```

---

## 2. Prerequisites & Environment Setup

Ensure dependencies and virtual environments are active:
```bash
cd /Users/thedeepakreddy/SYNTRA
uv sync
```

Run the automated test suite to confirm baseline functionality:
```bash
uv run pytest tests/test_orchestration_phase7.py -v
```

---

## 3. Executable Manual Scenarios

### Scenario 1: Mission Startup & Interrupt Checkpoint
**Script**: `scripts/manual_tests/phase_07/01_start_mission.py`  
**Objective**: Starts a new mission and verifies that LangGraph executes from `INTAKE` through `REQUIREMENTS_ANALYSIS`, `ARCHITECTURE_PLANNING`, `TASK_PLAN_GENERATION`, and `PLAN_VALIDATION`, then halts deterministically at `AWAITING_APPROVAL` with an active interrupt.

**Run Command**:
```bash
uv run python scripts/manual_tests/phase_07/01_start_mission.py
```

**Implementation Pattern**:
```python
import asyncio
from uuid import uuid4
from langgraph.checkpoint.memory import MemorySaver
from syntra.orchestration.engine import WorkflowOrchestrationEngine


async def main():
    checkpointer = MemorySaver()
    engine = WorkflowOrchestrationEngine(checkpointer=checkpointer)

    mission_id = uuid4()
    org_id = uuid4()
    result = await engine.start_mission(
        mission_id=mission_id,
        org_id=org_id,
        objective="Build high-throughput Redis caching layer",
    )

    assert "__interrupt__" in result
    interrupt = result["__interrupt__"][0].value
    assert interrupt["action_type"] == "TASK_PLAN_APPROVAL"

    snap = await engine.get_mission_state(mission_id)
    assert snap["values"]["domain_state"] == "AWAITING_APPROVAL"
    print("[SUCCESS] Mission paused at human approval gate.")


asyncio.run(main())
```

---

### Scenario 2: Approval Interrupt, Cryptographic Digest & Expiration Enforcement
**Script**: `scripts/manual_tests/phase_07/02_approval_interrupt.py`  
**Objective**: Inspects the approval request metadata, verifies HMAC-SHA256 signature against `syntra.core.config.get_settings().approval_secret_key`, and validates that tampered digests or expired approvals are strictly rejected with typed exceptions.

**Run Command**:
```bash
uv run python scripts/manual_tests/phase_07/02_approval_interrupt.py
```

**Key Validations**:
- **Tampered Digest**: Calling `resume_approval` with an altered `action_digest` raises `syntra.domain.exceptions.DigestMismatchError`.
- **Expired Approval**: If `expires_at` is fast-forwarded to the past, `resume_approval` raises `syntra.domain.exceptions.ApprovalExpiredError`.
- **State Invariance**: Mission state remains at `AWAITING_APPROVAL` and approval decision is not marked `CONSUMED`.

---

### Scenario 3: Plan Rejection & Replanning Circuit Breaker
**Script**: `scripts/manual_tests/phase_07/03_reject_plan.py`  
**Objective**: Verifies the human rejection feedback loop and circuit breaker limits.

**Run Command**:
```bash
uv run python scripts/manual_tests/phase_07/03_reject_plan.py
```

**Boundary Behavior**:
1. **Below Limit (`replan_count < max_replan_limit`)**: Rejection routes to `replanning` (domain: `PLANNING`), increments `replan_count`, regenerates the task DAG, and re-enters `AWAITING_APPROVAL`.
2. **At Limit (`replan_count == max_replan_limit`)**: Second rejection replans and pauses at approval.
3. **Above Limit (`replan_count > max_replan_limit`)**: Circuit breaker activates! The graph routes to `failed`, transitions domain state to `FAILED`, and records `error_message="Mission exceeded maximum replan limit of 2."`.
4. **Terminal Post-Failure Guard**: Subsequent `resume_approval` calls cannot restart or advance the failed mission.

---

### Scenario 4: Authorization and Full End-to-End Progression
**Script**: `scripts/manual_tests/phase_07/04_approve_and_resume.py`  
**Objective**: Exercises the two-gate human approval flow to completion.

**Run Command**:
```bash
uv run python scripts/manual_tests/phase_07/04_approve_and_resume.py
```

**Flow Steps**:
1. **Gate 1 (`TASK_PLAN_APPROVAL`)**: Human submits `decision="APPROVED"` with valid HMAC digest.
2. **Micro-Execution**: Workflow advances through `READY` -> `TASK_SCHEDULING` -> `EXECUTION_COORDINATION` -> `INTEGRATION` -> `INDEPENDENT_VERIFICATION`.
3. **Gate 2 (`DELIVERY_APPROVAL`)**: Workflow halts at the final delivery release interrupt.
4. **Final Delivery Approval**: Human submits release authorization. Mission transitions to `COMPLETED` and domain state updates to `COMPLETED`.

---

### Scenario 5: Checkpoint State & Metadata Inspection
**Script**: `scripts/manual_tests/phase_07/05_checkpoint_inspection.py`  
**Objective**: Queries the checkpointer directly using `thread_id="mission:{mission_id}"` and inspects channel values and security sanitization.

**Run Command**:
```bash
uv run python scripts/manual_tests/phase_07/05_checkpoint_inspection.py
```

**Key Validations**:
- `checkpointer.aget_tuple({"configurable": {"thread_id": thread_id}})` returns state channel dictionary.
- `create_checkpoint_metadata` strips all fields containing `secret`, `key`, or `token`.

---

### Scenario 6: Process Restart & Crash Recovery
**Script**: `scripts/manual_tests/phase_07/06_restart_recovery.py`  
**Objective**: Demonstrates crash recovery across process boundaries without side-effect duplication.

**Run Command**:
```bash
uv run python scripts/manual_tests/phase_07/06_restart_recovery.py
```

**Execution Pattern**:
1. Process 1 starts mission and advances to interrupt.
2. Process 1 instance is deleted (`del engine_1`).
3. Fresh Process 2 initializes with shared checkpointer.
4. `engine_2.get_mission_state(mission_id)` and `recover_mission(mission_id, org_id, checkpointer=shared_checkpointer)` restore the active checkpoint without executing any prior node.
5. Resuming from Process 2 continues execution seamlessly.

---

### Scenario 7: Administrative Pause, Resume, and Cancellation
**Script**: `scripts/manual_tests/phase_07/07_pause_and_cancel.py`  
**Objective**: Exercises administrative controls against authoritative database aggregates.

**Run Command**:
```bash
uv run python scripts/manual_tests/phase_07/07_pause_and_cancel.py
```

**Key Validations**:
- `pause_mission`: Sets mission state to `PAUSED`.
- `resume_mission`: Sets mission state back to `RUNNING`.
- `cancel_mission`: Sets mission state to `CANCELLED` and marks all active and pending tasks `CANCELLED`.
- Calling `cancel_mission` on a terminal mission raises `InvalidStateTransitionError`.

---

### Scenario 8: Transactional Outbox Event History Inspection
**Script**: `scripts/manual_tests/phase_07/08_event_history.py`  
**Objective**: Inspects the PostgreSQL / SQLite outbox table to verify transactional event emission.

**Run Command**:
```bash
uv run python scripts/manual_tests/phase_07/08_event_history.py
```

**Events Verified**:
- `MISSION_PAUSED`
- `MISSION_RESUMED`
- `MISSION_CANCELLED`
- `MISSION_FAILED`

---

## 4. Batch Execution of All Manual Scenarios

To execute the entire suite of 8 manual scenarios in sequence:

```bash
for f in scripts/manual_tests/phase_07/*.py; do
    echo "Running $f..."
    uv run python "$f" || exit 1
done
```

Expected output:
```
Running scripts/manual_tests/phase_07/01_start_mission.py...
[SUCCESS] Scenario 1 passed: Mission started, planned, and halted at human interrupt.
Running scripts/manual_tests/phase_07/02_approval_interrupt.py...
[SUCCESS] Scenario 2 passed: All digest, tampering, and expiration security checks verified.
Running scripts/manual_tests/phase_07/03_reject_plan.py...
[SUCCESS] Scenario 3 passed: Rejection replanning loop and circuit breaker verified.
Running scripts/manual_tests/phase_07/04_approve_and_resume.py...
[SUCCESS] Scenario 4 passed: Complete two-gate human approval and linear execution to COMPLETED.
Running scripts/manual_tests/phase_07/05_checkpoint_inspection.py...
[SUCCESS] Scenario 5 passed: Checkpoint channels and metadata integrity verified.
Running scripts/manual_tests/phase_07/06_restart_recovery.py...
[SUCCESS] Scenario 6 passed: Crash recovery and restart persistence verified.
Running scripts/manual_tests/phase_07/07_pause_and_cancel.py...
[SUCCESS] Scenario 7 passed: Pause, resume, and cancellation verified.
Running scripts/manual_tests/phase_07/08_event_history.py...
[SUCCESS] Scenario 8 passed: Transactional outbox event history verified.
```
