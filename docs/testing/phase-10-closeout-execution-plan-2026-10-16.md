# Phase 10 coordinated closeout execution plan — 2026-10-16

**Initial execution-plan checkpoint, not completion certification.**
The 2026-10-17 final completion directive is a continuation of this plan; the
sole active status tracker remains `tasks/todo.md`. Later P-A authorization and
its P-A-only 8 GiB amendment supersede initial ungranted/P-A-capacity proposals
below, not P-B/P-C/restart/repair approvals. The maintenance declaration is
confirmed; observed hold and fresh resources remain mandatory. Current actual
blockers and evidence are in the delivery report's current critical-path section.
Do not repeat B1/B2 or treat the directive as blanket infrastructure authority.
Verdict: **PHASE_10_REQUIRES_WORK**. Infrastructure remains
`BLOCKED_FILESYSTEM_CHECK_REQUIRED`; a recent normal host-memory sample does not
resolve ext4 consistency. Initial Category B/C proposals below are historical;
sections 13–14 record later B1/B2 authorizations/results. B3/Category C remain
ungranted; B2's one historical clone and assessment are completed, not reusable.
No Phase 11–13 work or SYNTRA frontend development is included.

This extends, rather than replaces, `tasks/plan.md` and `tasks/todo.md`.
The planning skill requires the plan before implementation; the documentation
skill requires historical evidence and new decisions to remain distinguishable.
No source/test implementation was changed during this initial checkpoint.

## 1. Authority, documents and chronology

Authoritative requirements: `docs/phases/roadmap.md` Phase 10;
`docs/phases/implementation-roadmap.md`; `AGENTS.md`;
`docs/architecture/agent-design.md`; the original user Phase 10 master request
(`/Users/thedeepakreddy/.codex/attachments/069f66ec-d350-4dcb-bcfe-e39f078d3630/Pasted text.txt`,
especially sections 9, 11, 17, 21, 29–34 and 39); and the new coordinated assignment
(`/Users/thedeepakreddy/.codex/attachments/ab296796-ac71-4e8b-ae19-312618a0f9f9/Pasted text.txt`).
The original section 39 supplies the 26 completion requirements indexed below.

Inspected current reports: `docs/phases/phase-10.md`, `docs/phases/progress.md`,
`docs/testing/phase-10-verification.md`, `phase-10-independent-audit.md`,
`phase-10-manual-testing.md`, `phase-10-infrastructure-diagnosis-2026-10-16.md`,
`phase-10-recovery-preflight-2026-10-16.md`,
`phase-10-controlled-recovery-2026-10-16.md`, and
`phase-10-offline-assessment-safety-review-2026-10-16.md` under `docs/testing/`.
Latest resource-readiness reports before this campaign are conversation/tool
records, not separate repository report files; do not invent missing filenames.

Chronology determines precedence:

1. October 15 23:29:10 CEST: host APFS ENOSPC, virtual-disk write failures,
   aborted ext4 journal, Docker blob/metadata I/O failures.
2. October 16 00:34–00:36: approved graceful stop, 15-file stopped-state
   clonefile backup, source/clone full hashing, one same-profile restart.
3. Existing image reads recovered. Kernel warnings still required a filesystem
   check. Original helper missed warning forms. Its optimistic JSON is historical.
4. Real infrastructure selection completed: 18 passed/1 skipped; QA/planning:
   110 passed. These are deterministic-model results with real effects.
5. `health-review.json` superseded `health-result.json`; harness stopped with
   exit 130. Full regression has no completed result; static/manual reruns stopped.
6. Subsequent read-only reviews rehashed all 15 backup files successfully,
   identified GPT/ext4 geometry and investigated resources/tooling. No checker ran.
7. This campaign: fresh metadata/source/evidence inspection and bounded reviewer
   planning review only. Current host/Docker readings below supersede historical
   inventory, not the unresolved authoritative filesystem blocker.

Original reports, logs, helper, backup and passing/failed evidence are unchanged.
Historical manual-guide headings and old image-read failures predate the later
successful selected recovery run; they must not be presented as current results.

## 2. Current verified status and evidence boundary

Campaign evidence directory:

```text
/Users/thedeepakreddy/SYNTRA/.syntra/phase10-evidence/20261016T013441+0200-closeout-preflight/
```

- Git: branch `main`, HEAD `998c00c4a7384851667dd5ea648533eddf29b92d`.
  Implementation commit `4b39a8d` retained. Baseline manifest covers 446
  tracked/nonignored regular files before plan updates. Existing dirty files are
  preserved; this plan does not authorize commits, branch resets or publication.
- Colima inventory at 01:35:47 CEST: existing `default` Running, arm64,
  2 CPUs, 4 GiB configured VM RAM, 100 GiB configured disk; no profile changes.
- Docker context `colima`; no running containers. Existing protected container
  `a178d7fd1428` remains Exited (137). No cleanup or deliberate state change.
- Existing image metadata reads succeed with original IDs:
  `syntra-sandbox:latest` = `a71c85627b01...`;
  `syntra-phase10-acceptance:local` = `63c9946b06f2...`.
  This does not validate all image layers, Docker writes or filesystem consistency.
- Authoritative filesystem result remains BLOCKED. Current guest kernel/service
  logs were not recollected through SSH in this initial stage; guest login can
  write authentication/service logs. Include such collection explicitly in the
  controlled current-state investigation, rather than claiming global no-write.
- Host PostgreSQL/Redis processes and test configuration are present. Connection,
  persistence and isolation health have not been retested. No DB/Redis test writes.
- Gemini credential presence check found no usable `GEMINI_API_KEY` in the
  scoped environment/project `.env`. Values were never printed. Live execution
  is BLOCKED_BY_CREDENTIALS and separately BLOCKED_BY_AUTHORIZATION; no call made.

Backup:

```text
/Users/thedeepakreddy/SYNTRA/.syntra/infrastructure-backups/20261016T002121+0200/
```

15 file sizes, modes and inode identities still match. Verified manifest equals
retained `backup-result.json` byte-for-byte; SHA-256
`c81349d1a8c1173ffc741c5876594cd88a0b8d7f20749e7051461e082320fbf5`.
Unverified-manifest SHA-256 remains
`03c188c48180f8717c88ac1b4810b1e42be88fabb704daea05575fb8ca8329a2`.
The previous full 15-file rehash passed; it was not unnecessarily repeated in
this planning stage. Full source-image hashing is mandatory immediately before
authorized cloning. Metadata equality is not a new full-content verification.

