# Phase 10 controlled recovery: storage and authorization preflight

Measured 2026-10-16, approximately 00:20–00:21 CEST (Europe/Budapest).
**Recovery has not begun. Explicit authorization is still required.**

## Current infrastructure and preservation checks

- Existing Colima `default` profile is running: macOS Virtualization.Framework,
  arm64, 2 CPUs, 4 GiB RAM, 100 GiB configured data disk. No profile change made.
- Docker context is `colima`; Engine 29.5.2 API responds. This alone is not a
  storage-health pass. The previously diagnosed APFS ENOSPC / guest journal-abort
  incident remains unresolved; no write probe or new container was attempted.
- Container inventory contains one dead container and no running containers:
  `syntra_sandbox_033e7b19-5182-431a-8059-653ff4329b4a_1`, ID `a178d7fd1428`.
  It remains untouched. Startup may perform normal journal/daemon recovery;
  no deliberate removal of this existing container is authorized.
- Git HEAD is unchanged at `998c00c4a7384851667dd5ea648533eddf29b92d`.
  All existing dirty/untracked implementation and report changes are preserved.
  `git diff --check` passes. No commit, checkout, reset or push occurred.
- Earlier execution evidence remains in
  `.syntra/phase10-evidence/2026-10-15-delivery/` (172 KiB allocated at this check).
  No artifact or original log was rewritten.

## Exact measured storage, versus safety budgets

Measurements use `stat` logical bytes and allocated 512-byte blocks, `du -sk`,
`df -k`, and `diskutil info`. GiB = 1,073,741,824 bytes. The VM is still running,
so log sizes and allocations can change; final backup sizes must be remeasured
after an authorized graceful stop.

| Source | Logical size | Allocated bytes now |
|---|---:|---:|
| VM boot disk, `_lima/colima/disk` | 21,474,836,480 bytes (20 GiB) | 1,150,054,400 |
| VM data disk, `_lima/_disks/colima/datadisk` | 107,374,182,400 bytes (100 GiB) | 966,623,232 |
| Both disks combined | 128,849,018,880 bytes (120 GiB) | 2,116,677,632 (about 1.971 GiB) |
| Entire three profile/disk directories below, including configuration/logs/metadata | Not used as a flat-copy requirement | 2,137,362,432 (about 1.991 GiB), from `du` |

The three measured directories are:

1. `/Users/thedeepakreddy/.colima/_lima/colima` — 1,143,288 KiB allocated.
2. `/Users/thedeepakreddy/.colima/_lima/_disks/colima` — 943,968 KiB allocated.
3. `/Users/thedeepakreddy/.colima/default` — 12 KiB allocated.

The capture includes the two disks plus regular configuration, VM identity/EFI
state, and relevant log files. IPC sockets and runtime lock files are not copied
as restorable data. Raw incident kernel/service logs must be exported before
stopping the VM. Preserve file permissions; do not expose configuration secrets
in a printed inventory or report.

Host `df -k` reported **8,069,271,552 bytes available (7.515 GiB), 97% used**.
`diskutil` separately reported 8,277,426,176 bytes of container free space;
these measurements have different accounting and timing. Use the lower
filesystem-available value for the gate and recheck immediately before action.

### Copy method and capacity decision

- A normal fully materialized backup of both disks requires at least **120 GiB
  plus metadata/logs** and cannot fit. It must not be attempted.
- APFS clone or verified sparse preservation avoids expanding holes. The source
  disks and proposed destination parent have the same filesystem device ID,
  `16777233`, and the volume is APFS. This makes a same-volume clone feasible
  in principle; clone success has **not** been tested because copying is not
  authorized. Clone metadata, copy-on-write growth and future test writes are
  not exactly predictable from today's file sizes.
- Proposed conservative gate: **3 GiB backup/COW budget + 5 GiB free operating
  reserve = 8 GiB available before starting this same-volume recovery plan**.
  These are explicit engineering safety budgets, not measured ext4/Colima
  requirements or a guarantee against concurrent host allocations.
