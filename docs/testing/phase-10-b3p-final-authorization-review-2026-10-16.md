# SYNTRA Phase 10 — final B3-P authorization review

2026-10-16, Europe/Budapest. **REVIEW ONLY; B3-P NOT AUTHORIZED.**
Infrastructure: **BLOCKED_FILESYSTEM_CHECK_REQUIRED**.
Phase 10: **PHASE_10_REQUIRES_WORK**.

This review refines the proposed authorization envelope in B3-Q section 8.
It does not rewrite that historical report or grant execution authority.
Recommendation: **split preservation and assessment at explicit checkpoints**.
Request only **B3-P-A host/native preservation** next, conditional on capacity
and a verified producer hold. VM shutdown/preservation (P-B) and assessment (P-C)
remain separately approved later stages. No lifecycle, backup, clone, attach,
mount, checker, replay, repair, restart or infrastructure test occurred here.

## 1. Fresh observations and readiness

### P-A-HEADLESS-1 preparation authorized; execution withheld — 2026-10-17

The user explicitly approved preparation after another memory failure, without
an unreviewed launch. Original P-A / 8 GiB / HOLD-1 approvals remain recorded.
Do not request them again or treat preparation as P-B/P-C authority.

The 03:19:52 WARNING sample stopped immediately. Following a materially changed
NORMAL/2.247 GiB observation, one bounded five-sample window PASSED over
124.803s, 04:17:18–04:19:22: NORMAL throughout, 2.253–2.297 GiB headroom, no new
swap-outs, final 13,080,653,824 bytes / 12.182308197 GiB available. All 15
historical backup full hashes/identities, manifest anchor, 82 retained indexed
evidence entries, Git fsck/HEAD and five pinned engineering files verified.
This does not certify the current ext4 filesystem or establish a producer hold.

Helper modules and offline guard cases are prepared in
`.syntra/phase10-evidence/20261017T032017+0200-pa-headless-preparation/`.
Initial independent helper review REQUEST_CHANGES and its nested-timeout follow-up
were corrected. Final independent code safety review is APPROVED_WITH_OPERATIONAL_BLOCKERS,
with no required code findings remaining. A final hash-bound review receipt and
exact Terminal handoff are issued; no helper main/dump/clone has run. The documented
resource/hold/backup guards remain unchanged or stricter, never weakened.
The user explicitly confirmed no SYNTRA access for Python PID36936 (Echo/SearxNG
cwd, localhost8888) and continued inactivity of an OpenClaw gateway whose user
plist can restart it if loaded. Its exact launchctl job query currently returns
113/not loaded; no assertion of active SYNTRA work or stop authority is made.

See HANDOFF.md there for the reviewed exact manual Terminal command/checksums.
No further scope clarification or repeated P-A approval is requested. The
remaining manual step is saving/quitting Codex and launching independently;
the helper still requires fresh exact-state/native/file/host stability and
operation-time resources before conditional P-A, then STOP A. No broad replanning.

### P-A-HEADLESS-1 — ONE narrow alternative, proposed 2026-10-17 03:14 CEST

**PROPOSED / NOT APPROVED / NOT EXECUTED.** This adds only an independent
Terminal execution handoff; it does not amend the approved resource thresholds,
backup scope, P-A-HOLD-1 or P-B/P-C gates. Existing P-A approvals remain valid
conditionally and must not be requested again.

Reason: the single requested resource recheck failed immediately at 03:11:15
(WARNING, 1.405944824 GiB headroom), despite 13.937629700 GiB storage passing.
Do not repeat this failed window without a meaningful resource change.
Read-only hashing of the measured 12,339,191-byte/2,138-file host set used a
256 KiB read buffer and peaked at 23.609375 MiB RSS. pg_dump/pg_restore version
startup peaked at 6.609375/6.59375 MiB, respectively; real dump/compression,
archive inspection, backend, clone/kernel and COW peaks remain UNVERIFIED.
Catalog reads show small application relations (974,848 dev / 5,595,136 test
bytes including indexes/TOAST), no large objects and zero other DB sessions at
the sampled instants, but do not bound actual dump memory. The existing RDB is
11,800 bytes and needs no new Redis fork or persistence trigger.
The Codex renderer alone was about 1.3205 GiB RSS; that is not unique/reclaimable
memory. Removing the interactive app workload may help; success is not assumed.

Requested sequence, only after this handoff is approved:

1. Prepare and review a one-shot P-A controller reusing the existing approved
   collectors/procedure. Provide its final exact Terminal command and hash
   before launch. No executable preservation helper exists yet; do not invent
   a ready command. Evidence here contains read-only diagnostics only.
2. User saves work and manually exits Codex, then launches the reviewed helper
   from an independent Terminal. Do not launch a detached Codex child, install
   a background service, kill arbitrary processes or alter OS configuration.
   Leave Colima, native PostgreSQL and Redis running; maintain the confirmed
   cooperative maintenance hold. Those services currently have parent PID1,
   not Codex, but must still be verified running before preservation.
3. The helper qualifies one fresh >=120-second window, >=3 samples: sustained
   NORMAL, >=1.5 GiB conservative headroom, no sustained swap-out growth,
   >=8 GiB storage. A failed sample stops the run, with no automatic wait/retry
   loop. Keep the 5 GiB operating reserve and stop at <=6 GiB free, deteriorating
   memory, unexpected allocation or any other existing stop condition.
4. Verify exact approved durable identifiers/states, no actual execution/live
   ownership/dispatch/consumption/reconciliation/conflicting writers, and the
   required >=120-second native/source/Git/artifact stability. Preserve exact
   pre-backup state. Any drift stops; record provenance uncertainty unchanged.
5. Execute only the original P-A scope sequentially: direct same-volume
   clonefile where approved (no full-copy fallback), separate dev/test custom
   dumps capped at 128 MiB EACH, stable complete existing RDB, source/Git/
   configuration/evidence preservation. No Redis SAVE/BGSAVE or new snapshot,
   no VM disk operation. Keep 0.5 GiB task allocation and 32 MiB new log/manifest
   ceiling; monitor resources throughout, including during hashing and dumping.
6. Verify source/destination identities, all sizes/hashes/manifests, PostgreSQL
   archive readability, and exact post-backup allowlist state. Archive listing
   is not a restoration test. Stop only the helper's new owned backup client
   on failure; retain incomplete outputs as FAILED, never auto-clean existing
   evidence. Write bulk results to private timestamped evidence, not the chat
   renderer, and display a compact terminal verdict. STOP AT CHECKPOINT A.

No hard peak-memory guarantee follows from the read profile or client startup
tests. The unchanged system gates and runtime stop policy remain decisive;
if they still fail after the app exits, no preservation is allowed. The helper
must not infer a global write fence from absent named workers. This is a
cooperative hold plus bounded fresh observations, with the exact HOLD-1 exception.

**Exact new approval requested:** approve P-A-HEADLESS-1 preparation/review and
one manually launched independent Terminal P-A run after Codex exits, retaining
every existing resource, producer-hold, scope, verification and stop safeguard.
This is NOT approval for P-B, P-C, Colima lifecycle changes, filesystem checking,
journal replay/repair, restoration, tests or new provider calls. Do not execute
the handoff until approved. Measurements/initial failed timing captures and
successful read-only recaptures are preserved under
`.syntra/phase10-evidence/20261017T031113+0200-pa-resource-alternative/`.

### P-A-HOLD-1 approval record — 2026-10-17 03:04 CEST

The human explicitly APPROVED the precise P-A-only exception below for the
unchanged allowlisted 108 INITIALIZING attempts, 314 pending outbox rows and six
pending Redis deliveries, with all fourteen current mandatory conditions.
The original proposal text below is historical, not a request for another approval.
The authoritative approval is the user's message; its bounded record is in
`.syntra/phase10-evidence/20261017T030402+0200-hold-approved-preflight/authorization.json`.
No database state or application policy code was changed. No memory/resource,
live-execution/ownership, dispatch, conflicting-writer, exact-state or stability
requirement is waived. Exact pre/post-backup durable-state evidence is mandatory;
any drift or resource failure stops execution. The exception remains P-A-only,
expires at A and grants no P-B/P-C/VM/filesystem/test authority.

The allowlist SHA matches the approved value. P-A resource qualification failed
immediately on WARNING and 1.319396973 GiB headroom. Therefore P-A did NOT begin,
and fresh current-state/stability verification remains pending after resources
qualify. Do not request the same approval again.

### Original P-A-HOLD-1 proposal — before the above approval

The original October 16 review and zero-INITIALIZING rule below remain historical
and currently authoritative; this dated proposal does not silently amend them.
The latest master directive explicitly authorizes bounded read-only record/queue
provenance diagnostics, independently of preservation eligibility. No P-A memory
threshold is changed. New evidence is separate under
`.syntra/phase10-evidence/20261017T025143+0200-durable-provenance/`.