Earlier evidence is present: 38 files under `2026-10-15-delivery/`, 105 under
`20261016T002121+0200-recovery/`. Both completed selection stdout/stderr hashes
still match `verification-results.json`; their pass counts remain historical.

## 3. Resources, separate gates and interruption policy

First current window, 01:34:41–01:36:41: installed RAM 8 GiB; pressure WARNING
throughout; proxy headroom approximately 1.43–1.73 GiB; zero additional swap-outs.
Capacity varied from 8,004,874,240 bytes (below 8 GiB) to 14,477,799,424 bytes.
No recovery action was started when capacity was below the gate.

Refresh at 01:44:08: conservative availability 14,766,841,856 bytes
(14.766842 GB / 13.752693 GiB), headroom 1.812 GiB, pressure NORMAL,
swap 2963 MiB used, swap-out counter unchanged. One normal sample is insufficient;
the confirmation window and final gate disposition are recorded in the evidence
and addendum below. Capacity is not reserved; remeasure before every action.

The proxy is free + inactive + speculative pages, not guaranteed allocatable RAM.
Do not double-count purgeable/file-backed memory. Compression/swap usage is not
itself a failure criterion. RSS is not complete process charged footprint.
Current relevant processes include ChatGPT/Codex, Virtualization/limactl,
PostgreSQL, Redis and Spotlight; no unrelated application is terminated.

| Workload | Required gate, unchanged from supplied proposal unless stated |
|---|---|
| Package dry-run | >=8 GiB available, >=1 GiB proxy headroom, noncritical pressure, no sustained swap-out growth; monitor the new process tree |
| Bottle installation | Successful exact dry-run, unchanged resolution, >=8.25 GiB available, >=1.5 GiB headroom, stable noncritical pressure and no sustained swap-out growth |
| Filesystem assessment | NORMAL pressure in >=3 samples spanning >=2 minutes; >=1.5 GiB headroom; no sustained swap-out growth; >=8 GiB available before each stage, >=5 GiB operating reserve throughout |
| Infrastructure tests | **Proposed additional gate:** current-state filesystem/Docker health accepted; normal pressure and >=1.5 GiB headroom across >=2 minutes; >=8 GiB before each selection and >=5 GiB throughout; sequential pytest selections/no extra xdist concurrency |

Last row is a documented test-operation proposal for approval, not a retrospective
change to any prior test result. Existing containers retain 512m/1 CPU/100 PID
limits; paused coding containers still consume memory. Do not lower isolation or
weaken tests to fit resources. Observe actual peak footprint and disk growth.

Budgets: provisioning 256 MiB incremental allowance; analysis clone/evidence/COW
1.5 GiB allowance; historical source is 100 GiB logical/966,623,232 allocated
bytes. These are engineering allowances, not guarantees. No 100 GiB materialized
copy, full partition extraction, source-build fallback or automatic cleanup.

No interruption is needed for a derivative of the existing historical backup.
A current-state snapshot requires newly approved graceful shutdown and downtime;
the earlier one-restart authorization has been consumed and is not reusable.

## 4. Ordered workstreams and completion contracts

Dependencies: **B -> C -> D -> E -> A -> G -> H -> I -> J -> L**.
F (classifier) and source/test preparation for G/J can proceed without unhealthy
infrastructure after this plan checkpoint. K is an optional separately authorized
branch, never a substitute for G–J. No infrastructure tests while A is blocked.

### A — Infrastructure health

- Requirement/status: current-state ext4, Colima, existing image identities,
  Docker/containerd, PostgreSQL and Redis health. **BLOCKED**.
- Prerequisites: D findings, E/current-state resolution, F corrected gate; risk HIGH.
- Authorization/owner: guest-log access/current-state operations in B2/B3 below;
  trusted infrastructure collector and operator, not autonomous engineering roles.
- Verify/evidence: complete boot-bound kernel/service captures, source UUID and
  checkpoint time, actual supported offline current-state result, image identities,
  protected container inventory and service probes. No fabricated clean status.
- Done: explicit current-state health decision plus no unresolved storage errors;
  image readability or historical checker exit 0 alone cannot complete A.

### B — Backup and resource readiness

- Requirement/status: immutable original backup and repeatable operation-specific
  gates. Metadata/evidence preservation PASSED; current full hashes before use
  and operation gates remain **UNVERIFIED until measured at that stage**.
- Prerequisites: none; risk LOW for inspection, HIGH if preservation fails.
- Authorization/owner: routine reads/reports allowed; additional disks/clones need
  B2/B3 approval. Owner: infrastructure preflight.
- Verify/evidence: df/diskutil bytes+GB+GiB, memory/swap sample JSON, manifests,
  source/clone hashes, inode/size/mode checks and original 446-file source baseline.
- Done: gate passes immediately before operation and evidence remains intact.

### C — Diagnostic tool provisioning

- Requirement/status: trusted compatible e2fsprogs 1.47.4 ARM64 Tahoe bottle.
  **PASSED B1** after explicit authorization: exact monitored dry-run, bottle
  hash verification, installation and native integrity/version/library checks.
  See section 13; device-level assessment remains outside B1.
- Prerequisites: B; risk MEDIUM (Homebrew/cache writes, transient memory).
- Authorization/owner: B1; exact commands and checksum in section 5.
- Verify/evidence: actual dry-run resolution, exit/timing/process-tree memory,
  downloaded bottle SHA, installed binary version/hash/architecture/library linkage.
- Done: exact binary validated, no unrelated modification/source compilation.

### D — Historical no-write filesystem assessment

- Requirement/status: assess an approved unmounted derivative, not the live disk.
  **COMPLETED B2: FILESYSTEM_INCONSISTENCIES_DETECTED**, native exit 4; all
  protective/integrity controls passed. See section 14. This does not clear A.
