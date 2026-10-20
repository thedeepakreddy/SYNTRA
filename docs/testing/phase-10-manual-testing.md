# Phase 10 operator and manual testing guide

Date: 2026-10-15 (Europe/Budapest). Current status:
**PHASE_10_REQUIRES_WORK**. Scenarios 07–12 currently fail because local Docker
image storage returns I/O errors. Scenario 13 is BLOCKED_BY_CREDENTIALS. Earlier
successful runs below are historical evidence only.

## Prerequisites and safety

Run from the existing SYNTRA repository using its uv environment. Scenarios
01–06 use real registry/runtime/policy interfaces and deterministic responses;
07–12 require Docker, Redis and a dedicated PostgreSQL test database. The fixture
requires `SYNTRA_TEST_POSTGRES_URL` whose database name contains `test`; never
point it at production. Redis uses isolated stream keys and cleans only those
keys. The PostgreSQL fixture creates/drops only its UUID-named schema.

Provision environment secrets privately, never paste URLs containing passwords
into logs or reports. `SYNTRA_REDIS_URL` can select the authorized local Redis
instance. The runner loads local `.env` without printing it. No paid Gemini
account, external deployment, remote repository or push is part of these scripts.

The required local acceptance image is defined in
`docker/phase10-acceptance.Dockerfile`, based on `syntra-sandbox:latest`, with
pinned Python test dependencies. Build the existing base image first if needed,
then build the acceptance image with:

```sh
uv sync
docker build -f docker/sandbox-worker.Dockerfile -t syntra-sandbox:latest .
docker build -f docker/phase10-acceptance.Dockerfile -t syntra-phase10-acceptance:local .
```

Build-time package downloads require authorized network access. Task containers
still run with networking disabled, non-root, a read-only root, dropped
capabilities and bounded resources. Do not expose the Docker socket to agents.

Scripts are thin scenario runners over actual repository-interface pytest
acceptance cases. They are not independent reimplementations of the application.
Each reports its mode and returns pytest's actual nonzero failure code; exit 77
means a declared missing prerequisite, not PASS. Some scripts intentionally
exercise the same complete fixture at different handoff boundaries.

## Execute the scenarios

Run each script as `uv run python scripts/manual_tests/phase_10/<filename>`.

| Script | Coverage and mode | Earlier result / wall seconds | Latest result / wall seconds |
|---|---|---|---|
| 01_agent_registry.py | Real ten-role registry/manifest validation | PASS, exit 0 / 1.92 | PASS, exit 0 / 1.41 |
| 02_product_requirements.py | Deterministic PM ambiguity, requirements and skill checks | 4 passed, exit 0 / 1.62 | 4 passed, exit 0 / 1.50 |
| 03_architecture_proposal.py | Architect registry and typed runtime contract | 2 passed, exit 0 / 1.17 | 2 passed, exit 0 / 1.68 |
| 04_engineering_task_plan.py | EM typed runtime contract and registration | 2 passed, exit 0 / 1.18 | 2 passed, exit 0 / 1.61 |
| 05_agent_skill_resolution.py | Role/manifest resolution and rejection | 13 passed, exit 0 / 1.73 | 13 passed, exit 0 / 1.91 |
| 06_agent_tool_authorization.py | Real policy/gateway with controlled effects | 15 passed, exit 0 / 2.60 | 15 passed, exit 0 / 2.12 |
| 07_backend_coding_task.py | Scripted model; real PG/Redis/Docker accepted mission | 1 passed, exit 0 / 7.55 | 1 failed, exit 1 / 2.75 |
| 08_qa_review_handoff.py | Same real accepted mission including independent QA | 1 passed, exit 0 / 7.27 | 1 failed, exit 1 / 2.63 |
| 09_debugging_rework.py | Actual rejection → diagnosis → correction → re-review | 1 passed, exit 0 / 9.12 | 1 failed, exit 1 / 2.98 |
| 10_multi_agent_collaboration.py | Accepted and rejected/reworked missions | 2 passed, exit 0 / 14.31 | 2 failed, exit 1 / 3.42 |
| 11_scheduler_sandbox_integration.py | Actual authoritative PG → Redis → Docker worker and duplicate delivery | 1 passed, exit 0 / 2.79 | 1 failed, exit 1 / 2.35 |
| 12_complete_engineering_mission.py | Full two-scenario mission fixture and clean delivery gate | 2 passed, exit 0 / 13.90 | 2 failed, exit 1 / 3.22 |
| 13_live_gemini_engineering.py | Opt-in real provider, PG/Redis/Docker | BLOCKED_BY_CREDENTIALS, exit 77 / 0.88 | BLOCKED_BY_CREDENTIALS, exit 77 / 0.79 |