Completed observations: two native snapshots **172.584 seconds** apart had
identical complete projections of all **108 INITIALIZING attempts** and **314
PENDING outbox rows**, including payload hashes. Both configured databases had
zero other sessions/transactions/prepared transactions and zero live leases.
All 108 attempts have zero agent-execution and sandbox-job records; 107 have
expired leases, one has no lease. 107 tasks are ASSIGNED and one is COMPLETED.
95 records match current test fixture signatures; 13 exact historical origins
remain UNVERIFIED. Signature matches are not authenticated invocation evidence.

All 314 outbox rows resolve to tasks/missions/projects (104 projects): 160
TASK_DISPATCHED, 152 TASK_COMPLETED, two TASK_FAILED. A new relay could publish
the 160 dispatch events; they must not be treated as harmless deleted work.
300 rows match fixture signatures and 14 remain unmatched. Six pending Redis
entries are about 45 hours old, retain their owners/delivery counts and complete
entry hashes, and have no matching task in either reviewed native database.
They can be transport-reclaimed by a subsequently started authorized client;
no claim/reconciliation was attempted, and other possible stores were not searched.
Do not call them globally orphaned or disposable.

No unexpected non-diagnostic Redis command growth, active consumer client,
running container or definite separate producer was observed. File commitments
were unchanged over **139.179 seconds** (459 source files, 1,282 Git entries,
343 prior evidence entries, selected native files; artifact/log/sandbox groups
empty). Host observations spanned **123.549 seconds**. The app inventory shows
only this chat active. Execution-capable current Codex/MCP runtimes remain;
this is cooperative sampled quiescence, NOT an enforced global write fence.

**Exact requested amendment, P-A ONLY:** permit the explicitly enumerated
records in `inactive-state-allowlist.json` to be preserved as
**DURABLE_INACTIVE_STATE**, rather than requiring their cancellation/deletion or
equating a stored INITIALIZING/consumer label with **ACTIVE_EXECUTION**. This
does not assert all historical test provenance is proven. The allowlist SHA-256:
`22b6461507b562acfed1b7ed6512e05aea10dff614f0f6ca79ad7a1b9097064e`.

Approval must explicitly accept the 13-attempt/14-outbox provenance limitations
and six unmatched Redis task references while preserving them unchanged.
It changes only this P-A qualification decision, not application task states,
ownership, leases, queues, retry semantics, completion criteria or retention.

Mandatory conditions remain:

1. Fresh unchanged P-A resource qualification: NORMAL >=120 seconds, >=1.5 GiB
   headroom, no sustained swap-outs, >=8 GiB entry, protected 5 GiB reserve and
   all archive/output/early-stop limits. Latest storage PASSED at
   **14,979,334,144 bytes / 13.950592041 GiB**; memory FAILED (WARNING, boundary
   headroom 1.494–1.517 GiB). Zero swap-out growth does not waive WARNING.
2. No RUNNING attempt, live lease, actual executing worker/sandbox, dispatcher,
   relay, reconciler, relevant transaction or conflicting source/artifact writer.
   Do not hide an unknown process behind the exception; identify it first.
3. Recheck exact IDs/states/payload hashes, pending ownership/delivery counts,
   write counters, source/Git/artifact stability and persistence immediately
   before P-A. Preserve sampled >=120s stability and the user's maintained hold.
   Any relevant scope/state/ownership/writer drift invalidates the exception.
4. No cancellation, ACK, reclaim, publishing, draining, reconciliation, deletion
   or data mutation. Preserve all queued/interrupted work and the complete RDB.
   No database restore proof is inferred from the eventual archive listing.
5. Expire this exception at Checkpoint A. It does not approve P-B/P-C, shutdown,
   restart, filesystem assessment/repair/replay, infrastructure tests or paid calls.

**Risks/protections:** unknown historical provenance remains visible; old work
could resume if the hold is broken. No technical barrier against an administrator
or forgotten/new writer is promised. Originals and old backups are untouched;
approval can be withdrawn before execution, and any failed gate stops P-A with
new partial evidence retained. No data rollback is needed for this policy-only
decision because no database/queue state is changed. Same-volume backups still
share APFS's physical failure domain.

**Decision requested:** approve or reject **P-A-HOLD-1** exactly as bounded above.
After approval AND resource stabilization, requalify only freshness/safety gates,
reuse the recorded provenance instead of restarting its investigation, then
perform already-approved P-A and STOP at Checkpoint A. No P-A has begun.

