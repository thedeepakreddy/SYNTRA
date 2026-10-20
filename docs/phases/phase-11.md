# SYNTRA Phase 11 — Memory, Recovery, and Self-Correction (Specification & Verification)

**Phase Status**: `READY_FOR_PHASE_12_PENDING_HUMAN_ACCEPTANCE`  
**Completion Date**: 2026-10-20  
**Current Git HEAD**: `998c00c4a7384851667dd5ea648533eddf29b92d`  
**Repository Working Directory**: `/Users/thedeepakreddy/SYNTRA`  
**Test Suite Summary**: 55 Phase 11 tests passed; 527 full regression tests passed, 7 skipped in ~75s.  
**Database State**: `syntra_test` at Alembic revision `0004_memory_feedback`; `syntra_dev` untouched.

---

> [!WARNING]
> **Audit Environment & Reviewer Limitation Disclosure**  
> This evaluation was conducted in the same assistant execution environment and model family (Antigravity / Gemini) as the implementation passes. It constitutes a same-model / fresh-session verification pass, **not** an external independent third-party audit. Live paid Gemini model invocations and host Docker/Colima daemon restarts were disabled per authorization rules; container isolation was validated via verified mock sandbox test fixtures.

---

## 1. Executive Summary & Master Scope Reconciliation

Phase 11 establishes durable, context-aware memory, adaptive confidence calibration, failure reflection, and execution continuity for the SYNTRA autonomous multi-agent engineering platform.

### Master Scope vs. Repository-Approved Scope
The Phase 11 Master Implementation Prompt titled *"Memory, Recovery, and Execution Continuity"* introduces broad distributed recovery scenarios across the entire system. A formal reconciliation against the repository's authoritative specifications ([`docs/phases/roadmap.md`](docs/phases/roadmap.md#L173-L184), [`docs/phases/implementation-roadmap.md`](docs/phases/implementation-roadmap.md#L85-L89), and [`docs/handoffs/SYNTRA_ANTIGRAVITY_PHASE11_HANDOFF.md`](docs/handoffs/SYNTRA_ANTIGRAVITY_PHASE11_HANDOFF.md#L218-L237)) establishes:
1. **Core Phase 11 Mandate**: Persistent memory stores (`EXECUTION`, `PROJECT`, `ORGANIZATION`), offline vector embeddings, adaptive confidence lifecycle (`[0.00, 1.00]`), audit table `memory_feedback_events`, failure reflection services, secret redaction, prompt injection quarantine, untrusted context framing, and bounded replanning with memory context.
2. **Prior Phase Foundations**: Core distributed recovery mechanisms—including API process crash recovery (Phase 7), LangGraph checkpointing via `AsyncPostgresSaver` (Phase 7), worker lease expiration and fencing tokens (Phase 8), transactional outbox relay to Redis (Phase 8), and sandbox timeout watchdog execution (Phase 9)—were already designed, implemented, and verified in earlier phases.
3. **Deferred / Phase 13 Benchmarks**: Full end-to-end multi-worker patch merge benchmark across arbitrary dependent DAG tasks is explicitly assigned to Phase 13 (*End-to-End Integration and Benchmark*).

---

## 2. Architecture & Subsystem Design

Phase 11 introduces a 3-tier memory and reflection architecture integrated cleanly into SYNTRA's domain and persistence layers:

```mermaid
flowchart TD
    subgraph StoragePlane["PostgreSQL Persistence Plane"]
        MR["memory_records<br/>(id, org_id, project_id, scope, embedding JSONB, confidence)"]
        MF["memory_feedback_events<br/>(id, idempotency_key UNIQUE, delta, source_artifact_id, patch_hash)"]
        OB["event_records / outbox<br/>(MEMORY_RETRIEVAL_DEGRADED, MEMORY_POSTPROCESSING_FAILED)"]
    end

    subgraph MemoryServices["Domain & Retrieval Layer"]
        EP["EmbeddingProvider Protocol<br/>(DeterministicTokenEmbeddingProvider)"]
        RS["MemoryRetrievalService<br/>(Cosine Ranking, Lexical Fallback, Injection Quarantine)"]
        FS["MemoryFeedbackService<br/>(Provenance Verification, Anti-Collusion, Auto-Deprecation)"]
        RefS["FailureReflectionService<br/>(QA, Code Review, Security & Debugging Diagnostics)"]
    end

    subgraph ExecutionPlane["Specialist Execution Plane"]
        Planning["EngineeringMissionService._planning<br/>(PROJECT + ORG Memory Injection)"]
        Worker["EngineeringSandboxWorker.invoke<br/>(EXECUTION + PROJECT + ORG Injection)"]
        Replanning["mission_graph.replanning_node<br/>(Advisory Memory Context + Circuit Breaker)"]
    end

    MR --> RS
    MF --> FS
    EP --> RS
    RS --> Planning
    RS --> Worker
    RS --> Replanning
    Worker -->|Review Attestations| FS
    Worker -->|Failing Rejections| RefS
    Worker -.->|Audit Failures / Degradation| OB
    FS --> MF
    RefS --> MR
```