Latest 07–12 failures occur at Docker provisioning with image-blob I/O errors,
not a newly fabricated test verdict. Mode labels indicate intended real
infrastructure; they do not imply that failed provisioning succeeded.

## Production-oriented CLI (not the deterministic demonstration)

`uv run syntra engineering agents` prints the actual registry. Operational
missions require configured Gemini credentials, PostgreSQL, Redis, an existing
scoped mission/project and explicit database grants. `start`, `advance`, and
`decide` require the operator-authorized `--repository` and repeated
`--verify-command` options; `--image` chooses an already prepared sandbox image.
Verify command consistency across start/resume so digest-bound task specs do not
drift. A worker must be configured for the same organization/project/repository.

Use real identifiers and paths in place of the angle-bracket placeholders:

```text
uv run syntra engineering start <mission-uuid> <org-uuid> --repository <target-repository> --image <prepared-image> --verify-command "python -m pytest -q"
uv run syntra engineering decide <mission-uuid> <org-uuid> <human-admin-uuid> <action-digest> --repository <target-repository> --image <prepared-image> --verify-command "python -m pytest -q"
uv run syntra engineering worker <org-uuid> <project-uuid> <target-repository> --image <prepared-image>
uv run syntra engineering advance <mission-uuid> <org-uuid> --repository <target-repository> --image <prepared-image> --verify-command "python -m pytest -q"
```

Inspect the plan/delivery interrupt before approving its exact digest. Agents
cannot approve, push or deploy. Active human admin/owner membership is required.
CLI help for start/advance/decide was executed successfully; real Gemini-backed
CLI operation was not possible without credentials.

## Bounded live provider test

Once explicitly authorized credentials exist, run scenario 13. Its isolated
test mission uses a USD 1.00 total mission ceiling and per-invocation/runtime
caps. The script enables `SYNTRA_RUN_PHASE10_GEMINI=1` in its subprocess. It must
report real token/cost usage, actual tool effects, diffs, reviews and any failure;
do not count merely constructing the SDK client as live verification.

## Targeted recovery verification

After the operator restores Docker health, run:

```sh
uv run pytest tests/test_phase10_mission_live.py tests/test_phase10_worker_live.py tests/test_phase10_sandbox_security_live.py tests/test_sandbox_phase9.py -q --tb=short
uv run pytest tests/test_phase10_independent_qa.py tests/test_phase10_planning.py -q --tb=short
uv run pytest -q --tb=short
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

Then rerun scripts 01–13 and update the report. Do not remove Docker failure
assertions or change fixture expectations to make the result green.

Successful mission evidence can be exported by setting
`SYNTRA_PHASE10_EVIDENCE_DIR` to an absolute subdirectory beneath
`<repository>/.syntra/phase10-evidence/` for the mission pytest command. The test
exports actual persisted patches/JSON and `outcome.json`; source fixture, UUID
database schema, Redis stream, containers and worktrees have scoped cleanup.
Prior evidence is retained in `2026-10-15-delivery/`; choose a new directory for
new runs so historical artifacts cannot be mistaken for fresh verification.

## Current infrastructure diagnosis and authorization boundary

`docker ps` returned no running containers at inspection, but `docker system df`
failed enumerating image blobs. Colima reports running. Host disk is 96% used
(8.1 GiB available); VM `/` has about 18 GiB free and `/var/lib/containerd` about
93 GiB free. This does not establish the precise corruption cause.

Final all-container inspection found one dead test sandbox:
`syntra_sandbox_033e7b19-5182-431a-8059-653ff4329b4a_1`. Inspection confirmed its
mounts are inside a test fixture path. An exact-name removal attempt failed with
an I/O error writing containerd's metadata database. It remains dead, not running;
cleanup is therefore not declared complete. No images, volumes or other
containers were removed.

Do not prune images, delete the container store, reset the VM or erase volumes.
A Colima restart can interrupt unrelated services and needs explicit user
approval. Preserve database/container data. Diagnose and repair the runtime
before retrying the live suite; do not repeatedly hammer a failing store.