- Prerequisites: B/C and B2; risk MEDIUM with immutable-source protections.
- Owner: trusted host infrastructure procedure; no Docker/guest analysis sandbox.
- Verify/evidence: direct clonefile, device provenance/read-only/unmounted proof,
  full e2fsck output/bitmask and original/clone post-hashes (sections 6–7).
- Done: interpretable supported historical result, or honest incomplete finding;
  D does not clear A and never implies repair permission.

### E — Current-state investigation/recovery if needed

- Requirement/status: resolve actual current filesystem condition. **BLOCKED**.
- Prerequisites: D and evidence-based next decision; risk HIGH/downtime.
- Authorization/owner: B3 for graceful stop/fresh preservation/no-write assessment;
  any replay/repair/restore/forced stop requires separate Category C approval.
- Verify/evidence: new current-state backup and hash/boot chronology; supported
  unmounted assessment; justified health decision, followed by separately approved
  start with its possible journal writes disclosed.
- Done: current state accepted under documented policy, not an optimistic regex.

### F — P1 recovery health-classifier remediation

- Requirement/status: recognize actual missed warnings and fail closed.
  **FAILED existing helper / PLANNED correction**.
- Prerequisites: inspect old helper/log fixture (done); risk MEDIUM; normal
  repository implementation requested in assignment section 11, no host mutation.
- Owner/files: proposed pure `src/syntra/core/storage_health.py`,
  `tests/unit/test_storage_health_unit.py`, and a new recovery-facing collector
  under `scripts/phase10/`; never edit the executed historical helper.
- Verify: `.venv/bin/python -m pytest tests/unit/test_storage_health_unit.py -q`
  using synthetic fixtures only, no Docker/DB/network; no dependency installation.
- Done: independently reviewed negative tests, sticky blockers and reason codes;
  passing classifier tests must not label the actual filesystem healthy.

### G — Functional workflow verification and P2 assertions

- Requirement/status: all ten role contracts, real handoffs/commands/patches,
  independent attestations and bounded rework. **PARTIALLY_VERIFIED historically**.
- Prerequisites: source/test preparation may be independent; live runs require A/F.
  Risk MEDIUM; ordinary repository fixes allowed; test-owned effects after health.
- Owner: existing operational/handoffs/engineering_worker/engineering_service,
  tests/test_phase10_* and approved target fixtures; no second scheduler/runtime.
- Verify/evidence: actual failure/fix/review chain, typed persistence/identity and
  clean candidate digests; role-specific gaps below; new outputs only.
- Done: real infrastructure tests pass with strengthened assertions and scoped
  cleanup, not merely stage labels or deterministic response queues.

### H — Complete automated regression

- Requirement/status: relevant Phase 7–9 and full suite exit 0 plus Ruff/mypy.
  **BLOCKED**; earlier full run failed, recovery full run interrupted.
- Prerequisites: A/G; risk MEDIUM from disposable schemas/Redis/container writes.
- Owner: existing environment/test harness; no uv sync or package upgrade implied.
- Verify/evidence: exact commands in section 9, complete stdout/stderr, all skips
  explained, fresh result/time/hash records; no conversion of failures to skips.
- Done: completed full-suite exit 0 and required static checks, no unresolved
  mandatory prerequisite skips or hidden platform failure.

### I — Manual scenarios 01–13

- Requirement/status: **BLOCKED** for fresh campaign. Prior 01–12 results are
  historical; 13 remains optional live evidence with explicit blockers.