### Original October 16 observations (historical)

At **22:51:22 CEST**, `df` and `diskutil APFSContainerFree` both reported
**12687118336 bytes = 12.687118336 GB = 11.815799713 GiB**. The proposed
**12 GiB** preservation-entry gate therefore **FAILS** by **197783552 bytes
(188.621 MiB)**. This supersedes the earlier resource pass for current capacity.
The 8 GiB assessment threshold and 5 GiB operating floor still pass as observations.
No cleanup is authorized; obtain more margin and recheck before any preservation.

Pressure is NORMAL; headroom proxy **1.891937 GiB** at that point. Swap-outs
were unchanged between this review's two points, but increased by 24712 pages
since B3-Q hours earlier. That does not prove sustained present growth or present
stability over two minutes. A fresh >=3-sample/>=120-second strict window is
**UNVERIFIED** and remains mandatory before execution; no threshold is weakened.

Colima `default` remains Running with both disk files open. No containers are
running; the protected exited-137 container is unchanged. Fresh bounded native
reads found zero other PG connections/transactions in each relevant database;
insert/update/delete counters remain unchanged from B3-Q. Redis still reports
one non-expiring DB-0 key, no other populated DB, AOF disabled, no persistence
operation in progress and zero changes since the last successful save. These
observations do not establish the missing producer hold or filesystem health.

New review evidence only:
`/Users/thedeepakreddy/SYNTRA/.syntra/phase10-evidence/20261016T224957+0200-b3p-review/`.
Existing B1/B2/B3/B3-Q evidence and reports are retained, not repeated or replaced.

## 2. Exact producer-hold procedure and its limits

No global maintenance/write-fence was demonstrated in the inspected source.
The CLI worker loop combines reconciliation, scheduling, outbox relay, message
reclaim and execution (`src/syntra/cli/engineering.py:178`). Consumers can
reconcile/requeue (`src/syntra/scheduling/consumer.py:25`). The outbox relay can
publish already queued work independently of a new submission. Legacy session
API execution also starts background swarms (`src/syntra/api/routes/sessions.py:99`).
Mission pause is not a universal barrier: it writes mission/outbox state and
does not fence all APIs, direct CLI callers, relays, file writers or other chats.

Required hold, not yet established:

1. User declares a maintenance window covering all people, chats/agents, scripts,
   scheduled jobs and editors able to write SYNTRA or launch Colima/Docker. No
   new submissions, approvals, CLI start/advance/decide/worker commands, tests,
   background swarm requests, queue consumption or direct repository writes.
2. Inventory exact producer PIDs/listeners/supervisors. After confirming they are
   idle, their owners stop the identified SYNTRA API/worker/relay/reconciler/MCP
   execution entry points and their auto-restart/watchers. No guessed PID,
   `pkill`, launchctl bootout, database service stop or broad process termination.
   Agent-led process changes need an exact-target approval; none is granted here.
3. If any work is in flight, stop this preservation sequence for a separate
   quiescence decision. Do not cancel leases, ACK/reclaim messages, reconcile,
   run workers to drain queues or kill an active task to manufacture idleness.
4. Verify twice across >=120 seconds: no producer/listener reappearance, no
   running sandbox containers, no other relevant DB sessions/transactions, no
   active INITIALIZING/RUNNING attempts or live worker leases, no Redis consumer/
   persistence activity, unchanged relevant row-write counters, stable frozen
   source/Git/artifact manifests. Live attempt/lease checks are still required;
   this review did not infer them from empty connections.
5. Record queued/outbox state without consuming/changing it. Pending work may
   remain preserved if all dispatchers/consumers are held; it must not be purged.
6. Maintain the hold through native backups, checkpoints and later VM capture.
   If released or violated, invalidate cross-store consistency and requalify;
   do not reuse the old backups as a new current coordinated checkpoint.

This is a **cooperative hold plus observed absence of running producers**, not
a kernel-enforced write barrier. It cannot block an administrator, forgotten
remote client or newly started process. An advisory lock alone would not fence
these unmodified entry points. If guaranteed technical prevention is required,
a separately approved enforcement/isolation design is necessary; do not claim
that this procedure provides one.

The intended freeze is SYNTRA application/dispatch/artifact changes. PostgreSQL
background maintenance, guest logging and explicitly approved backup/evidence
writes still occur. Preventing *every* host/guest disk write while services and
the VM remain running is not a truthful promise. No hold was activated here.

