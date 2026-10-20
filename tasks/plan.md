# Phase 10 implementation plan

Baseline: `1d07e39`; unrelated untracked results file preserved. All requested
preflight documents exist and have been read. Baseline: 225 passed, 6 skipped;
Ruff and mypy pass. No remote writes, production deployment, SYNTRA frontend,
or work on Phases 11–13 is authorized.

## Preflight gap analysis

| Area | Reuse | Gap |
|---|---|---|
| Roles | Existing domain AgentRole and ten capability profiles | Legacy agent classes cover seven older personas; no operational ten-role registry |
| Skills | Sixteen packages, SkillRegistry, progressive context builder | Role and manifest compatibility must both be validated per invocation |
| Models | ModelRuntime, ModelRouter, GeminiModelProvider, MockModelProvider | Runtime limits, failure accounting, tool allowlist and final validation need enforcement |
| Tools | ToolGateway, CapabilityPolicyEngine, SandboxToolBridge | Existing host workspace adapters must not be used for autonomous task execution |
| Workflow | LangGraph mission/task graphs and approval interceptor | Planning bypasses runtime; task graph fabricates test results by default |
| Worker | Scheduler, PostgreSQL attempts/leases/outbox, Redis dispatcher, Docker adapter | No production Redis consumer connects the scheduler to the sandbox adapter |
| Artifacts | ArtifactRepository and version checksums | Sandbox adapter emits UUIDs without storing content |
| Approvals | Digest-bound single-use plan/delivery approvals | Preserve authoritative gates and ensure operational path cannot take simulation shortcuts |
| Boundaries | Tenant repositories, grants, worktrees, hardened Docker | Validate identity, lease and cancellation before execution and at tool boundaries |

## Ordered work

1. Connect and test authoritative Redis worker lifecycle with real PostgreSQL,
   Redis and Docker. This is a gate before autonomous tool execution.
2. Validate ten role definitions, contracts, skills and limits; harden the shared
   ModelRuntime without introducing another provider or permission system.
3. Add sandbox-backed gateway bindings and bounded engineering execution with
   actual patch, command evidence and persisted artifacts.
4. Connect typed planning, implementation, independent review and bounded rework
   to LangGraph and the existing scheduler/approval system.
5. Add isolated defect fixture, acceptance tests and runnable manual scenarios.
6. Run regression/static/manual checks and independent hostile audit; correct
   defects and publish honest evidence and limitations. Stop at Phase 10.

Independent QA/review agents must not approve their own patches. Live Gemini
evidence is separate from deterministic provider evidence; missing prerequisites
remain explicit and prevent a false VERIFIED_COMPLETE verdict.

## Coordinated closeout continuation — 2026-10-16

The original implementation plan above is preserved as historical context.
Continue the same Phase 10 work using the dependency-ordered A–L workstreams,
resource gates, current-state health policy and explicit authorization envelopes
in [the consolidated execution plan](../docs/testing/phase-10-closeout-execution-plan-2026-10-16.md).
This extension does not mark the phase complete or grant infrastructure authority.
Historical recovery evidence and the immutable stopped-state backup must not be
rewritten. Fresh preflight records are separate under
`.syntra/phase10-evidence/20261016T013441+0200-closeout-preflight/`.

## B3 planning checkpoint — 2026-10-16

Current-state preservation is now governed by the single detailed
[B3 planning report](../docs/testing/phase-10-b3-current-state-preservation-plan-2026-10-16.md).
This is a planning-only extension, not authority to stop/start, clone, attach,
check or repair. The report separates historical B2 inconsistencies from unknown
current health, native PostgreSQL/Redis preservation from VM disks, and resource
eligibility from shutdown/persistence readiness. Next proposed scope is B3-Q
read-only service/shutdown qualification; later P preservation/assessment needs
its own approval after Q. All existing implementation work and open A–L tasks
remain unchanged. New evidence: `.syntra/phase10-evidence/20261016T160857+0200-b3-planning/`.

