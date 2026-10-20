# SYNTRA Phase 10 — B3 current-state preservation and assessment plan

Date: 2026-10-16, Europe/Budapest. **PROPOSED; PLANNING ONLY.**

Infrastructure: **BLOCKED_FILESYSTEM_CHECK_REQUIRED**. Phase 10:
**PHASE_10_REQUIRES_WORK**. Current filesystem consistency: **UNVERIFIED**.
B3 preservation/assessment execution: **NOT AUTHORIZED, NOT PERFORMED**.

This is the single canonical B3 planning report. It extends, without replacing,
the historical closeout plan, B1/B2 reports, recovery reports and independent
audit. The latest B3 planning-only instruction controls over older execution
permissions. No earlier permission is reused for another stop/start or check.

## 1. Executive disposition

The historical B2 procedure completed safely but its filesystem was not clean:
native e2fsck exited **4**, with uncorrected metadata inconsistencies and journal
recovery skipped. It neither assessed the current live disk nor demonstrated
application data loss. Repair is not justified merely to remove a warning.

The current `default` Colima VM is running and holds both disk files open.
PostgreSQL and Redis are native host services, outside those disks. A stopped VM
backup would preserve Docker disk state but would not back up the native stores,
host bind mounts, source tree, Git metadata or host execution artifacts.

The five-sample memory window passed the existing strict resource criteria.
Storage initially failed the new, proposed 12 GiB preservation-entry allowance,
then rose to **12.947250 GiB** at 16:21:40 CEST and passed it at that observation.
Capacity is not reserved and must be checked again at execution time.

Two safety prerequisites remain unresolved: the installed shutdown path cannot
yet be certified as wholly graceful, and native persistence/ownership/quiescence
details are incomplete. Therefore the next requested authorization is **B3-Q,
bounded read-only qualification**, not an open-ended recovery authorization.
Section 15 contains that one consolidated request. The later preservation plus
one no-write assessment can share a conditional authorization once those gaps
are resolved. Replay, repair, extraction and promotion remain separate decisions.

## 2. Evidence reviewed and provenance

Reviewed the Phase 10 verification report, independent audit, manual scenarios,
infrastructure diagnosis, controlled recovery, recovery preflight, offline safety
review, consolidated A–L closeout plan including B1/B2 addenda, B1 provisioning
report, B2 report, complete B2 checker stdout/stderr/timing and native statuses,
and retained manifests. Earlier reports are historical, not fresh passes.

New planning evidence only:

`/Users/thedeepakreddy/SYNTRA/.syntra/phase10-evidence/20261016T160857+0200-b3-planning/`

Files include the full five-sample resource window, final refresh, host/Docker
inventory, selected disk/config/native-service metadata, redacted endpoint
identities, retained-integrity results, host log search, a 449-file source
baseline, and independent planning-review limitations. Inventory stdout is
retained; it is not falsely presented as a fully instrumented per-command timing
transcript. Resource samples contain exact argv, times, exits and raw output.

Fresh integrity checks: **38 B2 evidence files matched their index**; all 15
historical backup files retained matching inode/size/mode; verified-manifest SHA
still `c81349d1a8c1173ffc741c5876594cd88a0b8d7f20749e7051461e082320fbf5`.
No full VM-image rehash was repeated in this planning stage. The most recent full
historical-backup pre/post verification remains B2, ending 15:48:31 CEST.
Current disk content hashes are deliberately unknown while the VM is running.

Read-only planning reviewer Hooke independently challenged supplied observations
and upstream shutdown/backup semantics. The reviewer did not read local recovery
reports, so this is a limited planning critique, not a final independent audit.
Its shutdown, Redis scope, clone-count, capacity and failure-path findings are
incorporated here. Same-provider agent review is not third-party certification.
Ruflo/ToolSearch routing was unavailable; no such invocation is claimed.

## 3. B2 actual findings and their limits

Historical source:
`/Users/thedeepakreddy/SYNTRA/.syntra/infrastructure-backups/20261016T002121+0200/data/datadisk`.
Historical derivative:
`/Users/thedeepakreddy/SYNTRA/.syntra/phase10-offline-assessment/20261016T153334+0200/datadisk.analysis.raw`.
Actual output:
`/Users/thedeepakreddy/SYNTRA/.syntra/phase10-evidence/20261016T153334+0200-b2-assessment/e2fsck.stdout`.

The installed native ARM64 e2fsck 1.47.4 ran once, with `-f -n -v` and
`-E nodiscard,no_inode_count_fullmap,readahead_kb=0`. All five passes completed:
inodes/blocks/sizes, directories, connectivity, reference counts and summaries.
Native exit **4** means errors left uncorrected. The observer's exit 0 means
capture completed; it must never replace the checker's actual exit.

| Finding in historical raw state | Interpretation |
|---|---|
| Unconnected directory inode 2097183, formerly under `/docker/rootfs/overlayfs` | Directory connectivity inconsistency; not proof all Docker layers or contents were lost |
| `..` points to inode 2097180 rather than the parent expected by the checker; refcount 2 should be 1 | Parent/reference metadata disagree with the checker's reconstructed directory graph |
| Block bitmap difference `+8396851` | Block allocation accounting inconsistency, not a verified file-content loss |
| Group 256 free count 24522 versus counted 24523 | Group summary mismatch |
| Global free count 25611878 versus counted 25611879 | Global summary mismatch, one block difference |
| Group 256 block bitmap checksum mismatch, ignored | Unresolved checksum discrepancy, not a passed checksum |
| Required journal recovery explicitly skipped | Pre-replay metadata view is not necessarily the consistent post-transaction view |

The output reported 6532/6553600 inodes and 602010/26213888 blocks, with 6776
files in its detailed statistics. All offered corrections were declined. No
unsupported-feature, attempted-write, I/O/ENOSPC, timeout or resource-interruption
failure was recorded. This does not verify every user-data block or Docker blob.

Both source/derivative full SHA-256 values before and after matched:
`9de7d661f8d4c4a7fce36ad6a54f74d235df57e0d6328da080a8aa3aaf2b12dd`.
The historical source inode was 97698031, derivative 97738504; each was
107374182400 logical bytes. OS read-only, unmounted device exposure was verified;
the exact returned device was detached without force. Neither is attached now.

Required classifications:

- **CONFIRMED_CORRUPTION_IN_HISTORICAL_SNAPSHOT:** confirmed metadata
  inconsistencies in the raw, unreplayed historical image. This label does not
  assert persistent post-replay corruption or permanent application damage.
- **POSSIBLY_JOURNAL_RELATED_INCONSISTENCY:** connectivity, parent/refcounts,
  allocation bitmaps, summaries and checksums can be affected by transactions
  not yet replayed. Some, all or none may remain afterward; no resolution claim.
- **UNVERIFIED_DATA_LOSS:** no comparison to an authoritative complete
  application-data manifest, layer-content audit or database recovery exists.