## 3. Redis whole-instance coverage, ownership and limitations

Configured source: `/opt/homebrew/var/db/redis/dump.rdb`, **11800 bytes**,
inode **97716107**, st_dev **16777233**, owner **UID 501 (`thedeepakreddy`)**,
GID 80, mode 0644; not a symlink. Original permissions were not changed.
Fresh file SHA still matches B3-Q:

`a6a747cfc03ea60a49606a14a58d8cd6da3752b5004b70c016aeae9fd1d7f66e`.

Runtime last-save time remains **2026-10-16 01:26:21 CEST**, matching file mtime
to the second; last save status OK, no unsaved counted changes and no save/AOF/
module fork/backup in progress. The observed dataset is DB 0, one key, no TTL.
No other populated logical DB was reported; no key name/value was queried or
decoded. Hashing reads opaque file bytes; it is not application-data inspection.

Standard RDB persistence is an instance dataset snapshot, not a DB-0-filtered
export. The configured completed file can be preserved without a fresh save.
Redis documents atomic replacement of completed RDB files and live-file backup
safety: [Redis persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/).

Classifications:

- File ownership, configured identity and byte stability: **PASSED observations**.
- Standard whole-instance snapshot scope: supported by persistence semantics;
  explicit approval must cover the **entire existing file**, including any
  non-SYNTRA/shared contents. Do not label it a verified SYNTRA-only export.
- Application/key business ownership and serialized key-for-key completeness:
  **UNVERIFIED**. File ownership and one-key INFO do not prove these.
- RDB checksum/load compatibility, semantic validity and actual restoration:
  **UNVERIFIED**; no isolated restore or data inspection was performed.

At future preservation, bracket the file clone with unchanged persistence,
keyspace, source inode/mtime/size and source/destination hashes under the hold.
If unsaved changes, replacement, populated DB scope or persistence state changes,
STOP. No SAVE/BGSAVE/BACKUP/replication export/CONFIG SET fallback. Restore needs
its own isolated-environment approval, compatible Redis/modules/config/ACLs,
privacy review and no connection to production dispatchers. RDB alone is not a
server configuration/ACL backup or a transaction-consistent PG/Redis checkpoint.

## 4. PostgreSQL protection still required

Diagnostics are not backups. **Two new logical dumps are warranted and remain
unperformed**, one each for native `syntra_dev` and `syntra_test`, using their
separate existing configured roles. B3-Q measured 9600023 and 18684951 bytes;
these historical database sizes do not bound future dump output. Neither role
is superuser; the dev role's cross-database permission denial must not be bypassed.