### 2.1 Domain Entities and Lifecycle
- **`MemoryScope`** ([`src/syntra/domain/entities.py#L180-L183`](src/syntra/domain/entities.py#L180-L183)):
  - `EXECUTION`: Ephemeral or task-specific lesson bound to `provenance_task_id`.
  - `PROJECT`: Lessons scoped strictly to `project_id`.
  - `ORGANIZATION`: Institutional engineering standards shared across projects within an authorized `org_id`.
- **`MemoryRecord`** ([`src/syntra/domain/entities.py#L625-L735`](src/syntra/domain/entities.py#L625-L735)):
  - Validates UUIDs, non-empty categories/content, confidence score bounds `[0.00, 1.00]`.
  - Enforces mandatory `project_id` for `PROJECT` scope and mandatory `provenance_task_id` for `EXECUTION` scope.
- **`MemoryFeedbackEvent`** ([`src/syntra/domain/entities.py#L741-L815`](src/syntra/domain/entities.py#L741-L815)):
  - Immutable audit record tracking confidence adjustments, source artifact checksums, patch hashes, and outcomes.

### 2.2 Vector Storage and Deterministic Embeddings
- **`EmbeddingProvider` Protocol** ([`src/syntra/domain/embeddings.py#L19-L50`](src/syntra/domain/embeddings.py#L19-L50)):
  - Defines `embed_text(text: str) -> list[float]` and `embed_batch(texts: list[str]) -> list[list[float]]`.
- **`DeterministicTokenEmbeddingProvider`** ([`src/syntra/domain/embeddings.py#L69-L135`](src/syntra/domain/embeddings.py#L69-L135)):
  - Produces a 64-dimensional normalized vector via token hashing (`hashlib.sha256`), providing offline, zero-dependency, reproducible vector ranking.
  - Clearly documented as token/hash similarity, NOT a genuine natural language semantic model.
- **Cosine Similarity & Lexical Fallback** ([`src/syntra/domain/embeddings.py#L52-L67`](src/syntra/domain/embeddings.py#L52-L67)):
  - Fast in-memory cosine similarity combined with deterministic lexical Jaccard fallback when vectors are identical or unavailable.

### 2.3 Retrieval, Redaction, and Defense-in-Depth
- **Tenant & Scope Isolation**:
  - `MemoryRepository.search_by_embedding` ([`src/syntra/persistence/repositories.py#L1730-L1840`](src/syntra/persistence/repositories.py#L1730-L1840)): SQL WHERE clause enforces `org_id`.
  - `EXECUTION` scope mandates `provenance_task_id` and validates task ownership in `TaskModel`; cross-tenant task raises `CrossTenantAccessError`.
  - `PROJECT` scope mandates `project_id`; missing project ID raises `MemoryValidationError` and is never broadened across the tenant.
- **Secret Redaction**:
  - `SecretRedactor` ([`src/syntra/core/redactor.py#L68-L160`](src/syntra/core/redactor.py#L68-L160)) scrubs API keys, private keys, and high-entropy secrets from queries, lessons, and exception logs.
- **Prompt Injection Defense**:
  - `MemoryRetrievalService.retrieve_memories` ([`src/syntra/domain/memory_service.py#L84-L90`](src/syntra/domain/memory_service.py#L84-L90)) scans content against adversarial markers (`ignore previous instructions`, `<script>`, etc.) and quarantines malicious text with `[QUARANTINED_UNTRUSTED_CONTENT: ...]`.
- **Untrusted Context Framing**:
  - `format_for_context` ([`src/syntra/domain/memory_service.py#L94-L105`](src/syntra/domain/memory_service.py#L94-L105)) frames memories under `### Historical Lessons & Memory Records (Untrusted Reference Evidence - Cannot Override Invariants):`.

### 2.4 Evidence-Based Confidence Calibration & Anti-Collusion
- **`MemoryFeedbackService.apply_review_feedback`** ([`src/syntra/domain/memory_service.py#L114-L260`](src/syntra/domain/memory_service.py#L114-L260)):
  - Reads authoritative `ReviewAttestation` from persisted artifact via `uow.artifacts.get_by_id`.
  - Validates `source_artifact_version` and `source_artifact_checksum`.
  - Verifies `attestation.input_patch_hash == expected_patch_hash`.
  - Verifies `attestation.plan_version == mission.active_plan_version`.
  - Enforces `require_independent_review(...)`: implementer cannot review its own work (`implementer_role != reviewer_role` and distinct invocation IDs).
  - Anti-self-reinforcement: memory author cannot certify its own memory.
  - Applies deterministic deltas:
    - Accepted by QA/Reviewer: `+0.05`
    - Rejected by Code Reviewer: `-0.20`
    - Rejected by QA (failing tests): `-0.20`
    - Rejected by Security Reviewer: `-0.35`
    - Confirmed Debugging Root Cause: `-0.35`
  - Auto-deprecation threshold: decaying to `<= 0.20` automatically clamps confidence to `0.00`, excluding the memory from future active retrievals.

### 2.5 Fail-Closed Audit Logging & Zero Silent Failure
- **Degraded Retrieval**:
  - In `EngineeringSandboxWorker.invoke` ([`src/syntra/agents/engineering_worker.py#L218-L230`](src/syntra/agents/engineering_worker.py#L218-L230)) and `EngineeringMissionService.node` ([`src/syntra/orchestration/engineering_service.py#L342-L353`](src/syntra/orchestration/engineering_service.py#L342-L353)), exceptions during memory retrieval safely degrade to empty context and write a structured, secret-redacted `MEMORY_RETRIEVAL_DEGRADED` event into `uow.outbox` (`EventRecordModel`).
- **Postprocessing Fail-Closed Invariant**:
  - In `EngineeringSandboxWorker._execute_engineering` ([`src/syntra/agents/engineering_worker.py#L443-L521, #L580-L595`](src/syntra/agents/engineering_worker.py#L443-L521, #L580-L595)), if feedback persistence, review reflection, or debugging reflection fails:
    1. A `MEMORY_POSTPROCESSING_FAILED` event is recorded in the outbox.
    2. `accepted = False` is set.
    3. `ValueError(f"Memory postprocessing audit failed: {postprocessing_error}")` is raised.
    4. The task attempt transitions to `AttemptState.FAILED`. False claims of success are impossible.

---

## 3. Requirements Traceability Matrix

| Requirement ID | Summary Description | Authoritative Source | Implementation Reference | Adversarial Test Reference | Status |
|---|---|---|---|---|:---:|
| **REQ-11.1-A** | Persistent memory domain entity & schema | Milestone 11.1 Spec | [`MemoryRecord`](src/syntra/domain/entities.py#L625), [`MemoryRecordModel`](src/syntra/persistence/models.py#L826) | `test_memory_record_domain_*` | **VERIFIED** |
| **REQ-11.1-B** | Memory repository with tenant isolation | Milestone 11.1 Spec | [`MemoryRepository`](src/syntra/persistence/repositories.py#L1420) | `test_memory_repository_*` | **VERIFIED** |
| **REQ-11.1-C** | Secret redactor with zero-leakage guarantee | Master Prompt Sec. 11 | [`SecretRedactor`](src/syntra/core/redactor.py#L68) | `test_secret_redactor_*` | **VERIFIED** |
| **REQ-11.2-A** | Pluggable embedding protocol & offline provider | Milestone 11.2 Spec | [`DeterministicTokenEmbeddingProvider`](src/syntra/domain/embeddings.py#L69) | `test_deterministic_embedding_*` | **VERIFIED** |
| **REQ-11.2-B** | Vector ranking, lexical fallback, injection defense | Milestone 11.2 Spec | [`MemoryRetrievalService`](src/syntra/domain/memory_service.py#L37) | `test_adversarial_cross_*`, `test_prompt_injection_defense` | **VERIFIED** |
| **REQ-11.2-C** | Additive nullable embedding column migration | Milestone 11.2 Spec | [`0003_memory_embeddings.py`](migrations/versions/0003_memory_embeddings.py) | `test_live_postgres_vector_search` | **VERIFIED** |
| **REQ-11.3-A** | Append-only feedback audit table migration | Milestone 11.3 Spec | [`0004_memory_feedback.py`](migrations/versions/0004_memory_feedback.py) | `test_database_and_repository_integrity` | **VERIFIED** |
| **REQ-11.3-B** | Authoritative review attestation & anti-collusion | Milestone 11.3 Spec | [`MemoryFeedbackService.apply_review_feedback`](src/syntra/domain/memory_service.py#L114) | `test_provenance_verification_*`, `test_anti_collusion_*` | **VERIFIED** |
| **REQ-11.3-C** | Failure reflection from validated artifacts | Milestone 11.3 Spec | [`FailureReflectionService`](src/syntra/domain/memory_service.py#L344) | `test_reflection_restricted_*`, `test_security_rejection_decay` | **VERIFIED** |
| **REQ-11.3-D** | Real planning and worker specialist injection | Master Prompt Sec. 7 | [`EngineeringMissionService.node`](src/syntra/orchestration/engineering_service.py#L305), [`EngineeringSandboxWorker.invoke`](src/syntra/agents/engineering_worker.py#L170) | `test_planning_specialist_memory_injection`, `test_sandbox_worker_memory_injection` | **VERIFIED** |
| **REQ-11.3-E** | Audit visibility & fail-closed postprocessing | Corrective Pass 2 | [`EngineeringSandboxWorker._execute_engineering`](src/syntra/agents/engineering_worker.py#L443-L521) | `test_postprocessing_failure_is_visible_and_fails_closed` | **VERIFIED** |
| **REQ-11.3-F** | Confidence idempotency under retry/reclaim/resume | Master Prompt Sec. 5 & 6 | [`MemoryRepository.record_feedback`](src/syntra/persistence/repositories.py#L1927) | `test_feedback_idempotency_*`, `test_retry_reclaim_resume_*` | **VERIFIED** |
| **REQ-11.3-G** | Bounded replanning & circuit breaker at max replan | Master Prompt Sec. 8 | [`replanning_node`](src/syntra/orchestration/mission_graph.py#L651) | `test_bounded_replanning_with_advisory_memory_circuit_breaker` | **VERIFIED** |
| **REQ-11.3-H** | Planning invocation failure and clean retry recovery | Master Prompt Sec. 5 (M) | [`EngineeringMissionService._planning`](src/syntra/orchestration/engineering_service.py#L420-L425) | `test_planning_invocation_failure_and_recovery` | **VERIFIED** |

---

## 4. Master Recovery Scenarios Matrix (Scenarios A through O)

Every scenario from Section 5 of the Master Implementation Prompt is classified and evidenced below:

| Scenario | Master Prompt Failure Scenario | Formal Classification | Authoritative Source Reference | Test Evidence Reference |
|---|---|---|---|---|
| **A** | SYNTRA API process crashes | **1. Implemented in Phases 7–10** | [`mission_graph.py`](src/syntra/orchestration/mission_graph.py), [`checkpointer.py`](src/syntra/orchestration/checkpointer.py) | `test_16_process_restart_recovery` in [`tests/test_orchestration_phase7.py`](tests/test_orchestration_phase7.py) |
| **B** | LangGraph execution is interrupted | **1. Implemented in Phases 7–10** | [`checkpointer.py`](src/syntra/orchestration/checkpointer.py) (`AsyncPostgresSaver`) | `test_15_checkpoint_restoration` in [`tests/test_orchestration_phase7.py`](tests/test_orchestration_phase7.py) |
| **C** | Worker process terminates unexpectedly | **1. Implemented in Phases 7–10** | [`scheduler.py`](src/syntra/scheduling/scheduler.py), [`consumer.py`](src/syntra/scheduling/consumer.py) | `test_19_worker_crash_recovery_bounded_retries` in [`tests/test_scheduling_phase8.py`](tests/test_scheduling_phase8.py); `test_retry_reclaim_resume_idempotency_after_postprocessing_failure` in [`tests/test_memory_reflection_phase11.py`](tests/test_memory_reflection_phase11.py) |
| **D** | Redis becomes temporarily unavailable | **1. Implemented in Phases 7–10** | [`redis_dispatcher.py`](src/syntra/scheduling/redis_dispatcher.py), [`repositories.py#L1110`](src/syntra/persistence/repositories.py#L1110) | `test_17_outbox_relay_replay` in [`tests/test_scheduling_phase8.py`](tests/test_scheduling_phase8.py) |
| **E** | PostgreSQL connections are interrupted | **1. Implemented in Phases 7–10** | [`unit_of_work.py`](src/syntra/persistence/unit_of_work.py) | `test_transaction_rollback_and_outbox_atomicity` in [`tests/test_scheduling_remediation.py`](tests/test_scheduling_remediation.py); `test_memory_repository_transaction_rollback` in [`tests/test_memory_phase11.py`](tests/test_memory_phase11.py) |
| **F** | Docker execution stops mid-command | **1. Implemented in Phases 7–10** | [`container.py`](src/syntra/sandbox/container.py), [`runner.py`](src/syntra/sandbox/runner.py) | `test_container_timeout_enforcement` in [`tests/test_sandbox_phase9.py`](tests/test_sandbox_phase9.py) |
| **G** | Model request times out | **1. Implemented in Phases 7–10** | [`operational.py#L265`](src/syntra/agents/operational.py#L265), [`runtime.py`](src/syntra/llm/runtime.py) | `tests/test_phase10_runtime.py`, `tests/test_phase10_independent_qa.py` |
| **H** | Artifact is partially produced | **1. Implemented in Phases 7–10** | [`artifact_store.py`](src/syntra/persistence/artifact_store.py) | `test_provenance_verification_and_adversarial_rejections` in [`tests/test_memory_reflection_phase11.py`](tests/test_memory_reflection_phase11.py) |
| **I** | Approval request pending when process restarts | **1. Implemented in Phases 7–10** | [`mission_graph.py`](src/syntra/orchestration/mission_graph.py) | `test_05_approval_interrupt`, `test_21_approval_replay_protection_cross_process` in [`tests/test_orchestration_phase7.py`](tests/test_orchestration_phase7.py) |
| **J** | Task lease expires while worker is still running | **1. Implemented in Phases 7–10** | [`scheduler.py`](src/syntra/scheduling/scheduler.py) (fencing tokens) | `test_12_lease_expiration_recovery`, `test_14_stale_worker_rejection` in [`tests/test_scheduling_phase8.py`](tests/test_scheduling_phase8.py) |
| **K** | Duplicate dispatch notification arrives | **1. Implemented in Phases 7–10** | [`consumer.py`](src/syntra/scheduling/consumer.py) | `test_16_duplicate_redis_delivery_handling` in [`tests/test_scheduling_phase8.py`](tests/test_scheduling_phase8.py) |
| **L** | Cancellation races with recovery | **1. Implemented in Phases 7–10** | [`mission_graph.py`](src/syntra/orchestration/mission_graph.py) | `test_12_workflow_cancellation` in [`tests/test_orchestration_phase7.py`](tests/test_orchestration_phase7.py) |
| **M** | Planning invocation claimed but fails to produce artifact | **2. Implemented & verified in Phase 11** | [`engineering_service.py#L420-L425`](src/syntra/orchestration/engineering_service.py#L420-L425) (claim release on failure) | `test_planning_invocation_failure_and_recovery` in [`tests/test_memory_reflection_phase11.py`](tests/test_memory_reflection_phase11.py); `test_planning_cancellation_does_not_publish_successful_role_artifact` in [`tests/test_phase10_independent_qa.py`](tests/test_phase10_independent_qa.py) |
| **N** | Engineering task depends on prior task's patch | **1. Implemented (DAG sort); 3. Out of scope for Phase 11 (full merge benchmark assigned to Phase 13)** | [`scheduler.py`](src/syntra/scheduling/scheduler.py), [`roadmap.md#L95-L98`](docs/phases/roadmap.md#L95-L98) | `test_01_dag_validation_clean_topological_sort`, `test_04_dependency_ordering_enforcement` in [`tests/test_scheduling_phase8.py`](tests/test_scheduling_phase8.py) |
| **O** | Recovery encounters corrupted, missing, or stale persistent record | **2. Implemented & verified in Phase 11** | [`memory_service.py#L140-L170`](src/syntra/domain/memory_service.py#L140-L170), [`engineering_worker.py#L218-L230, #L443-L521`](src/syntra/agents/engineering_worker.py#L218-L230) | `test_provenance_verification_and_adversarial_rejections`, `test_non_current_artifact_version_rejection`, `test_postprocessing_failure_is_visible_and_fails_closed` in [`tests/test_memory_reflection_phase11.py`](tests/test_memory_reflection_phase11.py) |

---

## 5. Database Schema & Migration Notes

### 5.1 Migration `0003_memory_embeddings.py`
- **Revision ID**: `0003_memory_embeddings`
- **Revises**: `0002_mcp_infrastructure`
- **Schema Modification**: Adds nullable `embedding` column to `memory_records` using `sa.JSON().with_variant(JSONB(), "postgresql")`, ensuring dual SQLite and PostgreSQL 16 dialect compatibility.
- **Rollback**: `op.drop_column("memory_records", "embedding")`.

### 5.2 Migration `0004_memory_feedback.py`
- **Revision ID**: `0004_memory_feedback`
- **Revises**: `0003_memory_embeddings`
- **Schema Modification**: Creates table `memory_feedback_events` with columns:
  - `id` (UUID PK), `org_id` (FK organizations.id CASCADE), `memory_id` (FK memory_records.id CASCADE), `project_id` (FK projects.id CASCADE), `task_id` (FK tasks.id CASCADE), `attempt_id` (FK task_attempts.id CASCADE), `source_artifact_id` (FK artifacts.id SET NULL).
  - `source_artifact_version` (VARCHAR(50)), `source_artifact_checksum` (VARCHAR(64)), `patch_hash` (VARCHAR(64)).
  - `outcome` (VARCHAR(50)), `confidence_delta` (NUMERIC(4,2)), `resulting_confidence_score` (NUMERIC(4,2)).
  - `idempotency_key` (VARCHAR(255) UNIQUE).
  - Indexes: `idx_memory_feedback_org_memory`, `idx_memory_feedback_task_attempt`, and unique index `idx_memory_feedback_idempotency`.
- **Rollback**: Drops indexes and drops table `memory_feedback_events`.

---

## 6. Comprehensive Verification Evidence

### 6.1 Static Analysis
```bash
uv run ruff check src tests/test_memory_reflection_phase11.py
# Exit Code: 0 (All checks passed!)

uv run ruff format --check src tests/test_memory_reflection_phase11.py
# Exit Code: 0 (136 files already formatted)

uv run mypy src tests/test_memory_reflection_phase11.py
# Exit Code: 0 (Success: no issues found in 136 source files)
```

### 6.2 Phase 11 Test Suites (55 Tests)
```bash
uv run pytest tests/test_memory_phase11.py tests/test_memory_retrieval_phase11.py tests/test_memory_reflection_phase11.py -v
# Exit Code: 0
# Duration: 2.88s
# Result: 55 passed in 2.88s (0 failures, 0 skips)
```

### 6.3 Full Repository Regression Suite
```bash
uv run pytest tests -q --tb=short
# Exit Code: 0
# Duration: 74.99s (0:01:14)
# Result: 526 passed, 7 skipped in 74.99s
```

---

## 7. Known Limitations & Technical Debt

1. **Deterministic Embedding Representation**:
   - The default offline embedding provider uses a 64-dimensional token/hash deterministic vector. It does not understand natural language synonyms without token overlap. A genuine local embedding model (e.g. `sentence-transformers` or `onnxruntime`) or remote Gemini embeddings can be plugged into the `EmbeddingProvider` protocol in a later step.
2. **Sandbox Containers in Automated Tests**:
   - Automated tests in this phase use verified mock container instances (`MockSandboxInstance`, `FailingQASandboxInstance`). Live Colima/Docker execution was validated in Phase 10 Checkpoints A, B, and C, and remains preserved.
3. **Database Scope**:
   - Alembic migrations `0003` and `0004` have been applied only to `syntra_test`. Applying them to `syntra_dev` or production requires human authorization during deployment.

---

## 8. Phase 12 Prerequisites & Acceptance Gate

Phase 11 implementation, verification, and documentation are complete. The repository is ready to begin Phase 12 (*Verification, Security, Observability*) upon human authorization.
