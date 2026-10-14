# SYNTRA LangGraph Workflow State Machine Design

## 1. Overview
SYNTRA uses **LangGraph** for durable workflow orchestration. Workflows are organized hierarchically into two decoupled state graphs:
1. **Mission Graph**: Governs the macro lifecycle from objective intake to final delivery approval.
2. **Task Execution Graph**: Governs the micro execution lifecycle for an individual task assigned to an agent.

All state transitions persist checkpoints in PostgreSQL, ensuring that crashes, restarts, or human approval delays never result in state loss.

---

## 2. Mission Graph (Macro Lifecycle)

```mermaid
stateDiagram-v2
    [*] --> INTAKE
    INTAKE --> REQUIREMENTS_ANALYSIS
    REQUIREMENTS_ANALYSIS --> ARCHITECTURE_PLANNING
    ARCHITECTURE_PLANNING --> TASK_GRAPH_GENERATION
    TASK_GRAPH_GENERATION --> PLAN_VALIDATION
    PLAN_VALIDATION --> AWAITING_HUMAN_APPROVAL: Plan Approval Checkpoint
    
    AWAITING_HUMAN_APPROVAL --> READY: Approval Granted
    AWAITING_HUMAN_APPROVAL --> REPLANNING: Approval Rejected
    
    READY --> TASK_SCHEDULING
    TASK_SCHEDULING --> PARALLEL_EXECUTION
    PARALLEL_EXECUTION --> INTEGRATION: All Tasks Complete
    PARALLEL_EXECUTION --> REPLANNING: Blocker / Failure Exceeded
    
    INTEGRATION --> INDEPENDENT_VERIFICATION
    INDEPENDENT_VERIFICATION --> DELIVERY_APPROVAL: Verification Passed
    INDEPENDENT_VERIFICATION --> PARALLEL_EXECUTION: Regression Detected
    
    DELIVERY_APPROVAL --> COMPLETED: Human Approval
    
    %% Alternate States
    PARALLEL_EXECUTION --> PAUSED: User Interruption
    PAUSED --> PARALLEL_EXECUTION: Resume
    PARALLEL_EXECUTION --> CANCELLED: Mission Cancelled
    REPLANNING --> TASK_GRAPH_GENERATION
    COMPLETED --> [*]
    CANCELLED --> [*]
```

---

## 3. Task Execution Graph (Micro Lifecycle)

```mermaid
stateDiagram-v2
    [*] --> TASK_ASSIGNED
    TASK_ASSIGNED --> CONTEXT_PREPARATION
    CONTEXT_PREPARATION --> SKILL_LOADING
    SKILL_LOADING --> IMPLEMENTATION
    IMPLEMENTATION --> LOCAL_TESTING
    LOCAL_TESTING --> ARTIFACT_SUBMISSION: Tests Pass Locally
    LOCAL_TESTING --> IMPLEMENTATION: Local Failure (Bounded Retry)
    
    ARTIFACT_SUBMISSION --> INDEPENDENT_REVIEW
    INDEPENDENT_REVIEW --> VERIFICATION: Review Passed
    INDEPENDENT_REVIEW --> IMPLEMENTATION: Review Rejected (With Comments)
    
    VERIFICATION --> VERIFIED: Independent Tests Passed
    VERIFICATION --> [*]: Escalated / Failed
    VERIFIED --> [*]
```

---

## 4. Key Orchestration Invariants
1. **Durable Human Interrupts**: When entering `AWAITING_HUMAN_APPROVAL` or `DELIVERY_APPROVAL`, the graph execution halts cleanly and persists the state checkpoint. Execution resumes only when the approval decision record is committed.
2. **Idempotent Side Effects**: Nodes interacting with the filesystem, sandbox, or external Git repositories write idempotency tokens to avoid duplicate effects during retries.
3. **Mission Cancellation Semantics**: Cancelling a mission prevents new tasks from being scheduled, revokes active worker leases, and triggers sandbox cleanup.