- Current capacity is **520,663,040 bytes (about 496.54 MiB) below that gate**.
  Therefore the same-volume recovery is **BLOCKED_BY_CAPACITY** now, even though
  a clone's initial metadata alone could fit. Do not initiate recovery until the
  gate passes or a separately approved destination/capacity plan is agreed.
- No user data will be deleted to make space. The user can provide additional
  host free space or an adequately sized external destination. Space must be
  rechecked after backup and before boot; preserve at least the proposed 5 GiB
  operating reserve before starting. Abort on a failed clone; never fall back
  silently to a 120 GiB full copy.

## Exact proposed destinations — not created

Stopped-state backup:

```text
/Users/thedeepakreddy/SYNTRA/.syntra/infrastructure-backups/20261016T002121+0200/
```

Fresh verification evidence, separate from previous runs:

```text
/Users/thedeepakreddy/SYNTRA/.syntra/phase10-evidence/20261016T002121+0200-recovery/
```

`.syntra/` is Git-ignored. No backup directory or disk copy was created. A clone
on the same APFS volume is a rollback copy, **not** an independent backup against
physical host-disk failure or deletion of the whole volume. An external backup
offers stronger isolation but needs a user-specified destination and new
capacity assessment. Do not silently change the approved destination.

## Staged action proposed for explicit approval

1. Once the capacity gate passes, preserve scoped raw logs, capacity measurements,
   source/Git status and inventories in the new evidence location. Recheck that
   no new running containers have appeared.
2. Gracefully stop the existing `default` Colima profile without `--force`.
   If stopping fails, report it and stop; do not force or reset.
3. Confirm the VM is stopped and the disk files are no longer open by its VM
   process. Remeasure sources and capacity, then clone/sparsely preserve the
   approved disks, configuration and logs into the exact new backup directory.
   Verify file sizes, permissions, manifests and content checksums while the VM
   is stopped. A byte-verified backup preserves the failed state; it does not
   certify the ext4 filesystem as consistent.
4. Start the **same** profile once without recreating it or changing storage.
   Normal boot/journal replay changes disk state, hence the backup-first order.
5. Read new kernel, Docker and containerd logs, filesystem/capacity state, container
   inventory, and inspect `syntra-sandbox:latest` and
   `syntra-phase10-acceptance:local`. Stop immediately if storage errors persist:
   no test creation, retries, repairs, pruning or image replacement. If another
   VM stop is needed, request authorization unless already explicitly granted.
6. Only after health checks pass, execute the previously failed real Docker
   acceptance modules, complete automated suite, static checks and manual
   scenarios 01–13. Preserve complete new outputs, actual exit codes, timings,
   actual patches and reviewer/rework evidence in the new evidence directory.

Explicit approval should also clarify permission for **new disposable test
resources** to be created and cleaned up by the already requested test harness.
This does not authorize removal of the pre-existing dead container, images or
volumes. No filesystem repair, remount, forced shutdown, prune, VM reset,
destructive cleanup or image replacement is included in the proposed approval.

## Verification and audit status

| Status | Requirement |
|---|---|
| PASSED | Current read-only inventory, exact storage measurements, unchanged HEAD/evidence and whitespace check |
| FAILED (previous run) | Last full suite: 372 passed, 15 failed, 7 skipped; Docker image-store I/O errors |
| BLOCKED | Capacity gate and explicit recovery authorization; no stop/start/copy has occurred |
| BLOCKED | Fresh real-infrastructure tests, full suite and manual reruns pending healthy authorized recovery |
| UNVERIFIED | Latest-tree real planning snapshots, handoffs, sandbox edits, patches, QA/review and bounded debugging/rework until live rerun passes |
| UNVERIFIED | Live Gemini; no new authorized provider invocation succeeded |

The earlier independent audit closed four P1s in the tested paths, not the live
infrastructure acceptance gap. No new audit/completion sign-off is claimed.
Deterministic model decisions with real infrastructure must remain distinct from
live Gemini and from simulated-container tests. Phase 10 remains
**PHASE_10_REQUIRES_WORK**. Phases 11–13 and the SYNTRA frontend remain unstarted.