## B3-Q authorized diagnostics — 2026-10-16

Explicit B3-Q authorization was executed within read-only diagnostic scope.
See [the consolidated qualification report](../docs/testing/phase-10-b3q-qualification-2026-10-16.md)
and `.syntra/phase10-evidence/20261016T170316+0200-b3q/`.
Resources passed; database-local PG and Redis reads succeeded after a preserved
cross-DB permission failure with no privilege expansion. Both native stores
were idle in bounded observations. A stable completed Redis RDB offers a future
no-fork preservation route. Docker/containerd policies permit timeout SIGKILL;
wholly nonforcing shutdown remains unverified, not silently accepted.
No stop/start, backup/clone/attachment/checker/repair/test occurred. B3-P remains
unapproved and conditional on explicit scope, producer hold, resources and
shutdown-risk acceptance. Existing Phase 10 health and completion blockers remain.

## B3-P final authorization review — 2026-10-16

[The final review](../docs/testing/phase-10-b3p-final-authorization-review-2026-10-16.md)
recommends replacing the earlier combined P envelope with P-A host/native
preservation, checkpoint A, P-B normal stop/stopped VM backup, checkpoint B,
then separately approved P-C assessment. Nothing is executed by that proposal.
Fresh capacity fell below the proposed 12 GiB preservation gate; a fresh full
memory window and producer hold remain required. Existing Redis file ownership/
stability is verified, business ownership and restore validity are not. A failed
graceful stop cannot guarantee a new VM backup; no force/live-clone fallback.
New read-only review evidence is separate under
`.syntra/phase10-evidence/20261016T224957+0200-b3p-review/`.

## Accelerated quality-first closeout — active continuation

Source of truth remains the consolidated closeout plan and latest B3-P reports.
`tasks/todo.md` is the sole active status checklist; older checked items retain
their historical scope. Do not create a second tracker or repeat B1/B2.

Critical path: P-A host/native preservation -> human checkpoint A -> separately
authorized P-B stopped current-VM preservation -> checkpoint B -> separately
authorized P-C current no-write assessment -> any separately approved recovery
and start -> accepted infrastructure health -> focused/integration/live tests ->
final full regression -> manual acceptance/static checks -> independent audit ->
26-requirement sign-off and Phase 11 handover (documentation only).

P-A entry is now explicitly approved at 8 GiB, with 5 GiB reserve, 0.5 GiB task
budget, 2 GiB background contingency, 0.5 GiB slack and early stop at 6 GiB.
All memory/producer-hold prerequisites remain. P-B/P-C gates are unchanged.
No resource sample or synthetic classifier result clears filesystem health.

Safe offline slices, sequential in this dirty worktree (no model agents or new
worktrees):

1. Pure fail-closed storage classifier + synthetic regression tests + offline
   saved-evidence entry point (<=3 implementation/test files). Reproduce missed
   warnings before implementation; verify fixtures, provenance/freshness, checker
   exits and sticky blockers. Never execute the historical recovery helper.
2. Planning role-specific snapshot/read/handoff assertions in existing tests;
   parameterize Architect/Manager as well as PM. Run only disposable SQLite and
   simulated-container lifecycle checks; prepare real Docker assertions but do
   not run them before clearance.
3. Direct rejection/rework/changed-patch/fresh-review and command-result
   assertions; test assertion validation offline, prepare real acceptance for
   later. Production corrections only if an actual defect is reproduced.
4. Consolidate traceability, review inputs and acceptance-evidence requirements
   in existing tracker/report. Independent audit must remain independent, not
   the implementer's self-review. No independent final sign-off is invented.

Each slice records its exact command, exit and evidence separately. Pure tests
and scoped static checks may run now; no native database/Redis test writes or
Docker calls. No full-suite reruns until infrastructure clearance and the final
substantive correction. Preserve all pre-existing dirty changes and history;
no commits, reset, stash, checkout, publication, repair or lifecycle operations.