Custom-format PG16 dumps preserve per-database consistent snapshots. Maintain
the producer hold to make sequential DB snapshots and the Redis saved state
correspond to the same unchanged application state; there is no automatic common
distributed transaction snapshot. Preserve private role/ownership mappings,
extensions/configuration and any required external objects. No live PG directory
copy, forced checkpoint, termination of connections, global privilege change or
indiscriminate password-hash export. See [PostgreSQL 16 dump guarantees](https://www.postgresql.org/docs/16/backup-dump.html).

Validate native exit, archive listing and full SHA. Archive listing does not
prove restore success; an isolated restore/constraint/application check remains
separately scoped and UNVERIFIED. Abort on missing required object privileges,
inconsistent hold, resource failure or output-size limits; retain partial files.

## 5. Shutdown and failure handling

The **90-second SIGKILL setting concerns Docker/containerd service shutdown**,
not a timer authorizing the assistant to force-kill the VM. Q observed SIGTERM,
KillMode=process, FinalKillSignal=9 and SendSIGKILL=yes for both services.

One normal command could be proposed later:
`/opt/homebrew/bin/colima stop default` — no force flag, retry or VM kill.
However stock Colima can log runtime-stop errors and continue to VM stop.
An outer observer cannot guarantee stopping that internal sequence before its
next stage. See [pinned Colima stop](https://github.com/abiosoft/colima/blob/v0.10.3/app/app.go).
Lima's VZ request has a separate 30-second wait after runtime handling; the two
timeouts are not necessarily concurrent. See [pinned VZ stop](https://github.com/lima-vm/lima/blob/v2.2.1/pkg/driver/vz/vz_driver_darwin.go).

Consequently no claim of a wholly nonforcing/graceful guarantee is possible for
that stock route. Do not change unit timeouts/signals, patch binaries or add a
force fallback. If possible daemon SIGKILL or backend teardown uncertainty is
unacceptable, P-B remains BLOCKED pending a separately reviewed alternative.
Approval of P-A does not accept those risks or authorize a stop.

After a future failed/timed-out stop:

- Stop downstream operations; record the VM's actual state, process/disk handles
  and logs. No second stop, restart, force, repair or clone of open disks.
- If still Running/unknown, retain it and the original disks as observed. A new
  stopped-state VM backup **cannot be guaranteed** in this branch.
- If disks are closed but clean shutdown is unproven, do not call them clean or
  application-consistent. Seek separate permission for a preservation-only,
  explicitly crash-consistent snapshot; no automatic continuation to assessment.
- Historical backup/evidence and newly verified P-A host/native backups remain
  protected. They are not a backup of all current Docker state and cannot
  automatically roll the live VM back. Never restore old disks over new work.

A graceful stop itself can flush/change original VM bytes before the stopped
backup exists. Exact preservation of running pre-stop bytes is a different,
unapproved design. If that residual risk is unacceptable, do not approve P-B.

## 6. Exact disk/clone/hash/storage envelope

Fresh current sources, both open by Virtualization PID 7472:

| Source | inode (st_dev 16777233) | Logical bytes | Allocated bytes |
|---|---:|---:|---:|
| `/Users/thedeepakreddy/.colima/_lima/colima/disk` | 97406017 | 21474836480 | 1496170496 |
| `/Users/thedeepakreddy/.colima/_lima/_disks/colima/datadisk` | 97405962 | 107374182400 | 598310912 |

**Current content SHA values are UNKNOWN until a verified stopped/no-writer
state.** Historical B2 SHA values must not be substituted or required to match
legitimate later writes. Compute SHA256(stopped boot)=SHA256(new boot backup),
and SHA256(stopped data)=SHA256(new data backup)=SHA256(new analysis before/after).
Use full logical-stream, bounded-buffer hashes; hash command success alone is
not equality. Revalidate source stability and no-writer protection throughout.

New immutable roots, bound to unique literal run IDs only after approval:

- P-A: `.syntra/infrastructure-backups/<RUN>-host-native/`.
- P-B: `.syntra/infrastructure-backups/<RUN>-vm-current/`, separate from the
  already verified P-A backup; no insertion into an immutable old backup.
- P-C: `.syntra/phase10-offline-assessment/<RUN>-current-state/`.
- Every stage: a new private timestamped evidence directory.

Two VM-disk direct clonefile operations in P-B, and one in P-C. At most one
attempt for each source/destination pair; abort first failure. P-A's enumerated
host/RDB file clones are additional small-file operations, not VM snapshots.
No hard links, `cp -c`, materialized fallback, disk extraction or replacement.
Require new absent destinations, same APFS filesystem, private parents, no
symlink ancestry, correct owner/source identities and distinct destination inodes.

Retain >=12 GiB before preservation and again after native exports/before stop;
fresh NORMAL >=120-second memory window, >=1.5 GiB headroom and no sustained
swap-out growth. Require >=8 GiB before stopped clones/attach/check and >=5 GiB
throughout, with early interruption of newly owned work before reserve threat.
The 12 GiB allowance comprises 5 GiB operating floor, 4 GiB shutdown/COW
contingency, 1.5 GiB analysis/evidence, 0.5 GiB bounded host/native output and
1 GiB slack. It is not an upper bound or reservation. The current gate fails.

VM copies represent 120 GiB logical plus a 100 GiB logical derivative; APFS
shares extents but worst-case later COW can approach those logical sizes. Do not
budget a writable repair derivative under this no-write plan. Up to 440 GiB of
logical hash input can be needed for the original full comparison plus derivative
post-hash, and additional repeated source verification can add more. No full
copy fits current capacity. Same-device clones are not independent SSD-failure
protection; an external-device transfer needs its own capacity/method approval.

## 7. Exact proposed command set and checkpoints — NOT EXECUTED

Variables below are new approved absolute destinations, not existing backup
paths. Roles/passwords are resolved privately from the correct configured DB
credential; no URL/password is placed in argv or evidence. All commands are
supervised gated steps, not a paste-and-run unattended sequence. Exclusive
destination creation and a reviewed file manifest precede any writing command.

### P-A — producer hold and host/native preservation only

User first establishes the hold described above. No blanket process-stop
permission is requested. Enumerate/freeze source, uncommitted/untracked work,
necessary ignored configuration, full Git/worktree dependencies, artifacts/logs,
closed legacy SQLite and approved native configuration. Exclude existing VM
backup/analysis trees from duplication, not deletion. New private output only.

```sh
/bin/df -k /Users/thedeepakreddy/SYNTRA
/usr/sbin/diskutil info -plist /System/Volumes/Data
/usr/sbin/sysctl kern.memorystatus_vm_pressure_level vm.swapusage
/usr/bin/vm_stat
/opt/homebrew/bin/colima list --json
/opt/homebrew/bin/docker --context colima ps -a --no-trunc

PGCONNECT_TIMEOUT=5 PGPASSFILE=/dev/null PGUSER="$B3P_DEV_ROLE" /opt/homebrew/opt/postgresql@16/bin/pg_dump --no-password --host=localhost --port=5432 --dbname=syntra_dev --format=custom --lock-wait-timeout=5s --file="$B3P_NATIVE/native/postgres/syntra_dev.dump"
PGCONNECT_TIMEOUT=5 PGPASSFILE=/dev/null PGUSER="$B3P_TEST_ROLE" /opt/homebrew/opt/postgresql@16/bin/pg_dump --no-password --host=localhost --port=5432 --dbname=syntra_test --format=custom --lock-wait-timeout=5s --file="$B3P_NATIVE/native/postgres/syntra_test.dump"
/opt/homebrew/opt/postgresql@16/bin/pg_restore --list "$B3P_NATIVE/native/postgres/syntra_dev.dump"
/opt/homebrew/opt/postgresql@16/bin/pg_restore --list "$B3P_NATIVE/native/postgres/syntra_test.dump"

/opt/homebrew/opt/redis/bin/redis-cli -h localhost -p 6379 INFO persistence
/opt/homebrew/opt/redis/bin/redis-cli -h localhost -p 6379 INFO keyspace
```

The native backup includes the entire configured stable RDB using the direct
clone primitive below with source `/opt/homebrew/var/db/redis/dump.rdb` and
destination `$B3P_NATIVE/native/redis/dump.rdb`. Recheck INFO and hashes afterward;
no Redis save/export/restore. Hash dumps, source/Git/config artifacts and
manifests; verify all expected files and preserve the sealed P-A result.
**STOP at checkpoint A for human review before any VM shutdown.**

### P-B — separately approved one normal stop and stopped VM preservation

Only after accepted checkpoint A, continued hold, fresh resources and explicit
shutdown-risk acceptance. Capture exact output and warnings; no forced retry.

```sh
/opt/homebrew/bin/colima stop default
/opt/homebrew/bin/colima list --json
/usr/sbin/lsof -nP /Users/thedeepakreddy/.colima/_lima/colima/disk /Users/thedeepakreddy/.colima/_lima/_disks/colima/datadisk
```

Only if clean/acceptable shutdown evidence, Stopped state, no open writers,
stable source identities, no restart supervisor and valid resources all pass,
use direct clonefile for these two exact pairs:

1. Current boot path above -> `$B3P_VM/vm/disk`.
2. Current data path above -> `$B3P_VM/data/datadisk`.

Preserve enumerated profile/generated Lima configuration, EFI/boot identifiers,
regular logs and any required backing files. Compare full source/backup hashes
and seal a new verified manifest. Do not attach an original disk.
**STOP at checkpoint B, VM Stopped; do not start assessment automatically.**

### Direct clone primitive for individually approved pairs

Invoke this proposed command individually with `B3P_SOURCE`/`B3P_DESTINATION`
bound to one approved pair. Private destination parents must already exist in
the new approved root. It does not replace stopped/no-writer/resource gates:

```sh
/Users/thedeepakreddy/SYNTRA/.venv/bin/python -B - "$B3P_SOURCE" "$B3P_DESTINATION" <<'PY'
import ctypes, os, stat, sys
from pathlib import Path
s, d = map(Path, sys.argv[1:])
if not s.is_absolute() or not d.is_absolute():
    raise SystemExit('STOP: absolute paths required')
if any(p.is_symlink() for p in (s, *s.parents, d.parent, *d.parent.parents)):
    raise SystemExit('STOP: symlink component')
if os.path.lexists(d):
    raise SystemExit('STOP: existing destination')
a, parent = s.lstat(), d.parent.stat()
if not stat.S_ISREG(a.st_mode) or a.st_uid != os.getuid():
    raise SystemExit('STOP: invalid source')
if parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) != 0o700:
    raise SystemExit('STOP: nonprivate destination parent')
if a.st_dev != parent.st_dev:
    raise SystemExit('STOP: cross-filesystem clone forbidden')
lib = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
lib.clonefile.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
lib.clonefile.restype = ctypes.c_int
if lib.clonefile(os.fsencode(s), os.fsencode(d), 0):
    error = ctypes.get_errno()
    raise OSError(error, os.strerror(error))
b, c = s.lstat(), d.lstat()
if (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns) != (b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns):
    raise SystemExit('STOP: source changed')
if c.st_dev != a.st_dev or c.st_ino == a.st_ino or c.st_size != a.st_size:
    raise SystemExit('STOP: clone identity/size mismatch')
print('Clone created; full hash verification still required')
PY
```

No fallback exists. Keep originals unchanged; set private permissions on new
outputs only. Full source/destination hashes are mandatory, for example:

```sh
/usr/bin/shasum -a 256 "$B3P_SOURCE" "$B3P_DESTINATION"
```

For large VM images, use the reviewed streaming/F_NOCACHE hashing procedure
with resource monitoring from the canonical B3 plan rather than unbounded cache
pressure or parallel hash jobs. Record and compare digest values, not exit alone.

### P-C — separately approved current derivative/no-write assessment

One clone from `$B3P_VM/data/datadisk` ->
`$B3P_ANALYSIS/datadisk.analysis.raw`, followed by full equality verification.

```sh
/usr/bin/hdiutil attach -imagekey diskimage-class=CRawDiskImage -readonly -nomount -noautofsck -plist "$B3P_ANALYSIS/datadisk.analysis.raw"
/usr/sbin/diskutil info -plist "$B3P_WHOLE_DEVICE"
/usr/sbin/diskutil info -plist "$B3P_PARTITION_DEVICE"
/usr/sbin/diskutil list -plist "$B3P_WHOLE_DEVICE"
/usr/bin/hdiutil info -plist
/sbin/mount

env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin LC_ALL=C E2FSCK_CONFIG=/dev/null \
  /opt/homebrew/Cellar/e2fsprogs/1.47.4/sbin/e2fsck -f -n -v \
  -E nodiscard,no_inode_count_fullmap,readahead_kb=0 "$B3P_PARTITION_DEVICE"

/usr/bin/hdiutil detach "$B3P_WHOLE_DEVICE"
/usr/bin/hdiutil info -plist
```

Devices come solely from that attachment's successful plist, never a guessed
disk number. Verify image mapping, partition geometry/GUID/ext4 UUID/features,
OS Writable=false and WritableMedia=false, no mounted child, and exact trusted
binary SHA before the single checker invocation. Missing proof means STOP.
Capture native checker exit independently of observer exit, complete output,
all passes/journal limitations, resources, exact-device nonforced detach and
unchanged full post hashes. No reattachment/retry or weaker protection fallback.
Leave VM Stopped, retain derivative/evidence, and report without clearing health
merely from Docker readiness or a historical check.

## 8. Final authorization request and retained exclusions

**Request B3-P-A ONLY, conditional on restored capacity, fresh memory qualification
and the user's established/verified producer hold:** create and verify the new
private host/Git/config/evidence/legacy SQLite and database-local PG backups,
plus a byte-identical clone of the entire existing stable Redis RDB. No new
Redis persistence, key inspection, service termination, VM lifecycle, VM-disk
clone, attachment or assessment. Stop at checkpoint A and present the verified
manifest, actual sizes/hashes, consistency limitations and renewed resource gate.

This is the recommended replacement for approving Q section 8's entire combined
P1–P5 sequence. P-B needs a distinct later approval after checkpoint A, including
explicit acceptance of normal service-escalation/backend failure risk. P-C needs
another approval after the current VM backup actually verifies. No phase is
automatically activated by successful prior diagnostics or checkpoint results.

If the cooperative hold or whole-instance Redis coverage is unacceptable, do
not approve P-A: resolve scope/enforcement first. If a fresh VM backup *before*
any shutdown-induced writes is mandatory, the stopped-first plan is insufficient
and must be redesigned under separate authority.

Journal replay, filesystem repair, restore/promotion/replacement, forced shutdown,
Colima restart, Docker cleanup/reset/removal, infrastructure tests and live
Gemini remain excluded. Native PG/Redis stay running. Do not begin Phases 11–13
or the SYNTRA frontend. All historical backups/evidence remain unchanged.

**STOP after this review. No B3-P stage has been approved or executed.**