- **CURRENT_FILESYSTEM_STATUS_UNKNOWN:** the backup predates the latest restart,
  replay and engineering activity. Current disks must be preserved separately.

The no-write implementation explicitly skips required journal recovery; `-n`
does not repair or produce a post-replay certification. See [pinned upstream
e2fsprogs 1.47.4 source](https://raw.githubusercontent.com/tytso/e2fsprogs/v1.47.4/e2fsck/unix.c).
Even an ordinary read-only ext4 mount can replay its journal; no mount of any
kind is part of this proposal. See [Linux ext4 mount semantics](https://docs.kernel.org/admin-guide/ext4.html).

## 4. Current infrastructure inventory

### 4.1 VM, storage identities and configuration

Colima **0.10.3**, commit `00f6c297e92a82c04a4ab507db0a61435650d7e8`;
Lima **2.2.1**. Profile `default`: **Running**, aarch64/VZ, Docker runtime,
2 CPUs, 4 GiB RAM, 100 GiB configured data disk, 20 GiB boot disk.

| Disk | Exact host path | Device / inode | Logical bytes | Allocated bytes |
|---|---|---|---:|---:|
| Current boot | `/Users/thedeepakreddy/.colima/_lima/colima/disk` | 16777233 / 97406017 | 21474836480 | 1496170496 |
| Current data | `/Users/thedeepakreddy/.colima/_lima/_disks/colima/datadisk` | 16777233 / 97405962 | 107374182400 | 598261760 |

Both are regular, owner UID 501, mode 0644, not symlinks. Virtualization PID 7472
holds both open for read/write. These are **not stopped-state clone sources**.
Their combined reported allocation is **1.950592 GiB**, not a bound on future
growth or unique physical extents. Existing clones share APFS blocks; adding `du`
values can double-count shared storage.

Measured directory allocations: `_lima/colima` 1481088 KiB;
`_lima/_disks/colima` 584240 KiB; profile `default` 12 KiB. The generated Lima
configuration exposes the user's home through writable virtiofs, despite an empty
explicit profile mount list. Host files accessed through it are outside VM-disk
coverage. No profile, disk-size, mount or runtime setting was changed.
Stopped-stage raw/backing-file dependencies must still be confirmed, not inferred
only from file suffix or size.

### 4.2 Docker and engineering activity

No running containers were returned. The protected pre-existing container remains:
`a178d7fd14286308ee1b11e0ccb0678804dbdfd34573f2bf9b5aa910cba40252`,
`syntra_sandbox_033e7b19-5182-431a-8059-653ff4329b4a_1`, Exited (137).
It has host worktree bind mounts. Do not remove the container or those worktrees.

Existing image metadata reads succeeded:

- `syntra-sandbox:latest` — `sha256:a71c85627b0114fb432baa40dd4627783813ee92ae1661540c8dac3b92c7afea`.
- `syntra-phase10-acceptance:local` — `sha256:63c9946b06f2ad70f0febd60fe6c09b8076e06865010de3ea90fa5bb8bbc2f00`.

`docker volume ls` returned no rows. That is not evidence that there is no
important application data: writable container layers, bind mounts and native
stores exist. Image inspection does not verify readable layers or filesystem
health. No containers were executed, started, stopped, removed or created.

Process-name inventory did not identify a named engineering worker/test run.
An existing Python process could not subsequently be identified through `lsof`
(exit 1, no result); do not classify it as stopped or safe to terminate from
that observation. No authoritative mission/lease/queue reads were made. **Global
engineering quiescence is UNVERIFIED**, not established by process names alone.
Before preservation require a user-agreed hold on API submissions, workers,
schedulers, outbox dispatchers, reconcilers, tests and repository writes. Do not
cancel leases or edit queues as a shortcut.

### 4.3 Native PostgreSQL, Redis and legacy SQLite

Configured `.env` endpoint identities were inspected without displaying secrets:
`localhost:5432/syntra_dev`, `localhost:5432/syntra_test`, and Redis
`localhost:6379/0`. Endpoint configuration is not proof of live client ownership.

| Service | Observed process/data | Preservation implication |
|---|---|---|
| PostgreSQL 16 | PID 1091, `/opt/homebrew/opt/postgresql@16/bin/postgres -D /opt/homebrew/var/postgresql@16`; localhost 5432; data dir 116468 KiB | Native, not covered by VM disks; do not copy an active data directory as a consistent backup |
| Redis | PID 38244, `/opt/homebrew/opt/redis/bin/redis-server 127.0.0.1:6379`; cwd `/opt/homebrew/var/db/redis`; localhost 6379 | Native in-memory data/current persistence must be qualified separately |
| Redis disk artifact | `dump.rdb`, 11800 bytes, modified about 01:26; directory 12 KiB | Historical persisted state only; freshness/current memory equivalence unknown |
| Legacy SQLite | `/Users/thedeepakreddy/SYNTRA/syntra.db`, 561152 bytes | Retain even though configured endpoints use PostgreSQL; no deletion as obsolete |

Static Redis configuration says `appendonly no`, `dbfilename dump.rdb`, that data
directory and `appenddirname appendonlydir`. Runtime settings, latest successful
save, other logical DBs, key ownership and memory usage remain **UNVERIFIED**.
No PostgreSQL/Redis connection, dump, SAVE/BGSAVE or configuration operation was
performed. No existing database or development environment was modified.

### 4.4 Host-only versus guest interaction

Host-only: `df`, `diskutil info`, `sysctl`, `vm_stat`, `ps` names/RSS,
selected `lsof`, file stat/du/config-field reads, existing evidence hashes,
narrow host unified-log search, local command help and installed tool-file hash.
Normal user 501 was used; sandbox escape for host-framework visibility was not
root/sudo authority.

Read-only Docker API queries are **guest-daemon interactions**, not pure host-only
reads. They may update daemon access/runtime logs. No `docker exec`, guest SSH,
mount, checker, native database query or guest diagnostic service was invoked.
The proposed qualification SSH below has a concrete safety purpose and needs
approval because authentication/logging can write the guest.

The accessible last-30-minute host kernel/Virtualization log search for ENOSPC,
no-space, I/O errors/IO failure and APFS transaction failures returned exit 0 and
only its header. This is **NO_MATCHES_IN_LIMITED_HOST_WINDOW**, not proof there
are no errors. It excludes guest logs and inaccessible/older events. The known
current-boot check-required warning remains authoritative.

## 5. Current resource measurements and proposed gates

Five samples from **16:09:21.862488 to 16:11:26.640726 CEST**, 124.778 seconds:
all pressure **NORMAL**, headroom proxy **2.038284–2.055984 GiB**; cumulative
swap-outs **3152481 pages**, unchanged. Final window swap used 3632.06 MiB
(3.547 GiB), not a new allocation requirement or readiness criterion by itself.
The proxy is free + inactive + speculative pages, without adding overlapping
purgeable/file-backed counts. Inactive memory is reclaimable, not guaranteed
immediately available. It is an operational estimate, not an OS commitment.

Fresh follow-up at **16:21:40 CEST**:

| Measurement | Actual observation |
|---|---:|
| `df` available | **13902004224 bytes** |
| `diskutil` APFS container free | **13902032896 bytes** |
| Conservative minimum | **13.902004224 GB = 12.947250366 GiB** |
| Installed RAM | 8589934592 bytes = 8 GiB |
| Memory pressure | NORMAL (1) |
| Headroom proxy | **1.949142 GiB** |
| Swap used | 3608.06 MiB = approximately 3.523 GiB |
| Swap-out counter | **3152481**, unchanged from qualification window |

GB means 10^9 bytes; GiB means 2^30 bytes. APFS `FreeSpace=0` in this plist is
not the shared-container availability field; use `APFSContainerFree` together
with `df` on the actual destination, conservatively taking the lower reading.
Space rose between observations; no cleanup was done or its cause established.

### Proposed preservation-stage storage budget — new policy, not approved

| Allowance | GiB | Basis/limitation |
|---|---:|---|
| OS/swap operating floor | 5 | Existing safety reserve, retained |
| Shutdown/dirty-data/COW contingency | 4 | Engineering allowance tied to configured VM RAM; **not a dirty-write upper bound** |
| Analysis clone/control-plane/evidence contingency | 1.5 | Existing analysis allowance; target assessment is no-write |
| Bounded host source/config/native exports | 0.5 | Must be measured and bounded before writes; Redis export currently unresolved |
| Additional slack | 1 | Do not spend it on unrelated work |
| Proposed pre-stop minimum | **12** | **12884901888 bytes**, stricter than historical 8 GiB |

At 16:11:26, 11.379959 GiB would fail this proposal by 665763840 bytes. At
16:21:40 it passes by **1017102336 bytes (0.947250 GiB)**. This is a point-in-time
resource pass only, not execution readiness. If measured exports/dirty activity
exceed allowances, increase the required gate or stop; never weaken it silently.

After approved host exports and immediately before stop, require >=12 GiB.
After confirmed stop, before **each** clone, attachment and check, retain the
existing >=8 GiB entry gate. During approved hashing/checking sample at least
every 5 seconds, guard >=5 GiB; halt new work at <6 GiB as early warning and on
rapid unexplained loss. No reserve is physically guaranteed against other apps.
If shutdown is in progress and capacity deteriorates, do not force-kill the VM
or abort it into an unknown state: stop downstream work, record state, seek help.

Memory before heavy preservation/hash/assessment: >=3 samples spanning >=120
seconds, all NORMAL, headroom >=1.5 GiB at every sample, no sustained swap-out
growth. Keep the existing definition: increasing counter in **two consecutive
sample intervals** is sustained; reset/reboot/counter ambiguity requires a new
window. During work use 5-second monitoring; warning pressure, low headroom,
sustained growth or failed measurement stops affected work. No process is killed
to meet the gate. Read-only qualification itself should also use this strict
gate to avoid approving a service export under marginal resources.

One checker only; no full inode-count map or readahead. B2's measured behavior
supports this bounded proposal but does not guarantee a future corrupted image's
memory use. Use streaming 1 MiB hash buffers and `F_NOCACHE` as in reviewed B2
hashing; avoid whole-image buffers/parallel hash/checker jobs. Native Redis fork
COW could exceed headroom and needs its own later budget after live INFO data.

APFS direct clones share extents initially; they are not 100 GiB new allocations,
but metadata growth and later COW cannot be predicted exactly. Use `clonefile`
only; failure/EXDEV ends that branch. **No `cp -c` or full-copy fallback.**
See [Apple clonefile contract](https://raw.githubusercontent.com/apple-oss-distributions/xnu/main/bsd/man/man2/clonefile.2).
Materializing current boot+data is 120 GiB logical; a data derivative adds 100
GiB. A later writable derivative could rewrite up to its entire logical space;
the present budget does not authorize or cover that worst case. Current sparse
allocation is not a repair budget. Verification can stream 440 GiB of logical
input for source/backup/derivative equality and derivative post-check, with 240
GiB more if both originals/backups are fully rehashed again. Sparse holes lower
physical reads but not the bytes the SHA algorithm must process. Allow monitored
minutes, potentially longer; elapsed time is evidence, not a promised deadline.

A separately approved, encrypted second physical device materially improves
safety against APFS-container/SSD failure and frees repair workspace. Cloning
across filesystems cannot share extents; it needs an explicitly budgeted sparse
transfer or >=120 GiB for the boot/data pair (>=220 GiB with another materialized
data derivative), plus application/evidence reserve. A destination with >=256
GiB free is a conservative materialized-workspace recommendation, not a measured
requirement of a sparse transfer. No external device is identified/approved and
no relocation or copy is performed. Same-device clones are not disaster backups.

## 6. Preservation strategy and consistency requirements

### 6.1 Protect historical artifacts first

Never overwrite, chmod, attach, repair, move or restore the historical backup or
B2 derivative. Keep old logs and both optimistic/superseding health records.
Recheck manifest identities before a future operation; repeat full historical
image hashing only if required for use or a changed-integrity suspicion, rather
than rerunning B2 unnecessarily. New artifacts go only to new timestamped roots.

### 6.2 Host source, Git, evidence and native stores

Before VM interruption, inventory a frozen source manifest: tracked files,
nonignored untracked work, `.git` objects/refs/index/reflogs/config/worktree
metadata, necessary ignored `.env`/local configuration, artifacts, logs, receipts,
the protected test worktree's external Git dependencies and legacy SQLite.
Preserve all existing files in place. For an approved additional host backup,
enumerate selected regular files and use same-volume direct clones under a
private new root; no blind recursive clone of `.syntra`, which contains VM
backups/derivatives. Explicitly exclude reproducible `.venv`, caches and existing
large VM backup/analysis trees from duplication, **not deletion**. Include an
index of their immutable existing locations/hashes. Escaping symlinks, external
Git common dirs, an open SQLite WAL, or mutable artifacts not covered by a writer
hold are a STOP until their exact preservation scope is approved.

Protect secrets with new directories 0700 and secret files 0600; no credential
values in transcripts or command argv. Do not alter permissions on old originals.
A Git bundle alone would miss working-tree/untracked/ignored work; a clean Git
status alone would miss ignored data. Current HEAD is
`998c00c4a7384851667dd5ea648533eddf29b92d`; existing dirty implementation and tests
are user work, not cleanup scope. No commit/reset/clean/push is proposed.

**PostgreSQL:** logical dumps of `syntra_dev` and `syntra_test` are warranted and
probably feasible given the ~114 MiB cluster allocation, but actual sizes,
privileges, extensions and writers must be qualified first. Use installed PG16
`pg_dump` in custom format, one DB at a time, no source changes or server stop.
Capture DB/extension/encoding/owner/required-role metadata without password
hashes; do not export unrelated databases/globals indiscriminately. Each dump is
transactionally consistent individually, not a common snapshot across the two
DBs or Redis. A cooperative all-writer hold is needed for a coordinated SYNTRA
checkpoint. `pg_restore --list` plus SHA verifies readable archive structure,
not restore correctness. A later isolated restore test needs separate scope.
See [PostgreSQL 16 dump consistency](https://www.postgresql.org/docs/16/backup-dump.html).

**Redis:** first identify runtime persistence, dataset size, logical DBs and
ownership. Existing `dump.rdb` is not a fresh memory backup. `redis-cli --rdb`
uses replication to export the **entire instance**, not DB 0 only; it may trigger
forking, COW, buffering and persistence writes. It is excluded from B3-Q and not
implicitly authorized by a VM backup. If dedicated ownership and memory budget
are confirmed, propose an explicitly approved whole-instance export; if shared,
design a scoped consistent export with TTL/stream semantics first. Do not assume
queue state disposable. No SAVE/BGSAVE, CONFIG SET, CLIENT PAUSE, FLUSH*, service
stop, or key-by-key ad hoc backup fallback. See [Redis CLI backup behavior](https://redis.io/docs/latest/develop/tools/cli/)
and [Redis persistence risks](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/).

Until those backups/coverage are resolved, native stores remain protected
**in situ but not freshly backed up**. A capacity check or raw VM clone cannot
close that preservation gap. Do not begin the shutdown stage while claiming
complete SYNTRA preservation with this gap unresolved.

### 6.3 Quiescence and graceful shutdown risk

No running containers at inspection is encouraging, not a future downtime grant.
Confirm no unrelated containers/jobs would be interrupted immediately before
stop. Require a user-coordinated producer/repository hold. If active processes
appear, identify exact mission/owner/PID and await scope; do not send broad kills,
cancel tasks, or stop host PostgreSQL/Redis or unrelated services.

Normal shutdown flushes dirty pages, checkpoints/unmounts filesystems and writes
runtime logs/metadata. Thus a later approved graceful stop **can modify current
disk bytes before their stopped-state clone exists**. No byte-exact pre-shutdown
image is promised. With prior journal/ENOSPC errors, flushing may fail or expose
more damage; a stopped result might still be only crash-consistent. If preserving
the exact running instant before any such write is required, stop planning this
sequence and request a separately designed crash-consistent/live-snapshot method;
do not silently clone open disks and call them application consistent.

Installed stop-source review: Colima first stops guest runtimes, logs some
runtime-stop failures nonfatally, then invokes Lima. Lima's ordinary stop path
is separate from force stop. VZ requests shutdown but returns an error after
30 seconds without confirmed stop. Hostagent returns after driver cleanup, so
process disappearance alone is not proof of clean guest shutdown. This last
consequence is an inference from the control flow. Sources: [Colima application stop](https://github.com/abiosoft/colima/blob/v0.10.3/app/app.go),
[Lima graceful-stop path](https://github.com/lima-vm/lima/blob/v2.2.1/pkg/instance/stop.go),
[pinned VZ stop](https://github.com/lima-vm/lima/blob/v2.2.1/pkg/driver/vz/vz_driver_darwin.go),
[hostagent shutdown](https://github.com/lima-vm/lima/blob/v2.2.1/pkg/hostagent/hostagent.go).

Guest systemd policies may escalate service termination; external-driver cleanup
also has conditional escalation paths, not proven applicable to this built-in
VZ instance. Autostart/launchd routing and active runtime service policies need
read-only qualification. **Do not equate absence of `--force` with a guaranteed
wholly nonforcing operation.** No stop command is execution-ready on this record.
Do not modify systemd timeouts, replace binaries, patch Colima, disable launchd
or change the VM configuration to resolve this gap under a read-only approval.

## 7. Staged B3 procedure — proposed commands, DO NOT EXECUTE

These are gated human-reviewed stages, not one unattended script. Variables
below are placeholders populated only from future verified records. Paths must
be absolute, absent at creation, owner-only, non-symlink throughout their ancestry
and on the same APFS filesystem. Failure never authorizes retries/alternatives.
No B3 execution helper has been created or run in this planning stage.

### Q — Read-only service and shutdown qualification (next proposed approval)

Refresh host resources over >=120 seconds and current Docker/process metadata.
Use the exact current profile, existing clients/credentials privately, and only
these bounded guest/native reads; no file enumeration/data-content export.
The installed `colima ssh --help` was checked; it accepts `--profile` and `--`.

```sh
/bin/df -k /Users/thedeepakreddy/SYNTRA
/usr/sbin/diskutil info -plist /System/Volumes/Data
/usr/sbin/sysctl hw.memsize kern.memorystatus_vm_pressure_level vm.swapusage
/usr/bin/vm_stat
/opt/homebrew/bin/colima list --json
/opt/homebrew/bin/docker --context colima ps -a --no-trunc
/opt/homebrew/bin/colima ssh --profile default -- cat /proc/sys/kernel/random/boot_id
/opt/homebrew/bin/colima ssh --profile default -- systemctl show docker.service containerd.service -p Id -p ActiveState -p SubState -p TimeoutStopUSec -p SendSIGKILL -p KillMode -p KillSignal -p FinalKillSignal
/opt/homebrew/bin/colima ssh --profile default -- findmnt -rn -o SOURCE,TARGET,FSTYPE,OPTIONS
```

Inspect only already identified host Colima/Lima parent commands and relevant
autostart labels/configuration read-only; do not change them. Inspect pinned
source/binary identity to determine which built-in/external driver path is
actually active. No broad guest log scan or added diagnostic command is implied.
If units/access differ, record UNVERIFIED and stop rather than starting services
or elevating implicitly. SSH can produce authentication/service logs; that
incidental write risk is part of Q approval, not called globally no-write.

For native PG16 use the SYNTRA-configured role resolved privately as
`PG_BACKUP_ROLE` (never a password in argv), existing approved credential access,
`-X`, no password prompt and a read-only transaction. No new credential file or
privilege grant. Proposed first query against `syntra_dev`:

```sh
PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=5000' \
  /opt/homebrew/opt/postgresql@16/bin/psql -X --no-password \
  --host=localhost --port=5432 --username="$PG_BACKUP_ROLE" --dbname=syntra_dev \
  --command="BEGIN READ ONLY; SELECT current_database(), version(); SELECT datname, pg_database_size(oid) FROM pg_database WHERE datname IN ('syntra_dev','syntra_test'); SELECT datname, state, count(*) FROM pg_stat_activity WHERE datname IN ('syntra_dev','syntra_test') GROUP BY datname,state; SELECT extname,extversion FROM pg_extension; COMMIT;"
```

Repeat only the identity/extensions query for `syntra_test`; inspect required
non-secret role/ownership metadata scoped to those DBs if readable. Do not read
mission contents or client query text, dump globals/password hashes, create a
schema, acquire a write lock, or interpret no active SQL as proof no future
producer. Authentication/statistics/server logging can change normally.

```sh
/opt/homebrew/opt/redis/bin/redis-cli -h localhost -p 6379 INFO memory
/opt/homebrew/opt/redis/bin/redis-cli -h localhost -p 6379 INFO persistence
/opt/homebrew/opt/redis/bin/redis-cli -h localhost -p 6379 INFO keyspace
/opt/homebrew/opt/redis/bin/redis-cli -h localhost -p 6379 CONFIG GET dir dbfilename appendonly appenddirname save
```

No key values, key scan, replication/export, save or config change. ACL failure
means STOP, not credential guessing. Obtain user's confirmation whether this
whole instance is SYNTRA-dedicated; INFO cannot prove business ownership.
Q ends with exact native backup scope/budget and a qualified shutdown proposal
or an explicit blocker. It **does not** itself proceed to P even if all reads pass.

### P1 — Pre-interruption coverage (future combined P approval)

Prerequisites: Q completed; shutdown path acceptable under no-force policy;
native backup scope/credentials/limits approved; cooperative writer hold;
>=12 GiB and strict memory window. Freeze exact file manifests/source versions.
Choose a fresh literal timestamp once, record it as `B3_RUN_ID`; reject reuse.

Proposed roots (not created):

```text
/Users/thedeepakreddy/SYNTRA/.syntra/infrastructure-backups/<B3_RUN_ID>-current-state/
/Users/thedeepakreddy/SYNTRA/.syntra/phase10-offline-assessment/<B3_RUN_ID>-current-state/
/Users/thedeepakreddy/SYNTRA/.syntra/phase10-evidence/<B3_RUN_ID>-current-state/
```

Approved host-file clones, configuration/log snapshots and native exports live
under the new backup only; evidence is outside it. Recheck output-size limits
and free capacity during exports; preserve partial exports as FAILED, no cleanup.
Proposed PG commands, **not authorized yet**, one at a time:

```sh
/opt/homebrew/opt/postgresql@16/bin/pg_dump --no-password --host=localhost --port=5432 --username="$PG_BACKUP_ROLE" --dbname=syntra_dev --format=custom --file="$B3_BACKUP/native/postgres/syntra_dev.dump"
/opt/homebrew/opt/postgresql@16/bin/pg_dump --no-password --host=localhost --port=5432 --username="$PG_BACKUP_ROLE" --dbname=syntra_test --format=custom --file="$B3_BACKUP/native/postgres/syntra_test.dump"
/opt/homebrew/opt/postgresql@16/bin/pg_restore --list "$B3_BACKUP/native/postgres/syntra_dev.dump"
/opt/homebrew/opt/postgresql@16/bin/pg_restore --list "$B3_BACKUP/native/postgres/syntra_test.dump"
```

Parent directory/exclusive destination checks must precede commands: pg_dump can
overwrite an existing filename. Read catalog snapshots only; default dump read
locks can briefly contend with DDL, so use a reviewed lock-wait timeout at final
approval if needed. Dump success plus hash is not a restored-database PASS.
Redis export command is deliberately **not executable here** until Q determines
dedicated/shared ownership, persistence mode, size and fork budget. No silent
fallback to an old RDB. Hold P if this current-state coverage remains unresolved.

### P2 — One controlled stop, if and only if separately approved

Candidate CLI, subject to Q resolving the nonforcing concern:

```sh
/opt/homebrew/bin/colima stop default
```

Capture exact argv, times, all output, native exit and shutdown host logs. No
`--force`, `limactl stop --force`, kill, launchctl bootout, VM reset or retry.
Do not wrap a VM stop in an automatic SIGKILL timeout. A timeout, runtime-stop
failure, ambiguous backend exit or new storage error means halt downstream work,
report actual Running/Stopped/UNKNOWN state and seek direction. Do not force
completion or restart because the planned terminal state was Stopped.

After successful graceful evidence, require `colima list --json` Stopped,
`lsof` on both exact disk paths with no writer handles, stable identity metadata,
no pending autostart and no reappearance during two observations >=5 seconds
apart. Review normal shutdown/unmount completion from available serial/hostagent
logs. Missing evidence is not a clean shutdown. Even genuinely graceful stop
does not certify the ext4 contents. Never attach either original disk.

### P3 — Preserve both stopped disks and one assessment derivative

Recheck >=8 GiB, pressure/headroom, file identities, format/backing dependencies,
writer exclusion and original no-symlink paths. Clone exactly these pairs:

| Attempt | Source | New destination |
|---|---|---|
| 1 | `/Users/thedeepakreddy/.colima/_lima/colima/disk` | `$B3_BACKUP/vm/disk` |
| 2 | `/Users/thedeepakreddy/.colima/_lima/_disks/colima/datadisk` | `$B3_BACKUP/data/datadisk` |
| 3, only after verified backup | `$B3_BACKUP/data/datadisk` | `$B3_ANALYSIS/datadisk.analysis.raw` |

At most three VM-disk clone attempts; three successes on the success path. Abort
first failure, no retries/fallback. Additional small enumerated regular-file
clones preserve source/config/log data; they are not extra VM image copies.
Do not use a hard link. The common-state claim for sequential boot/data clones
depends on continuous writer exclusion, not an atomic two-disk clone operation.

Proposed exact direct primitive (not run), once per approved pair in the table.
Populate `B3_CLONE_SOURCE` and `B3_CLONE_DESTINATION` with that pair's verified
literal paths only after stopped/no-writer/resource gates; create and protect
the new parent directories under the approved root first. This primitive does
not itself establish those external gates and must not be run out of sequence:

```sh
/Users/thedeepakreddy/SYNTRA/.venv/bin/python -B - "$B3_CLONE_SOURCE" "$B3_CLONE_DESTINATION" <<'PY'
import ctypes
import json
import os
import stat
import sys
from pathlib import Path

source, target = map(Path, sys.argv[1:])
if not source.is_absolute() or not target.is_absolute():
    raise SystemExit('STOP: absolute paths required')
for path in (source, *source.parents, target.parent, *target.parent.parents):
    if path.is_symlink():
        raise SystemExit('STOP: symlink component')
if os.path.lexists(target):
    raise SystemExit('STOP: destination already exists')
before = source.lstat()
parent = target.parent.stat()
if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid():
    raise SystemExit('STOP: unexpected source type/owner')
if parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) != 0o700:
    raise SystemExit('STOP: destination parent not private')
if before.st_dev != parent.st_dev:
    raise SystemExit('STOP: cross-filesystem clone forbidden')
libc = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
libc.clonefile.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
libc.clonefile.restype = ctypes.c_int
if libc.clonefile(os.fsencode(source), os.fsencode(target), 0) != 0:
    error = ctypes.get_errno()
    raise OSError(error, os.strerror(error))
after, cloned = source.lstat(), target.lstat()
if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
    raise SystemExit('STOP: source changed during clone')
if (cloned.st_dev != before.st_dev or cloned.st_ino == before.st_ino
        or cloned.st_size != before.st_size):
    raise SystemExit('STOP: clone identity/size mismatch')
print(json.dumps({'source': str(source), 'destination': str(target),
                  'source_inode': before.st_ino, 'clone_inode': cloned.st_ino,
                  'bytes': cloned.st_size, 'full_hash_verification_pending': True}))
PY
```

No catch-and-copy branch, retry or removal of a partial target. Full digest
verification remains mandatory below. The stopped sources remain unmodified by
the clone/hash operation; no chmod on originals. Protect only new derivatives.

Clone profile `/Users/thedeepakreddy/.colima/default/colima.yaml`, generated Lima
configuration and enumerated regular VM boot identifiers/EFI/config/serial/
hostagent logs and data-disk metadata after stop, including newly discovered
required backing files. Do not copy sockets/PIDs as restorable runtime state.
If inventory differs from approved manifest, halt and amend scope.

Full streaming SHA-256 compare stopped boot to backup boot and stopped data to
backup data; independently hash derivative equal to the new data backup. Record
source/backup size, inode/device, owner/mode, times, allocation and digest; verify
identities/writer exclusion again. **Do not compare current disks to historical
B2 digest as an equality requirement**: legitimate later writes may differ.
Write a new verified manifest and its SHA only after all comparisons pass.

### P4 — Read-only unmounted exposure and identity/protection gate

Record binary file hash, not another installation/checker invocation. Expected
native binary `/opt/homebrew/Cellar/e2fsprogs/1.47.4/sbin/e2fsck`, SHA-256
`40dd92042872a4f39c1954a3588a77c08ef05c8e05898172058ff4407e8c2f60`.
B1 verified ARM64 dependencies; B2 proved access for its historical partition.
Current feature/device compatibility must still be checked; mismatch means STOP.

```sh
/usr/bin/hdiutil attach -imagekey diskimage-class=CRawDiskImage -readonly -nomount -noautofsck -plist "$B3_ANALYSIS/datadisk.analysis.raw"
```

Capture stdout plist/stderr/native status to new evidence. Parse this successful
response to resolve the exact whole device and Linux partition; do not prefill
`/dev/disk4` or any disk number. Correlate image path/device through hdiutil info.
Then, **using only returned identifiers**:

```sh
/usr/sbin/diskutil info -plist "$B3_WHOLE_DEVICE"
/usr/sbin/diskutil info -plist "$B3_PARTITION_DEVICE"
/usr/sbin/diskutil list -plist "$B3_WHOLE_DEVICE"
/usr/bin/hdiutil info -plist
/sbin/mount
```

Require whole and partition `WritableMedia=false` and `Writable=false`; no
mounted child in plist or mount inventory; original images remain unattached.
Use read-only byte parsing to verify raw/GPT header+entry-array CRCs, partition
boundaries and ext4 magic/UUID/block size/features. Compare to just-created
current-backup records, not merely historical expectations. Historical geometry
is a discrepancy trigger to investigate, **not authority to pick a different
partition**:

- 512-byte sector; entry 1; LBA 2048–209713151; byte offset 1048576;
  length 107372085248.
- Partition GUID `17300ecd-f3b8-4833-9d55-18ffc2a130b8`.
- ext4 UUID `3de9071f-0361-4f65-88a3-f223f8faacb2`; block size 4096.
- Historical features compat/incompat/ro_compat `0x3c/0x2c6/0x46b`;
  incompat `0x4` journal-recovery flag. Do not assume current masks unchanged.

Record s_state/ERROR_FS, needs_recovery, error_count and first/last error times
without clearing anything. Check superblock/feature support before the checker;
CRC/identity ambiguity is STOP, not permission for an alternate superblock or
partition extraction. See [kernel ext4 superblock fields](https://docs.kernel.org/filesystems/ext4/super.html).
Use normal-user device access proven possible in B2; if not available now,
request exact-command/device permission rather than sudo/chmod/mount fallback.

### P5 — One no-write check, exact output, safe detach and post-integrity

Only after every prior gate, one invocation against the verified **partition**:

```sh
env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin LC_ALL=C E2FSCK_CONFIG=/dev/null \
  /opt/homebrew/Cellar/e2fsprogs/1.47.4/sbin/e2fsck -f -n -v \
  -E nodiscard,no_inode_count_fullmap,readahead_kb=0 "$B3_PARTITION_DEVICE"
```

Capture complete stdout/stderr separately, native status/exit bitmask, tool SHA,
identity/protection data, start/end/elapsed/peak-RSS and monitored resources.
Do not pipe away native exit or equate observer success with checker success.
No `-p/-a/-y`, writable mode, mount, bad-block scan, journal-only replay, repair,
discard, optimization or unsupported-flag fallback. Unsupported/native access
failure means incomplete, not a reason for another invocation.

On resource/error cancellation, stop only the newly owned checker process with
graceful interrupt/termination as approved; never force VM/device termination.
Wait for checker exit before detaching. A hung checker requires new direction,
not forced detach. Record partial output as UNVERIFIED.

```sh
/usr/bin/hdiutil detach "$B3_WHOLE_DEVICE"
/usr/bin/hdiutil info -plist
```

Detach only that returned whole device, without force. Confirm mapping/device
nodes disappeared. On failed detach, leave it read-only and report it attached;
no restart/delete/reattach workaround. After successful detach, full rehash of
derivative must equal its pre-check digest; verify new backup manifests/small
files, source/backup stability and any required full post hashes. No auto-delete
of evidence/clone, even on success. Report all five passes, journal handling,
error bits, flags, hashes and uncertainty. Successful P ends with VM **Stopped**;
failure ends in actual observed state, not forced attainment of that target.

## 8. Expected evidence and completion contract for future execution

For every stage: exact argv/cwd; sanitized environment identity; start/end,
duration and native exit; complete raw stdout/stderr; resource samples and stop
reasons; authorization and ownership scope. New records only, including partial
failures. Do not place output inside the historical backup or prior B2 evidence.

Required chain: producer hold and native backup coverage -> exact graceful-stop
record -> no-writer proof -> stopped disk identity/format/backing inventory ->
direct-clone results -> all full-hash comparisons/new manifests -> analysis
pre-hash -> attachment plist/device mapping -> OS read-only/unmounted and UUID/
geometry/features -> actual one-check output/exit -> safe exact-device detach ->
post-hash/source-stability evidence -> reviewed interpretation and decision case.

“B3 procedure completed safely” and “filesystem clean” are separate results.
A safe exit-4 assessment can complete the procedure while health still fails.
Native dump archive listing is not application restore validation. No paid model
execution or engineering tests are implied by any preservation success.

## 9. Journal, repair, data recovery and promotion are different authorities

| Option | Purpose and allowed target | Additional approval and risk |
|---|---|---|
| A: no-write assessment | One current-state derivative, OS read-only, no mount, `-n` | Future P approval; no correction, journal may remain unprocessed |
| B: journal recovery trial | A **new disposable derivative** of verified current backup | Separate write approval; replay changes metadata and may expose damage; budget COW and recheck afterward |
| C: filesystem repair trial | Another approved disposable derivative | Separate repair decision with exact checker/options/backup/resource plan; may reconnect/orphan/drop files or metadata |
| D: application-data recovery/export | Approved derivative or validated logical archive, new destination | Separate extraction/scope/privacy/consistency approval; untrusted metadata and incomplete DB/layer recovery risk |
| E: promotion/restoration | Separately chosen profile/destination and rollback plan | Separate high-impact approval; boot/data/config coherence, later writes and data loss must be evaluated |

No B–E operation is authorized by Q or a no-write P approval. Never target the
historical/current immutable backup for recovery; never automatically overwrite
live disks or substitute old images. Successful trial repair does not authorize
promotion. A journal-required no-write result may be inherently insufficient to
certify health; report that limitation rather than invent a PASS. Do not prescribe
repair if Q/current-state findings show only a historical flag needing expert
interpretation. Write-capable commands are intentionally withheld until scope,
necessity, exact derivative and capacity have been reviewed.

## 10. Defensible current-state health acceptance policy

The blocker is sticky. Do not clear it using Docker readiness, image inspection,
container execution, rw mount, recovery-complete text, a historical snapshot,
successful synthetic tests or an empty/incomplete log capture.

A future offline result is acceptable only if:

1. It derives from the correctly identified **latest quiesced/stopped state**,
   after later activity, with complete provenance and stable writer exclusion.
2. Supported exact checker completes all required passes, native exit **0**,
   no unresolved metadata findings, no unsupported/I/O/resource limitation, no
   unprocessed required journal, unchanged pre/post content hashes.
3. Journal and superblock state are coherently interpreted. ERROR_FS or required
   recovery still present prevents unconditional health acceptance. A nonzero
   historical error_count alone is context, not permission to zero flags; tie
   first/last times to the incident and document a justified resolution. An
   unexplained active error state or skipped required replay stays BLOCKED.
4. Independent reviewer assesses complete output, hashes, identity, flags and
   limitations. Coordinator interpretation is not self-certification.

Even then label **OFFLINE_METADATA_CONSISTENCY_PASSED**, not universal data
integrity or live-health PASS. A stopped VM has no new boot evidence. Separately
authorized same-profile start is write-capable and may replay a journal; its
policy must be approved explicitly. Collect full boot-scoped kernel and Docker/
containerd logs with collection exits/completeness/boot ID/disk association and
no new/repeated unresolved warning. Compare error history, do not erase it.
Only an explicit append-only superseding acceptance record can clear the current
infrastructure blocker; keep both prior records. Relevant Docker layer/data and
native DB/Redis health still need later authorized non-destructive validation.

Snapshot consistency alone does not prove every user file/database row correct.
Application invariants, hashes of known content, layer access, database validity
and finally controlled engineering tests provide different evidence. If the
read-only envelope cannot establish these prerequisites without a write, stop
at BLOCKED and request the precise write decision. No return to Phase 10
infrastructure testing merely because P's checker exits zero.

## 11. Recovery decision tree (A–G)

All cases protect the historical backup/B2 evidence, new verified backups if
available, current originals, native stores, host bind mounts, source/Git and
uncommitted work. No case authorizes pruning, cleanup, replacement or an automatic
restart/restore. “Rollback” below means retaining known evidence/state until a
separately approved recovery choice, not writing old data over current disks.

### A — Current-state assessment appears clean

- Interpretation: supported complete exit 0 plus clean journal/flags/provenance
  can pass **offline metadata consistency only**. A skipped required journal or
  active error flag routes to B/D rather than A.
- Risk: unverified user content, flags/history, native application state and
  behavior after a future start; clean snapshot not universal live certification.
- Assets/action: preserve originals/new backups/derivative and native stores;
  independently review record, then prepare separate same-profile start/log and
  application validation plan. Do not dispatch tests.
- Authority: P covered only completed assessment. Start/replay policy and later
  verification require explicit approval; no B–E write authorization inferred.
- Rollback/stop: leave VM Stopped; retain all copies. Stop on any missing identity,
  hash, flag interpretation, source stability or new health warning.

### B — Errors plausibly related to an unprocessed journal

- Interpretation: raw pre-replay consistency is not post-replay consistency;
  neither guaranteed benign nor necessarily permanent damage.
- Risk: replay could fail or leave other errors; trial writes/COW can consume
  storage or alter recovery evidence.
- Assets/action: retain read-only assessment and all originals; expert-select a
  separate derivative journal-only trial plan if genuinely needed, followed by
  another separately scoped assessment. Do not replay the preserved backup.
- Authority: **separate journal-write approval**, exact command/derivative/storage
  budget; P alone is insufficient.
- Rollback/stop: retain unmodified backup, abandon trial logically without deleting
  it; no promotion. Stop on capacity/protection/feature/I/O or ambiguous results.

### C — Structural damage remains or is strongly indicated

- Interpretation: metadata findings may require recovery; assess journal context
  before asserting persistent post-replay corruption or file-content loss.
- Risk: repairs can discard/reconnect metadata, change filenames and lose Docker/
  DB consistency; replacement images could conceal lost execution evidence.
- Assets/action: preserve all sources and trial history; obtain specialist review
  and prioritize scoped application export from a new derivative when justified.
  Compare repair versus data-recovery strategies, ideally on external storage.
- Authority: separate **repair** and/or **export** approvals; promotion a later
  separate decision. No blanket `-y` or restore-as-default policy.
- Rollback/stop: originals/verified backups untouched; no automatic restoration.
  Stop on unbounded damage, low resources, missing content or invalid data claims.

### D — Checker cannot complete or evidence is insufficient

- Interpretation: unsupported features/device access, missing passes, signals,
  exit bits 8/16/32/128 or incomplete output mean **UNVERIFIED**, not clean.
  Decode all bits; 1/2 or content change contradict intended no-write operation.
- Risk: false certification, repeated scans, privileged/writable fallback.
- Assets/action: preserve partial logs, all disk files and native/source data;
  wait for checker exit and safely detach only its derivative if possible.
  Diagnose tool/resource issue from evidence without another check.
- Authority: revised-tool/permission/second-attempt approval if needed; no source
  build, installation, sudo, alternate-superblock or writable fallback implied.
- Rollback/stop: leave actual VM/attachment state documented; do not force-detach
  a busy device. Stop before rerun or treating observer exit as checker result.

### E — Host capacity or memory unsafe

- Interpretation: failed resource gate invalidates entry/continuation regardless
  of apparent filesystem result. Other host activity can consume reserves.
- Risk: ENOSPC, swapping, VM write failures or interrupted preservation.
- Assets/action: before stop, perform no lifecycle action. During owned hash/check
  halt affected work safely, keep logs/partial files; no process termination or
  cleanup of existing data. During shutdown record actual state, do not force it.
- Authority: user frees capacity/closes applications manually or approves a new
  external-storage/resource plan. No prune/delete/cache removal implicit.
- Rollback/stop: no restore/restart; retain backups and report whether attachment
  remains. Resume only after a fresh full qualification window and approval.

### F — Disk identity or read-only protection fails

- Interpretation: target not proven correct/safe; checker must never start.
- Risk: wrong-device damage, mounted target/journal writes, changed source.
- Assets/action: protect originals/backups/native stores; capture discrepancy and
  safely detach only a conclusively identified newly attached derivative. Do not
  guess a device number or detach an unrelated host disk.
- Authority: revised mapping/protection/privilege plan approval; no chmod,
  writable attach, mount or partition extraction fallback.
- Rollback/stop: no check/replay; if mapping is ambiguous, preserve actual state
  and request direction rather than issue an unsafe detach. Hash any safely
  detached derivative and quarantine a mismatch without deletion.

### G — Current-state preservation cannot safely complete

- Interpretation: failed clone/hash/manifest, remaining writer, unexpected
  backing file, incomplete native backup, unqualified stop or autostart makes a
  current verified checkpoint unavailable.
- Risk: only unverified/partial snapshots; losing data by proceeding or confusing
  them with the historical verified backup.
- Assets/action: keep historical evidence and untouched originals/native stores;
  label partial new files FAILED/UNVERIFIED, record errno/actual state. No analysis
  attachment/check unless the approved current checkpoint genuinely verifies.
- Authority: amended source list, downtime method, DB/export coverage or external
  transfer approval. Do not retry as a full copy or repair a source to clone it.
- Rollback/stop: pre-stop failure leaves VM as observed; post-stop failure leaves
  it stopped if it actually stopped. No automatic restart, delete or restore.

## 12. Phase 10 continuity and work remaining after B3

Safe while blocked: read-only architecture review; existing result/provenance
analysis; health-classifier **design**; synthetic regression **planning**;
independent-audit preparation; documentation and requirement traceability. This
planning authorization does not itself implement classifier changes or run tests.
Do not invoke Docker engineering workers, live DB scenarios or paid Gemini.

After separately accepted current health: implement/independently verify the P1
fail-closed health classifier; strengthen the P2 direct failure -> debug fix ->
rejection -> changed patch -> fresh exact-patch QA/code/security review chain;
prove PM/Architect/EM planning snapshot reads and typed handoffs; real sandbox
commands, Git patches, independent QA/review/security, bounded debugging/rework,
leases/cancellation/accounting/idempotency; supported target Frontend/DevOps
toolchain behavior without a SYNTRA UI. Rerun focused failures, complete suite,
static checks and all mandatory supported manual scenarios, isolated to new
test-owned resources. Preserve the old container/images/volumes/worktrees.

Retain historical failed/interrupted suites; no new full/static/manual result
was produced here. Native service recovery/validation, independent hostile audit,
26-item final acceptance matrix, completion report and handover remain open.
Deterministic model decisions with real Docker effects are not live Gemini.
Live Gemini stays **UNVERIFIED**, optional under original policy and requiring
separate usable credentials, exact authorized model/budget and actual successful
provider response. No Phases 11–13, SYNTRA frontend, deployment or GitHub push.

## 13. Risk/status matrix

| Requirement | Disposition at this planning checkpoint |
|---|---|
| B1 exact trusted tool provisioned | PASSED retained evidence; binary hash freshly matches; no reinstall/checker run |
| B2 protective procedure | PASSED retained evidence; evidence-file index freshly verified |
| B2 historical metadata cleanliness | FAILED, native exit 4, journal skipped |
| Historical backup latest full integrity | PASSED in B2; fresh metadata/manifests match, no new full image hash claim |
| Latest observed >=8 GiB and >=5 GiB reserve | PASSED observation only |
| Proposed >=12 GiB pre-stop gate | PASSED at 16:21:40; previously failed; needs approval and immediate recheck |
| Strict memory qualification | PASSED measured window; later NORMAL follow-up, no extra swap-outs; repeat before work |
| No running Docker containers | PASSED observed inventory, not future downtime authorization |
| Global producer quiescence | UNVERIFIED |
| Native DB/Redis current-state backup coverage | BLOCKED on Q scope, ownership, consistency and export budget |
| Guaranteed acceptable graceful stop path | UNVERIFIED; execution BLOCKED until qualified |
| Current-state VM preservation and check | BLOCKED pending prerequisites and new explicit P authorization |
| Current live filesystem/data integrity | UNVERIFIED; BLOCKED_FILESYSTEM_CHECK_REQUIRED persists |
| Later tests/final independent audit/Phase 10 acceptance | BLOCKED / REQUIRES_WORK |

Final B3 risk: **high impact if executed incorrectly; planning and limited
inspection completed without recovery execution**. Neither historical damage
nor currently improved resources authorizes repairing the VM. Same-device clones
reduce logical-overwrite risk, not physical-device risk. No plan can promise
zero loss with an already damaged live filesystem; disclose remaining uncertainty.

## 14. What can share one later execution authorization

Once Q closes stop/native-scope gaps, one conditional **P** authorization can
cover the reviewed producer hold, bounded host/native preservation, **one**
acceptable graceful stop, stopped-state boot/data backup (two clone attempts),
verification/config/log preservation, **one** data analysis clone, one read-only
unmounted attach/check/detach and post-hash/evidence report. No extra prompt is
needed between its routine gates if all exact preconditions remain true.

Any changed package/tool, source/backing-file set, unrelated workload, DB export
scope, permission, shutdown semantics or resource requirement stops P. A failed
stage does not authorize retries, lifecycle recovery or force. Successful P ends
Stopped. Journal/repair/export-from-damaged-data/promotion and restart are not in
that no-write-assessment envelope and require their own explicitly scoped
decisions. Do not use broad earlier B3 wording to consume those approvals.

## 15. One consolidated approval request — next safe stage B3-Q ONLY

**Please authorize B3-Q: a bounded resource recheck and read-only qualification of
the existing `default` profile's shutdown/runtime policies and native
`localhost:5432/{syntra_dev,syntra_test}` / `localhost:6379` persistence, size and
ownership requirements, using the exact query scope in section 7-Q.**

This includes the limited guest SSH read commands and their incidental auth/log
writes, existing normal-user PostgreSQL/Redis read-only queries, selected relevant
host autostart/process/configuration reads, and new private timestamped evidence.
It excludes key values, application-data export, producer/service termination,
Colima stop/start, clones/snapshots, attachment/mount, checkers, repairs, installs,
Docker/database mutations, tests and provider calls. If a read needs additional
privilege or broadened data scope, stop and report it rather than escalating.

Q must stop with the exact native preservation manifest/budget and a qualified
nonforcing-stop proposal, or unresolved blockers. **Q approval is not conditional
authority to proceed to P.** The purpose of this narrower next stage is to avoid
asking for shutdown/backup execution while critical prerequisites are unknown.
All future P/Category C decisions remain unapproved. No additional action is
taken until the user responds.