- Prerequisites: A/G/H, approved dedicated test DB/Redis and existing images.
- Risk MEDIUM; owner: existing scripts/manual_tests/phase_10/* and _runner.py.
- Verify/evidence: each exact script separately, mode/exit/time/artifacts;
  exit 77 is blocked, never PASS; preserve previous manual evidence.
- Done: supported mandatory scenarios pass and opt-in live status remains honest.

### J — Independent correctness/security audit

- Requirement/status: fresh final audit **UNVERIFIED**. Carson completed a separate
  read-only planning review only; this is not a new release sign-off.
- Prerequisites: F/G/H/I evidence; risk LOW for source review, probes scoped safely.
- Owner: independent reviewer invocation, separate from implementer; same
  model/provider organization limitation disclosed; no external third-party claim.
- Verify/evidence: reopen every old P1, P2 workflow provenance, permissions,
  cancellation/retry/accounting/cleanup; findings matrix with reproduction,
  correction, command evidence and residual risk. Scope includes health classifier.
- Done: all critical/high in-scope findings closed by actual independent evidence.

### K — Authorized live Gemini verification

- Requirement/status: **BLOCKED_BY_CREDENTIALS / BLOCKED_BY_AUTHORIZATION**.
- Prerequisites: A, credential readiness, model availability and separate paid-call
  approval with exact model/ceiling/timeouts; risk paid/external data disclosure.
- Owner: existing Gemini provider/ModelRuntime/registry, isolated acceptance task.
- Verify/evidence: real provider responses, tools/patch/tests/review, usage and
  estimated/unknown costs. Existing scenario has a USD 1 mission ceiling;
  verify the requested cap before approval rather than silently granting it.
- Done: actual authorized bounded live result, or accurately labeled UNVERIFIED.
  Original sections 17/33/39 make live opt-in and require labeling missing live
  evidence; no invented waiver and no all-ten LIVE_MODEL_VERIFIED claim.

### L — Final acceptance and Antigravity handover

- Requirement/status: **BLOCKED** on mandatory workstreams, not on a calendar date.
- Prerequisites: A/F/G/H/I/J; K governed by original opt-in policy. Risk incorrect
  release certification. Owner: coordinator, with independent review evidence.
- Verify/evidence: 26-item traceability below, final report sections A–T requested
  by current assignment, exact changed files/commit proposal and residual risks.
- Done: every mandatory item truly passes or verdict remains REQUIRES_WORK/
  BLOCKED/UNVERIFIED. No undocumented DEFERRED_BY_APPROVED_SCOPE entries.
  Handover describes contracts/debt only; no Phase 11 implementation.

## 5. Tooling commands and exact approval envelope B1

Actual installed version: **Homebrew 7.0.9**. `brew help install` exit 0 explicitly
supports `--dry-run`, `--formula`, `--force-bottle`, `--skip-post-install` and warns
about dependent updates/cleanup. Only version/help were run, not a package dry-run.

Current official metadata: e2fsprogs 1.47.4 revision 0, ARM64 Darwin macOS 26
(`arm64_tahoe`), keg-only; bottle SHA-256:

```text
f8024861ae8b5a645374d7960a5b5e3c41576c792712925d55deb186a74a1d06
```

Bottle 2,465,453 bytes; installed payload 9,077,613 bytes. Existing ARM64
gettext 1.0 and libunistring 1.4.2 satisfy recorded bottle requirements; gettext's
json-c 0.19 dependency is also installed. No source build/pkgconf provisioning.
Metadata identity is verified; no downloaded payload exists to hash yet.
Sources: [Homebrew formula](https://formulae.brew.sh/formula/e2fsprogs),
[formula API](https://formulae.brew.sh/api/formula/e2fsprogs.json),
[official bottle registry](https://ghcr.io/v2/homebrew/core/e2fsprogs/manifests/1.47.4),
[Homebrew command semantics](https://docs.brew.sh/Manpage).

**B1a proposed monitored dry-run (approval required):**

```sh
/usr/bin/time -l env -u HOMEBREW_FORCE_API_AUTO_UPDATE -u HOMEBREW_BUILD_FROM_SOURCE \
  HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_CLEANUP=1 \
  HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK=1 HOMEBREW_NO_INSTALL_UPGRADE=1 \
  HOMEBREW_NO_ANALYTICS=1 /opt/homebrew/bin/brew install \
  --dry-run --formula --force-bottle --skip-post-install e2fsprogs
```

Capture process-tree memory, elapsed time, swap/storage deltas and exact output.
Dry-run does not install packages, but Homebrew may write cache/metadata/log/lock
files; this is not a global zero-write guarantee. Stop on runtime bootstrap,
additional packages, changed version/architecture, unsupported flags, source
compilation, critical pressure, sustained swap-out growth or failed capacity.

**B1b proposed installation (explicit installation approval required):**
first fetch only the selected bottle, validate its exact SHA and compare current
selection/dependency receipts. The reviewed fetch flag is `--bottle-tag=arm64_tahoe`;
do not combine it with mutually exclusive `--force-bottle` in the fetch command.
Then use the same controlled environment:

```sh
env -u HOMEBREW_FORCE_API_AUTO_UPDATE -u HOMEBREW_BUILD_FROM_SOURCE \
  HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_CLEANUP=1 \
  HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK=1 HOMEBREW_NO_INSTALL_UPGRADE=1 \
  HOMEBREW_NO_ANALYTICS=1 /opt/homebrew/bin/brew fetch \
  --formula --bottle-tag=arm64_tahoe e2fsprogs
```

```sh
env -u HOMEBREW_FORCE_API_AUTO_UPDATE -u HOMEBREW_BUILD_FROM_SOURCE \
  HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_CLEANUP=1 \
  HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK=1 HOMEBREW_NO_INSTALL_UPGRADE=1 \
  HOMEBREW_NO_ANALYTICS=1 /opt/homebrew/bin/brew install \
  --formula --force-bottle --skip-post-install e2fsprogs
```

The actual dry-run must show only the exact package. A changed selection is a
STOP, not authority to upgrade dependencies. No unsupported ignore-dependencies,
force overwrite, sudo, global PATH edit, services start or cleanup. Normal-user
Homebrew destinations were writable in previous metadata inspection; recheck
before use. If the installed tool needs ungranted privileges, stop.

Expected binary `/opt/homebrew/Cellar/e2fsprogs/1.47.4/sbin/e2fsck`, opt alias
`/opt/homebrew/opt/e2fsprogs/sbin/e2fsck`. After approved provisioning, inspect
`file`, `otool -L`, binary SHA and version-only output. No filesystem target in
this stage. Preserve cache/receipts and any failed new package state for review;
no unilateral uninstall/cleanup rollback is authorized.

## 6. Historical assessment B2: exact target and no-write controls

Target is the backup's `data/datadisk`, not
`/Users/thedeepakreddy/.colima/_lima/_disks/colima/datadisk` (live source).
Data-image SHA: `9de7d661f8d4c4a7fce36ad6a54f74d235df57e0d6328da080a8aa3aaf2b12dd`.
GPT entry 1: offset 1,048,576; length 107,372,085,248 bytes;
partition GUID `17300ecd-f3b8-4833-9d55-18ffc2a130b8`;
ext4 UUID `3de9071f-0361-4f65-88a3-f223f8faacb2`; block size 4096.
Current byte reads confirm primary GPT/entry-array CRCs and these identifiers.
Feature masks `0x3c/0x2c6/0x46b` are supported in upstream 1.47.4 source;
runtime binary/device compatibility remains UNVERIFIED until actually exercised.

After B2 approval and gates, use the existing safety review's direct clonefile
procedure, revalidating paths/no symlink redirection. New private destination:

```text
/Users/thedeepakreddy/SYNTRA/.syntra/phase10-offline-assessment/<new-timestamp>/datadisk.analysis.raw
```

No destination reuse, hard link, materialized copy, partition extraction or
fallback. Verify distinct inode, exact size and full source/clone hashes.

```sh
hdiutil attach -imagekey diskimage-class=CRawDiskImage -readonly -nomount -noautofsck -plist "$ANALYSIS_IMAGE"
```

Resolve the returned whole device and Linux partition 1 from this successful
attachment plist. Record `hdiutil info -plist`, `diskutil info/list -plist` for
those exact devices and mount inventory. Require OS `WritableMedia=false` and
effective `Writable=false`, no mounted children, verified geometry/GUID/ext4 UUID.
Never guess a `/dev/diskN` or silently switch to a different interface.
Host attachment/detachment changes device/control-plane state: B2 authorizes
those writes and new evidence writes, not original/analysis/live disk content writes.

Approved no-write assessment command proposed for B2:

```sh
env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin LC_ALL=C E2FSCK_CONFIG=/dev/null \
  /opt/homebrew/opt/e2fsprogs/sbin/e2fsck -f -n -v \
  -E nodiscard,no_inode_count_fullmap,readahead_kb=0 "$PARTITION_DEVICE"
```

Record raw stdout/stderr and exact exit bitmask, timing/tool hash and snapshot
identity. No mount, repair flags, discard, bad-block scans or journal-only run.
`-n` is not a repair and skips required journal recovery; findings may reflect
the unreplayed stopped state. Never replay to improve the result without Category C.
Detach only the returned whole device with `hdiutil detach "$WHOLE_DEVICE"`,
without force; preserve a failed detach and ask for direction. Verify disappearance,
then unchanged full hashes of original and derivative. No automatic clone deletion.

Missing read-only proof, unsupported feature/option/device behavior, new I/O,
insufficient reserve, memory-warning threshold breach, signal or incomplete
output means STOP/UNVERIFIED, never a clean result. Device-access elevation is
not blanket sudo; approve an exact resolved-device command if actually necessary.

## 7. Current-state decision, health policy and rollback

| Historical outcome | Required interpretation and minimum next step |
|---|---|
| Complete supported exit 0 | Historical consistency only. Current unresolved warning still requires a current-state decision/snapshot; do not clear it |
| Exit includes 4 / metadata findings | Uncorrected findings; skipped journal may matter. Expert analysis first; no automatic repair |
| Exit includes 8/16/128 / unsupported interface | Incomplete tool assessment; obtain a compatible-tool/environment plan, not a writable fallback |
| Signal / canceled / missing output | UNVERIFIED; preserve partial evidence and investigate resources before retry |
| Exit includes 1/2 or hash change | Contradiction of intended no-write mode; stop and investigate protection/target provenance |
| New I/O or ENOSPC | Stop affected reads/checker safely; retain evidence and ask for storage/data-safety direction |

**B3 is deliberately not executable yet:** if required after D, inventory current
activity, obtain explicit downtime approval for `colima stop default` (no force),
verify Stopped/no disk handles, and preserve both current disks/configuration/logs
using direct clonefile under a new
`.syntra/infrastructure-backups/<timestamp>-current-state/` directory. Original
historical backup stays untouched. Verify all new stopped-source/backup hashes.
Assess a separate derivative of this fresh stopped snapshot under the same
unmounted no-write controls. This preserves later execution data before any
possible corrective write. B3 needs its own final source list/capacity budget.

Proposed current-state acceptance policy: complete supported offline assessment
of the correctly identified recent stopped state, no unresolved inconsistency or
unprocessed-journal limitation, immutable evidence, and subsequent explicitly
authorized same-profile health verification without fresh storage warnings.
Any required clearing of error state, replay or repair is a separate Category C
decision, even if described as a minor metadata correction. Do not claim a
read-only check cleared on-disk flags. If these conditions cannot be met, A remains
BLOCKED. A successful boot or `recovery complete` cannot substitute for them.

Starting the VM can write/replay its journal. No second start is included in B1/B2;
any B3 restart/normal-recovery behavior must be explicitly described and approved,
including journal-replay risk under the user's Category C boundary. If authorized
repair is later justified: trial only on another disposable derivative first,
measure growth, validate data/FS/application results and provide a distinct
promotion/rollback decision. Never restore old data over current disks implicitly.

## 8. Repository remediation and test-strengthening plan

**2026-10-17 execution note:** the active status is maintained only in
`tasks/todo.md`. The pure classifier/saved-input adapter, 62 synthetic classifier
cases, 19 direct acceptance-evidence cases and all-three-planning-role read test
are now implemented. Final selected offline verification is 237 passed; scoped
static checks passed. Stronger real mission assertions are prepared but UNRUN.
Existing historical helper/evidence are unchanged. The classifier's PASSED is
only evidence eligibility, never current health or test authority; its dispatch
flag remains false and unresolved incidents require separate independent
superseding decisions. Use real trusted provenance, not hand-authored true flags,
for any future collected evidence. See the latest verification milestone and
pinned review packet; independent closure is still required.

F classifier: pure structured input/output, reason codes and matched lines;
current boot/disk identity, complete successful captures, freshness boundaries,
sticky unresolved blockers and explicit superseding records. Recognize actual
previous-mount IO failure, check-required/mounting-with-errors/e2fsck-recommended
warnings; I/O variants/case, journal abort, ENOSPC, ext4/metadata errors.
Missing/empty/truncated/stale/wrong-boot evidence fails closed. Historical clean
snapshots, API/image/rw/test success cannot erase current blockers. Do not count
unsupported/incomplete checker output as health. Decode combined exit bits.

Synthetic regressions: every actual warning, mixed success ordering, incomplete
and wrong-boot logs, prior blocker, historical-vs-current snapshot mismatch,
benign ACPI I/O mapping, unsupported checker text, exit bits 0/1/2/4/8/16/32/128
and combinations, missing read-only proof/hash mismatch; no test dispatch on
BLOCKED/UNVERIFIED. Preserve original `start_health.py` and both health JSONs.

G P2 improvements from separate planning reviewer Carson (no tests run):

1. Parse authoritative execution results: configured baseline fails, new zero
   regression fails for the intended assertion, real fix follows, full/QA commands
   pass without timeouts; validate event order and captured source/test diff.
2. Persisted rejection -> FailureAnalysis -> second implementation -> changed
   patch hash -> fresh QA/code/security invocations bound to that patch/attempt.
   Existing boolean rework adds coverage for already-strict behavior, not a second
   demonstrated production bug repair; describe it accurately.
3. Add valid persisted-review fixtures and negative stale-patch/wrong-attempt/
   missing-reviewer/mixed-author groups; exercise scheduler and service validation.
4. Bind final integration artifact bytes/hash, final result/reviewer set and
   consumed human approval to the authoritative completed attempt.
5. Verify compatible manifest/base/patch digests and exact commands; conflict must
   also block service/graph delivery, not merely fail direct patch application.
6. Cancellation barriers after final review/before publication and during delivery
   approval: persistent CANCELLED, stale approval unconsumed, scoped cleanup,
   settlement once. Duplicate dispatch must not add results/artifacts or spend.

Likely edit sets are existing mission_live/worker_live/independent_qa tests;
application changes only for legitimate reproduced defects. No assertion weakening.

## 9. Functional scope, actual test order and live-provider policy

Ten registered roles are visible in `src/syntra/agents/operational.py`:
PM, Architect, EM, Backend, target Frontend, QA, DevOps, Code Reviewer, Security
Reviewer, Debugger. All require registry/skill/tool/schema/runtime/budget/provenance
checks. Historical real effects cover PM inspection, Backend, QA, review and
bounded debugging with deterministic provider decisions; not all-ten live autonomy.

Required role-specific follow-ups:

- PM/Architect/EM: source uses the same read-only planning snapshot path, but
  actual Architect/EM reads are not proven. Add role-specific tool-call traces and
  typed artifact/input assertions in both pure lifecycle and real Docker cases.
- Frontend: original section 9 requires source changes and supported-sandbox
  build/test output, and explicitly permits reporting missing dependencies rather
  than weakening networking. Plan a preloaded isolated target fixture/toolchain;
  do not build SYNTRA UI. Until safe tooling exists: BLOCKED/UNVERIFIED, not waived.
- DevOps: actual configuration/artifact validation required; determine any image
  build requirement from accepted task criteria. No host Docker socket. Separate
  trusted build-service/toolchain approval if needed; no image-tag replacement.
- Dependencies: original section 21 explicitly requires prerequisite verification
  blocking; arbitrary predecessor-patch preload is not explicitly assigned to a
  later phase. No approved deferral found. Trace scheduler/spec/worktree paths and
  document required bounded semantics before implementation: topological order,
  exact approved predecessor attempt/patch provenance, shared base, conflict and
  stale-plan rejection, reviewed candidate binding. Do not claim general support.
- Large object storage/full CVE scanners/Phase 12 verifier remain disclosed limits;
  do not silently expand into later phases or call missing mandatory behavior done.

After A passes and new disposable test resources are authorized:

```sh
uv run pytest tests/test_phase10_agents.py tests/test_phase10_runtime.py tests/test_phase10_worker.py tests/test_phase10_billing.py tests/test_phase10_independent_qa.py tests/test_phase10_planning.py -q --tb=short
uv run pytest tests/test_phase10_mission_live.py tests/test_phase10_worker_live.py tests/test_phase10_sandbox_security_live.py tests/test_sandbox_phase9.py -q --tb=short
uv run pytest tests/test_orchestration_phase7.py tests/test_scheduling_phase8.py -q --tb=short
uv run pytest -q --tb=short
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

Paths exist now; new classifier tests join the suite after implementation.
Use the existing environment without uv sync/upgrades; prohibit unintended live
provider opt-in when running deterministic selections/full suite. Never silently
enable scenario 13. Keep actual supported skips and acceptance impact explicit.
Run manual scripts individually as `uv run python scripts/manual_tests/phase_10/<filename>`
for all 13 existing filenames in the guide; 13 only with separate provider approval.

DB must be explicitly test-named `SYNTRA_TEST_POSTGRES_URL`; fixture creates/drops
only its UUID schema. Redis uses owned stream keys; Docker/worktrees only new
test-owned resources. Neither existing container nor images/volumes is cleanup scope.

K policy: original sections 17, 33 and DoD 25 explicitly make live Gemini opt-in
and require accurate unavailable labeling. Thus absence of live evidence is not
itself an invented waiver of a mandatory live-run gate. Mandatory non-live gates
still must pass. Credential presence is not authentication success. Current
Google documentation retains 2.5 Pro/Flash but limits availability to prior users;
account eligibility is UNVERIFIED. Retired 2.0 Flash Lite is disabled in the
registry. Do not switch paid models or claim availability without review.
See [official lifecycle policy](https://ai.google.dev/gemini-api/docs/deprecations).

## 10. Independent audit, evidence contract and final requirements

After changes/tests, use a fresh reviewer invocation to inspect actual diffs and
new outputs, not implementer summaries alone. Reproduce every historical P1 and
the new classifier/P2 cases within appropriate safe test scopes. Report reviewer
identity, same-provider limitation, command evidence and unresolved risks.
Carson's current six-item review is planning input only; no final sign-off exists.

Every execution record must contain exact argv/cwd/start/end/duration/exit,
execution mode, safe environment identity, complete stdout/stderr, counts/skips,
artifacts, SHA-256 and failure classification. Do not log secret values or
credential-bearing URLs. Preserve partial/canceled logs. New command logs and
assessments go to unique directories; no rewrite of earlier result files.

Initial traceability: original master request section 39. Detailed final matrix
must add actual implementation/test/reviewer evidence and limitations for each.
No row below is a fresh runtime pass claim.

| ID | Requirement | Evidence owner / final prerequisite | Current acceptance status |
|---|---|---|---|
| D01 | Ten roles registered | operational registry / G | UNVERIFIED fresh, historical deterministic coverage |
| D02 | Meaningful executable implementations | all ten roles, target build limits / G | BLOCKED for unverified role effects |
| D03 | Role skills | registry + SkillsRegistry / G | UNVERIFIED fresh |
| D04 | Tool permissions | sandbox_gateway + grant policy / G,J | UNVERIFIED fresh |
| D05 | Real ModelRuntime path | SpecialistAgent/runtime / G | UNVERIFIED fresh |
| D06 | Structured contracts | operational/schemas/handoffs / G | UNVERIFIED fresh |
| D07 | Real artifacts | artifact_store/handoffs / G | BLOCKED fresh live evidence |
| D08 | LangGraph handoffs | engineering_service/graphs / G | BLOCKED fresh live evidence |
| D09 | Deterministic scheduler | scheduling/consumer / G,H | BLOCKED fresh live evidence |
| D10 | Leases/fencing | scheduler/reconciler / G,H | BLOCKED fresh live evidence |
| D11 | Isolated coding tools | sandbox/provider/tool bridge / G,J | BLOCKED fresh live evidence |
| D12 | Real source diff | worker/worktree / G | BLOCKED fresh live evidence |
| D13 | Real modified-repository tests | mission fixtures / G | BLOCKED fresh live evidence |
| D14 | No self-certification | persisted exact-patch reviews / G,J | UNVERIFIED strengthened assertions |
| D15 | Bounded debugging/rework | worker + P2 chain / G | UNVERIFIED strengthened assertions |
| D16 | Human approvals enforced | approval/mission boundaries / G,J | UNVERIFIED fresh |
| D17 | Budgets enforced | runtime + settlement / G,H,J | UNVERIFIED fresh |
| D18 | Duplicate effects barred | start CAS/outbox/reconciliation / G,H | UNVERIFIED fresh |
| D19 | End-to-end fixture passes | existing accepted/rework/integration fixtures / G | BLOCKED |
| D20 | Relevant full suite passes | H; last completed full run failed | FAILED historical, BLOCKED fresh |
| D21 | Supported manuals pass | I; credential blocker separate | BLOCKED fresh |
| D22 | Ruff/mypy pass | H; historical results not reused | BLOCKED fresh |
| D23 | No SYNTRA UI | scope/diff review / J,L | PASSED inspection; preserve invariant |
| D24 | No GitHub push | local-only operations / L | PASSED this campaign; preserve invariant |
| D25 | Label unverified Gemini | K/report mode separation / L | PASSED labeling; live UNVERIFIED |
| D26 | No unresolved critical/high defects | health-classifier P1 + final audit / F,J,L | FAILED current open P1 |

Final report must cover requested A–T sections, agent capability classifications,
per-scenario outputs, incident/recovery chronology, exact Git state and requirement
IDs. Allowed final verdict is PASSED only after all mandatory gates pass;
otherwise REQUIRES_WORK/BLOCKED/UNVERIFIED with evidence. No fabricated percentage.

Proposed local commit grouping, **not authorization to commit**: (1) plan/evidence
documentation; (2) classifier + pure regressions; (3) workflow test strengthening;
(4) separately justified application fixes; (5) final audit/acceptance/handover.
Preserve the pre-existing dirty implementation. No reset/clean/checkout/push.

## 11. Consolidated approval requests and stop rules

- **B1 tooling:** explicitly choose dry-run only, or dry-run plus conditional exact
  installation. If both are approved, present actual dry-run output before the
  installation stage and proceed only with identical reviewed selection, checksum,
  dependencies and passing separate resource gates. No redundant routine prompts.
- **B2 historical assessment:** may be approved together with B1, but cannot run
  until C passes and the stricter filesystem resource gate passes. Includes one
  derivative clone, read-only unmounted attachment, exact no-write invocation,
  nonforced detach, pre/post hashes and new evidence. No live filesystem changes.
- **B3 current-state snapshot/start:** request only after historical findings and
  exact current targets/downtime are known. Earlier restart permission is consumed.
- **Category C remains separate:** journal replay/repair, restore/promotion/reset,
  removal/prune/forced shutdown, paid model calls, publication or changed security.
  No Category B approval implies any of these actions.
- **Repository work:** section 11 authorizes classifier remediation and synthetic
  tests in the normal workspace; section 15 requests P2 strengthening. This initial
  checkpoint delivers the plan first. No additional general Phase 10 prompt is
  needed to continue routine scoped implementation after plan review.

Stop the affected operation on failed resources, unexpected writes/hash changes,
wrong identity, missing protection, storage errors or ungranted privileges.
Preserve partial evidence; safely stop only newly authorized process groups,
never existing user applications/VM services. Do not force detach, restart,
prune, repair or restore as an automatic workaround. Continue independent safe
source/documentation work while an infrastructure branch is blocked.

No install/dry-run/checker/clone/attachment/stop/restart/repair/test or model call
has been performed in this initial planning stage. Only new reports/evidence and
append-only task-plan updates are written. Stop at the Phase 10 boundary.

## 12. Final preflight disposition — 01:46:31 CEST

The later confirmation supersedes the earlier host-resource observations only:
five samples from 01:44:27 to 01:46:31, spanning **124.039 seconds**, all NORMAL,
proxy headroom **1.692–1.810 GiB**, swap used **2963 MiB** throughout and zero
additional swap-outs. Final `df`: **14,766,559,232 bytes**; APFS:
**14,766,546,944 bytes**. Conservative availability:
**14.766547 GB / 13.752419 GiB**. Operating reserve is above 5 GiB.

| Gate | Disposition |
|---|---|
| Dry-run host-resource prerequisites | PASSED in this confirmation window; recheck immediately before execution |
| Installation host-resource thresholds | PASSED measurements; complete installation gate BLOCKED on actual dry-run/approval |
| Historical assessment host-resource thresholds | PASSED in this window; operation BLOCKED on tooling/approval/device controls |
| Filesystem/current-state health | BLOCKED_FILESYSTEM_CHECK_REQUIRED, unchanged |
| Full/static/manual verification and final release audit | BLOCKED; not run in this planning checkpoint |

No approval was inferred from improved measurements. B1/B2 may now be considered
as conditional consolidated approval envelopes; B3 and Category C remain distinct.
See `resource-confirmation.json`, `infrastructure-inventory.json`,
`package-metadata.json`, `homebrew-version.txt`, `homebrew-help.txt` and
`planning-review-carson.md` in the new campaign directory. No dry-run result,
installation success, filesystem assessment or fresh application-test pass exists.

## 13. Authorized B1 execution — completed 2026-10-16

The user explicitly approved Option 2 (dry-run plus conditional exact bottle
installation), then resumed the same B1 campaign hours later. This supersedes
the **B1 authorization/tooling status only**, not any filesystem or Phase 10
acceptance result. B2/B3 and Category C remain unapproved.

**B1: PASSED.** Homebrew dry-run exit 0 twice selected only e2fsprogs 1.47.4.
The downloaded ARM64 Tahoe bottle matched approved SHA-256
`f8024861ae8b5a645374d7960a5b5e3c41576c792712925d55deb186a74a1d06`.
The controlled installation at 12:31:43–12:31:45 CEST exited 0 and poured that
bottle only, without source compilation, dependency upgrades, automatic cleanup
or post-install steps. All 49 old receipt hashes and unrelated prefix links are
unchanged. No old keg removed; only e2fsprogs added. Homebrew Git HEAD unchanged.

Initial resource observation: five NORMAL samples over 124.749 seconds, minimum
headroom 1.843 GiB, zero additional swap-outs. Because the continuation occurred
hours later, official metadata, the package preview and resources were refreshed.
Fresh installation window: five stable WARNING/noncritical samples over 124.799
seconds, minimum headroom 1.629 GiB, >=11.454 GiB capacity, zero new swap-outs.
This passes the unchanged **separate B1** gate, not the stricter B2 NORMAL gate.
Installation samples then became NORMAL, >=1.782 GiB headroom, no swap-out growth.

Last B1 measurement at 12:33:40 CEST: `df` and `diskutil` both report
**12,368,957,440 bytes = 12.368957 GB / 11.519489 GiB**; pressure NORMAL;
proxy headroom 1.792 GiB; swap used 3,188.25 MiB, swap-out counter 3,105,129
unchanged throughout resumed provisioning. Operating reserve remains >5 GiB.
No resource result grants B2 authority; recheck its strict gate before any action.

Installed binary `/opt/homebrew/Cellar/e2fsprogs/1.47.4/sbin/e2fsck`, opt alias
`/opt/homebrew/opt/e2fsprogs/sbin/e2fsck`, Mach-O arm64. Version-only `-V` exit 0
reports e2fsck/EXT2FS 1.47.4. Installed SHA-256:
`40dd92042872a4f39c1954a3588a77c08ef05c8e05898172058ff4407e8c2f60`.
Library closure resolves to existing/bundled ARM64 libraries and system dyld.
All 142 regular payload files are accounted for: 105 identical; 28 with identical
file-backed Mach-O sections, exact path substitutions and valid signatures;
eight exact text relocations; one SBOM with only verified installation metadata
changes; all six archive hard-link relationships intact. Keg allocation 8,032 KiB,
compressed bottle 2,465,453 bytes; ancillary
metadata/evidence separate. Configuration intentionally remains staged in `.bottle`
under `--skip-post-install`; no global PATH/configuration changes.

New evidence:
`.syntra/phase10-evidence/20261016T015443+0200-b1-provisioning/`.
Full result and staged ready-for-approval B2 procedure:
[B1 provisioning report](phase-10-b1-provisioning-2026-10-16.md).
Original backup manifest hashes still match; full original disk rehash is a B2
pre-use requirement, not claimed performed in B1. Original reports/logs unchanged.

Next: request explicit **B2** permission for one direct historical APFS analysis
clone, read-only unmounted attachment, exact `-f -n -v`/bounded-memory no-write
assessment, nonforced detach and unchanged pre/post original/clone hashes, all
conditional on strict resources and verified identity/read-only safeguards.
Native device compatibility/access remains UNVERIFIED until that authorized step.
No filesystem checker targeted a filesystem; no Colima lifecycle, Docker changes,
infrastructure tests, paid model calls or later-phase implementation occurred.
**Infrastructure: BLOCKED_FILESYSTEM_CHECK_REQUIRED. Phase 10: REQUIRES_WORK.**

## 14. Authorized B2 completion — historical inconsistencies, no repair

Explicit user B2 authorization allowed exactly one historical direct clone,
read-only/unmounted attachment, one no-write assessment and exact-device safe
detach/post-integrity. All prerequisites and protective controls **PASSED**.
The historical filesystem was **NOT CLEAN**:
**FILESYSTEM_INCONSISTENCIES_DETECTED**, native **exit bitmask 4**, errors left
uncorrected. B2 completed; no second clone/check or further recovery is implied.

Five NORMAL-pressure samples over 124.798 seconds, >=2.038 GiB proxy headroom,
flat swap-outs and >8 GiB capacity passed preflight. All 15 original preserved
files fully rehashed successfully before and after. Both manifest hashes match.
Original live-source metadata was recorded, not its current contents assessed.

Exactly one direct clonefile at 15:42:03 CEST created the private derivative
`.syntra/phase10-offline-assessment/20261016T153334+0200/datadisk.analysis.raw`.
Original inode 97698031, derivative inode 97738504, same filesystem,
107,374,182,400 logical bytes. Before/after original and clone hashes all match
`9de7d661f8d4c4a7fce36ad6a54f74d235df57e0d6328da080a8aa3aaf2b12dd`.
No full-copy fallback; clone preserved, not deleted.

Actual attach response returned `/dev/disk4` and `/dev/disk4s1` (not guessed).
GPT CRCs, partition offset 1,048,576/length 107,372,085,248, partition GUID,
ext4 UUID `3de9071f-0361-4f65-88a3-f223f8faacb2`, block size/features all match.
Whole and partition `WritableMedia=false`, `Writable=false`, no mounted children;
normal UID 501 device reads succeeded, no sudo/device permission changes.

One 1.47.4 native `-f -n -v -E nodiscard,no_inode_count_fullmap,readahead_kb=0`
invocation under clean configuration ran at 15:45:02 CEST. All five passes
completed; **journal recovery explicitly skipped**. Findings: unconnected inode
2097183 under Docker overlayfs, incorrect parent/reference count, block bitmap
difference +8396851, group 256/global free-block count disagreement and bitmap
checksum mismatch. All corrections declined. No unsupported/I/O/storage errors,
attempted-write warning, timeout or resource interruption. Native exit 4 is not
the observer's exit 0 and not evidence of correction or a clean filesystem.

Exact new device detached without force; independent follow-up confirmed no
analysis attachment or device nodes. Full post-integrity ended 15:48:31 CEST.
Across 66 monitored stage samples, all NORMAL, >=1.956 GiB headroom, no swap-out
growth. Final 15:49:02 sample: **12,268,552,192 bytes (12.268552 GB / 11.425980
GiB)** available, NORMAL, 1.990 GiB headroom. Same Colima profile Running;
no running containers; old protected container unchanged. No live disk, image,
volume, database, Redis, package or engineering-test mutation.

Detailed findings/19 requested report items:
[B2 completion report](phase-10-b2-assessment-2026-10-16.md).
New evidence only:
`.syntra/phase10-evidence/20261016T153334+0200-b2-assessment/`.
Earlier evidence preserved. **Procedure PASSED; historical cleanliness FAILED;
current integrity UNVERIFIED; infrastructure BLOCKED; Phase 10 REQUIRES_WORK.**

Next decision requires separate **B3** current-state interruption/preservation/
assessment approval after exact activity/targets/clone-count/capacity planning.
Any journal replay, repair, promotion/restore/replacement or start that could
replay is a distinct **Category C** write approval. Historical unreplayed errors
alone neither prove current corruption nor justify repair. No infrastructure
tests, provider calls or later phases are resumed. Stop after this B2 report.
