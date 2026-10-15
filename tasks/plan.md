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
