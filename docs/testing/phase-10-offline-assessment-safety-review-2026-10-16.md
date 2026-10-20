# Phase 10 — offline filesystem assessment safety review

Date: 2026-10-16, Europe/Budapest. **PLAN ONLY — NOT AUTHORIZED FOR EXECUTION.**

**Verdict: PHASE_10_REQUIRES_WORK.** The authoritative infrastructure state remains
`BLOCKED_FILESYSTEM_CHECK_REQUIRED`. No offline filesystem checker has been run.
This report does not authorize repair, another Colima stop/start, disk attachment,
Docker changes, further tests, or Phases 11–13/frontend work.

Labels: **CONFIRMED** = directly observed or retained execution evidence;
**LIKELY** = supported inference; **UNKNOWN** = insufficient evidence;
**UNVERIFIED** = proposed capability or acceptance condition not demonstrated.
Historical observations are explicitly distinguished from current measurements.

## 1. Current filesystem status

**CONFIRMED, captured latest recovery boot:** at 00:36:33 CEST, `vdb1` reported:

```text
Filesystem error recorded from previous mount: IO failure
Marked fs in need of filesystem check.
warning: mounting fs with errors, running e2fsck is recommended
recovery complete
```

It subsequently mounted read/write. That does not clear the preceding warnings.
`health-review.json` supersedes the optimistic original `health-result.json`;
both original records and the executed helper remain unchanged.

**LIKELY:** host APFS ENOSPC caused virtual-disk write failures and an aborted
guest ext4 journal. This is supported by the October 15 host/guest logs and the
infrastructure diagnosis, not merely inferred from Docker failures.

**UNKNOWN:** present metadata consistency, whether application data was lost,
whether only historical error state remains, and whether any repair is needed.
Readable image metadata is not a verification of all layers, volumes, or data.
No new guest session was opened during this review: even diagnostic SSH can
write guest authentication/service logs. Current live guest state was not polled.

Evidence reviewed: controlled recovery report, independent audit, infrastructure
diagnosis, both health JSON records, full captured pre/post-recovery kernel and
Docker/containerd logs, backup manifest, source integrity manifest, and helper.
The post-start service-log capture had no matching storage failures; that limited
window cannot override the kernel warnings or establish ongoing health.

Evidence root:

```text
/Users/thedeepakreddy/SYNTRA/.syntra/phase10-evidence/20261016T002121+0200-recovery/
```

## 2. Existing backup integrity and actual disk layout

**CONFIRMED:** the original stopped-state backup remains available at:

```text
/Users/thedeepakreddy/SYNTRA/.syntra/infrastructure-backups/20261016T002121+0200/
```

All **15 backed-up regular files** were read and rehashed in this safety review;
all sizes and SHA-256 values match `manifest-verified.json`. The historical
manifest also records distinct source/clone inodes and source/backup equality
verified while Colima was stopped. No backup contents were changed here.

| Preserved file | Logical bytes | SHA-256 |
|---|---:|---|
| `vm/disk` | 21,474,836,480 | `4792e5ff49a975ca34d78cf552f59a9fbe8b09a2391ae114c5daca57e9524f45` |
| `data/datadisk` | 107,374,182,400 | `9de7d661f8d4c4a7fce36ad6a54f74d235df57e0d6328da080a8aa3aaf2b12dd` |

Backup directories are private, mode 0700. Do not change backup permissions,
attach the original, or place analysis output inside it. APFS clones share the
physical device: they are not independent protection against host disk failure.

Read-only byte parsing of the preserved data disk confirms:

| Property | Observed value |
|---|---|
| Container format | Raw disk, protective MBR, GPT |
| GPT validation | Primary header and partition-entry-array CRCs match |
| Linux filesystem partition | Entry 1; type `0fc63daf-8483-4772-8e79-3d69d8477de4` |
| Sector size / first / last LBA | 512 bytes / 2048 / 209713151 |
| Partition byte offset | **1,048,576** |
| Partition byte length | **107,372,085,248** |
| ext4 magic / block size | `0xEF53` / 4096 bytes |
| Filesystem UUID | `3de9071f-0361-4f65-88a3-f223f8faacb2` |

This identifies the layout, not filesystem consistency. Do not check the whole
GPT image as if its ext4 superblock were at byte zero. The protective MBR's LBA 1
is not the ext4 partition start. Backup GPT and complete ext4 structures have
not undergone consistency checking.

The source manifest contains 444 source-file records. The prior recovery checked
them before intentionally updating reports, with no unexpected changes. It is
not a VM-filesystem manifest, a database backup, or proof that every current
source file still matches after those documented report updates. Git HEAD
remains `998c00c4a7384851667dd5ea648533eddf29b92d`; existing dirty work is preserved.

## 3. Proposed offline assessment procedure

Preferred conditional method: **host-native e2fsprogs, a new APFS analysis clone
of the preserved data disk, an unmounted OS-read-only partition device, and
`e2fsck -f -n`**. Do not use Docker or the running Colima guest as the assessment
environment. Host-native device access/build compatibility remains UNVERIFIED.

1. Obtain separate tool-provisioning approval or an approved existing trusted
   binary; identify version, binary hash, supported features, configuration and
   dependencies. Recheck capacity and memory before provisioning or examination.
2. Create a private, new timestamped analysis directory outside the backup.
   Recheck the source data-disk hash. Use direct `clonefile`, fail closed, without
   a materialized-copy fallback. Verify distinct inode, identical size and hash.
3. Attach **only the new clone**, explicitly `-readonly -nomount -noautofsck`.
   Raw image recognition must be explicit. Record the returned device inventory.
4. Resolve devices from this attachment's plist, never from a guessed disk
   number. Independently verify whole-device/partition identity, read-only media,
   no mounts, GPT geometry and ext4 UUID. Abort before the checker if any check
   is unavailable, ambiguous, inconsistent, or not read-only.
5. Run one approved no-write assessment against partition 1, not the live guest
   device or whole image. Capture stdout, stderr, exit bitmask, timing, tool hash
   and snapshot hash. Stop on host/storage errors or resource pressure.
6. Detach only the newly attached analysis whole device, without force. Verify
   its disappearance, rehash the analysis image and original preserved data
   image, and compare to the pre-assessment hash. Preserve all outputs and clone.
   Do not delete it automatically or reuse the earlier evidence directory.

**Journal limitation:** upstream e2fsck's no-write path skips required journal
recovery. Its report can therefore reflect an unreplayed historical snapshot;
apparent inconsistencies need interpretation, not automatic repair. See the
[upstream implementation](https://raw.githubusercontent.com/tytso/e2fsprogs/master/e2fsck/unix.c).
Do not replay the journal to obtain a more reassuring result without separate
write authorization. Linux documents that even a normal ext4 read-only mount
can replay the journal and write data. **No mount is proposed**, including a
`ro,noload` mount. See the [kernel documentation](https://cdn.kernel.org/doc/html/latest/admin-guide/ext4.html).

Crucially, this backup predates the restart, journal replay and completed tests.
Its assessment is historical. Even a clean result cannot certify the current
live filesystem or automatically clear its blocker. A current stopped-state
snapshot would require a separately approved graceful stop and fresh backup;
it is not included in this proposal.

## 4. Exact commands proposed — DO NOT RUN YET

These are staged commands, not an unattended script. Stop between stages for
the stated gates. Commands below have **not** been executed. Device and checker
variables must be populated only from verified observations after approval.

### Stage A: capacity and trusted tooling

```sh
df -k /Users/thedeepakreddy/SYNTRA
sysctl -n hw.memsize
command -v e2fsck
```

The host has no executable `e2fsck`, `debugfs`, `dumpe2fs`, `qemu-img` or `fuse2fs`
on PATH; common Homebrew e2fsprogs binary/Cellar locations are absent. Guest
tool availability is UNVERIFIED; do not SSH merely to discover it. `hdiutil`
exists; only its help/manual was consulted. Homebrew publishes macOS e2fsprogs,
but that is not proof of an installed or suitable build. See the
[official formula](https://formulae.brew.sh/formula/e2fsprogs).

No installation command is approved or prescribed until package/dependency
sizes and effects are resolved. Installing a package is a host WRITE/network
operation, not a read-only prerequisite. No automatic Homebrew updates, cleanup,
global configuration changes or new VM provisioning are authorized.

### Stage B: new fail-closed clone — WRITE, requires approval

The proposed Python command creates only the new analysis directory/image and
a pre-assessment hash record. It never opens the preserved image for writing.
It deliberately has no copy fallback and refuses an existing destination.

```sh
python3 - <<'PY'
import ctypes
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

source = Path('/Users/thedeepakreddy/SYNTRA/.syntra/infrastructure-backups/20261016T002121+0200/data/datadisk')
root = Path('/Users/thedeepakreddy/SYNTRA/.syntra/phase10-offline-assessment')
expected = '9de7d661f8d4c4a7fce36ad6a54f74d235df57e0d6328da080a8aa3aaf2b12dd'
def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
def capacity_gate():
    stat = os.statvfs(source.parent)
    if stat.f_bavail * stat.f_frsize < 8 * 1024**3:
        raise SystemExit('STOP: below proposed 8 GiB gate')

capacity_gate()
if source.is_symlink() or not source.is_file():
    raise SystemExit('STOP: unexpected source')
if source.stat().st_size != 107374182400 or digest(source) != expected:
    raise SystemExit('STOP: preserved image mismatch')
if root.is_symlink():
    raise SystemExit('STOP: unexpected destination root')
root.mkdir(mode=0o700, exist_ok=True)
work = root / datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%z')
work.mkdir(mode=0o700, exist_ok=False)
target = work / 'datadisk.analysis.raw'
if source.stat().st_dev != work.stat().st_dev:
    raise SystemExit('STOP: not on the same filesystem')
capacity_gate()
libc = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
libc.clonefile.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
libc.clonefile.restype = ctypes.c_int
if libc.clonefile(os.fsencode(source), os.fsencode(target), 0) != 0:
    error = ctypes.get_errno()
    raise OSError(error, os.strerror(error))
if source.stat().st_ino == target.stat().st_ino:
    raise SystemExit('STOP: clone identity invalid')
if target.stat().st_size != source.stat().st_size or digest(target) != expected:
    raise SystemExit('STOP: analysis clone mismatch')
with (work / 'before.json').open('x') as out:
    json.dump({'source': str(source), 'analysis': str(target),
               'bytes': target.stat().st_size, 'sha256': expected}, out, indent=2)
print(work)
PY
```

Stop if the gate fails; leave any partial new evidence intact for review. Record
the returned absolute directory as `ASSESSMENT_DIR`; set `ANALYSIS_IMAGE` to its
`datadisk.analysis.raw`. Verify path ancestry/no symlink redirection before use.
Do not choose an arbitrary older directory if a creation step fails.

### Stage C: read-only attachment — host CONTROL-PLANE WRITE

```sh
hdiutil attach -imagekey diskimage-class=CRawDiskImage -readonly -nomount -noautofsck -plist "$ANALYSIS_IMAGE" > "$ASSESSMENT_DIR/attach.plist" 2> "$ASSESSMENT_DIR/attach.stderr"
plutil -p "$ASSESSMENT_DIR/attach.plist"
```

Any attach failure stops the assessment. Resolve `WHOLE_DEVICE` and
`PARTITION_DEVICE` from `system-entities` in this successful attachment only.
Require exactly one new whole disk with the expected GPT and its Linux
partition 1. There is deliberately no prefilled `/dev/diskN` target.

```sh
diskutil info -plist "$WHOLE_DEVICE" > "$ASSESSMENT_DIR/whole.plist"
diskutil info -plist "$PARTITION_DEVICE" > "$ASSESSMENT_DIR/partition.plist"
diskutil list -plist "$WHOLE_DEVICE" > "$ASSESSMENT_DIR/layout.plist"
mount > "$ASSESSMENT_DIR/mounts.txt"
hdiutil info -plist > "$ASSESSMENT_DIR/attachments.plist"
```

These commands read OS state and write new evidence files. Before proceeding,
validate that this image maps to this whole device; `WritableMedia` is false
and effective `Writable` is false on the relevant devices; no nonempty
`MountPoint` or mount-table entry exists for any attached child. Confirm the
recorded byte geometry and ext4 magic/UUID through read-only device reads.
Host APFS metadata confirms that `Writable`, `WritableMedia` and
`WritableVolume` are actual local plist field names; their values on the future
analysis device are not yet known. Missing fields or inability to verify the
protection means STOP, not assumed safety. Native attachment/partition exposure
may fail; do not switch to a writable attachment, mount, extraction, or guest VM.

### Stage D: checker — target READ ONLY; evidence files WRITE

`E2FSCK` must be the approved absolute native binary, not an untrusted PATH
substitution. Record its version/hash after separate tool approval. Use a clean
environment and no inherited e2fsck configuration:

```sh
if env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin LC_ALL=C E2FSCK_CONFIG=/dev/null "$E2FSCK" -f -n -v -E nodiscard "$PARTITION_DEVICE" > "$ASSESSMENT_DIR/e2fsck.stdout" 2> "$ASSESSMENT_DIR/e2fsck.stderr"; then
    CHECK_EXIT=0
else
    CHECK_EXIT=$?
fi
printf '%s\n' "$CHECK_EXIT" > "$ASSESSMENT_DIR/e2fsck.exit"
```

No `-p`, `-a`, `-y`, bad-block scans, journal-only replay, optimization,
alternate-superblock repair, discard, or repair fallback is permitted.
Unsupported options/features, missing dependencies, target-access failures or
signals produce an incomplete assessment. Do not retry with weaker protection.
The [upstream manual](https://raw.githubusercontent.com/tytso/e2fsprogs/master/e2fsck/e2fsck.8.in)
documents no-write/forced checking and exit bitmasks. This command's suitability
still depends on the approved native build and verified unmounted device.

### Stage E: exact-device detach and integrity records

```sh
hdiutil detach "$WHOLE_DEVICE" > "$ASSESSMENT_DIR/detach.stdout" 2> "$ASSESSMENT_DIR/detach.stderr"
hdiutil info -plist > "$ASSESSMENT_DIR/attachments-after.plist"
shasum -a 256 "$ANALYSIS_IMAGE" > "$ASSESSMENT_DIR/analysis-after.sha256"
shasum -a 256 /Users/thedeepakreddy/SYNTRA/.syntra/infrastructure-backups/20261016T002121+0200/data/datadisk > "$ASSESSMENT_DIR/original-after.sha256"
df -k /Users/thedeepakreddy/SYNTRA > "$ASSESSMENT_DIR/capacity-after.txt"
```

Detach is a host control-plane mutation. No `-force`; if detach fails, report
the device as still attached and request direction. Hash comparisons must match
the known digest, not merely succeed as commands. Never auto-delete a mismatch.

## 5. Read/write risks, protected data and permissions

| Operation | Classification and boundary |
|---|---|
| Metadata/hash/GPT reads | Read target contents; host caches/logs/access-time metadata may change normally |
| mkdir, clonefile, manifests, transcripts | Host filesystem WRITES, confined to new analysis directory |
| Tool provisioning | Host WRITES/network/dependency effects; separate approval and size review |
| hdiutil attach/detach | Host OS/device/control-plane WRITES; proposed exposed media forced read-only |
| e2fsck with exact approved flags | Target no-write assessment, plus new log WRITES; verify OS protection first |
| Any mount/journal replay/repair | Write-capable; excluded, even a nominal read-only mount is not a shortcut |
| Guest SSH/loop-device setup | Can write live guest logs/change device state; not proposed |

Thus the entire procedure is **not globally read-only**. Its intended guarantee
is no content writes to the original backup, analysis disk, or live VM disks,
with explicitly approved host control-plane/evidence writes. Hashes verify
content preservation afterward but are not a substitute for preventive controls.

| Protected item | Assessment impact and remaining risk |
|---|---|
| Existing images/containers/volumes | No Docker access or modification; snapshot reads do not verify all application data |
| PostgreSQL/Redis | No connections or DB recovery; raw snapshot includes whatever state existed then, not a logical backup |
| Colima configuration/VM boot data | Do not attach the boot disk or edit profile/configuration; no VM lifecycle commands |
| SYNTRA source/Git/artifacts/logs | Read existing evidence; only this new report and future separate assessment outputs are created |
| Original backups | No write handles/attachment; only derivative clone exposed; shared physical storage remains a risk |
| Other development environments/credentials | No package updates, mounts, environment edits or credential reads; tool install effects require review |

Use the normal user for file reads, cloning and evidence. Host device-framework
access needs a less-restricted execution context than the agent filesystem
sandbox; a diagnostic `diskutil info` required that context here. This is not
blanket sudo authorization. If partition reads require elevated privileges,
request narrowly scoped approval for that exact verified device/command; do not
chmod devices or broaden privileges. Keep evidence private: disks can contain
credentials and database data even if this checker does not enumerate file data.

## 6. Storage and memory requirements

**CONFIRMED host measurements:** `df` reported 7,750,872 KiB available
(7.392 GiB). A subsequent APFS metadata read reported 7,935,123,456 bytes free
(7.390 GiB). Small differences reflect ongoing host activity; neither is a
reservation. Installed RAM is 8,589,934,592 bytes (8 GiB); available memory and
checker peak memory are UNKNOWN.

The preserved 100 GiB data image reports 966,623,232 allocated bytes (0.900 GiB).
A same-volume APFS clone initially shares extents; exact new metadata allocation
cannot be promised. No 100 GiB materialized copy or partition extraction fits.

| Resource | Proposed allowance / restriction |
|---|---|
| New analysis disk | One 100 GiB logical APFS clone; no full-copy fallback |
| New physical-storage budget | 1.5 GiB total for clone metadata/COW contingency and logs; engineering allowance, not measured future usage |
| Host operating reserve | At least 5 GiB throughout; stop before reserve is threatened |
| Entry capacity gate | Retain conservative **8 GiB available** gate from recovery; recheck immediately before clone/attach/checker |
| Tool provisioning | Additional download/install/dependency size UNKNOWN; must be separately measured/budgeted |
| Memory | One checker only; measure pressure/swap first; abort rather than increase storage pressure |

**Capacity gate currently FAILS:** approximately 0.61 GiB below 8 GiB, even before
any tool provisioning. Do not begin assessment under current measurements.
No cleanup is authorized here. More free space or a revised, explicitly approved
resource plan is necessary. A separate physical backup would need separate
destination/capacity approval, not a silent relocation or full copy.

## 7. Infrastructure interruption requirements

No Colima shutdown/restart is needed for this historical preserved-copy plan.
The backed-up image is independent of the running VM's logical write path.
Neither live disk is attached or copied. Do not claim no performance impact:
full hashing/checking consumes host disk bandwidth and memory shared with Colima.

Current container activity is UNVERIFIED in this review; no interruption is
proposed, so no Docker call is needed. The recovery evidence records no running
test containers when verification stopped and preservation of old container
`a178d7fd1428`. A current snapshot/repair/restore would require a new activity
inventory and separate interruption authorization.

## 8. Expected diagnostic outputs

New timestamped directory only: tool identity/version/dependency and capacity
records; source/clone geometry, UUID, sizes/inodes/hashes; attach plist and
stderr; device/mount/protection verification; e2fsck stdout/stderr, start/end
times and exact exit code; detach records; post-assessment hash comparisons;
final interpretation tied to snapshot hash and capture time.

Expected checker stages include inode/block checks, directory structure,
connectivity, reference counts and allocation summaries when supported.
Whether journal replay was skipped must be reported prominently. Partial output,
feature incompatibility or a canceled run must never be labeled a full result.

## 9–11. Findings, recovery options and risks

| Possible assessment outcome | Interpretation | Next option; separate approval required | Principal risk |
|---|---|---|---|
| Exit 0, complete supported check, unchanged hashes | No inconsistency found by that checker on that historical snapshot | Review report; consider a fresh current offline snapshot before resolving live blocker | False reassurance about later writes, skipped journal or application data |
| Exit includes 4, or consistency findings | Errors left uncorrected; unreplayed journal may affect interpretation; not automatically irreparable | Expert review; if justified, journal replay/repair trial on a **second disposable derivative**, never original backup | Replay/repair changes evidence and can discard/orphan data; COW growth |
| Exit includes 8/16/128, unsupported features, inability to expose partition | Operational/tooling failure, not proof of corruption | Obtain compatible trusted tooling/separate analysis environment and revised plan | Additional writes, dependencies, transfer exposure and storage needs |
| Exit includes 32 or signal/timeout | Incomplete assessment | Review resource/I/O cause before authorizing another attempt | Repeated scans/swap pressure on nearly full host |
| Exit includes 1/2 or any unexpected disk modification | Contradiction of intended no-write procedure | Stop, preserve clone/logs, investigate protection breach; do not promote result | Potential content changes or wrong target |
| New I/O/ENOSPC or hash mismatch | Safety gate failed; preserve all evidence | Stop assessment; seek storage/device diagnosis and backup plan | Further host/VM writes can worsen loss |
| Severe structural damage confirmed after expert review | Potential recovery needed; extent/application data loss still case-specific | Recovery/export from derivative, application backups, or deliberate restore plan | Lost post-backup work, incomplete DB consistency, restored historical corruption |

Exit values are bitmasks, not an enum: assess all set bits and full output.
Do not clear ext4 error flags, run repair, replay journals, reset Docker, prune,
replace images or restore the historical disk simply to make health checks pass.
If repair is unnecessary, no repair should be performed. If a derivative repair
trial succeeds, promotion to the live profile is a separate high-impact decision,
not an automatic next step.

## 12. Proposed health-classifier correction — NOT IMPLEMENTED

The executed `start_health.py` regex looked for `I/O error`, `input/output error`,
aborted journals, explicit `EXT4-fs error`, read-only remounts and ENOSPC.
The captured warnings instead used `IO failure`, `EXT4-fs warning`, recorded
previous errors, needing a check and mounting with errors. Those strings missed
the regex, so Docker/image/mount successes incorrectly cleared the gate.

Proposed design, subject to implementation approval:

- Extract a pure, deterministic classifier with reason codes and matching log
  lines. Record original decisions and superseding reviews append-only.
- Match case-insensitively: recorded filesystem errors; `IO`/`I/O` failures;
  filesystem-check-required/needs-checking/need-of-filesystem-check variants;
  mounting-with-errors; e2fsck recommended; aborted journals; ENOSPC and the
  existing hard errors. Scope error patterns to relevant storage context rather
  than rejecting harmless text such as ordinary ACPI I/O mapping.
- Treat these warnings as sticky `BLOCKED_FILESYSTEM_CHECK_REQUIRED`, including
  historical-error warnings emitted during the current boot. Later `recovery
  complete`, `rw`, API readiness, image inspection or test passes cannot erase it.
- Missing, failed, truncated, undecodable, stale or wrong-boot evidence is
  `UNVERIFIED`; it must fail the permission-to-test gate. Never treat missing
  matches in missing logs as success.
- A prior unresolved authoritative blocker persists even with otherwise clean
  logs. A historical snapshot's checker exit 0 cannot clear a current-live block.
- Bind any future assessment to disk UUID, snapshot hash/time, tool and complete
  output. Clearing a blocker requires an explicit accepted resolution for the
  correct state, not an arbitrary boolean or a Docker success response.
- Separate `NO_NEW_STORAGE_ERROR_DETECTED` from `FILESYSTEM_CONSISTENCY_VERIFIED`;
  neither automatically means Phase 10 complete or authorizes more operations.

Keep the executed helper and original `health-result.json` immutable. Add future
corrected code/tests outside that historical evidence directory. No application,
recovery-helper or test implementation was changed in this review.

## 13. Required regression tests — proposal only, NOT ADDED OR RUN

Illustrative test contract for a future pure classifier; the module/API below
does not yet exist. These are intentionally not runnable claims of coverage.

```python
import pytest

# Proposed API only; implement after explicit approval.
from syntra.infrastructure.storage_health import classify_storage_health


@pytest.mark.parametrize(
    "warning",
    [
        "EXT4-fs warning (device vdb1): Filesystem error recorded from previous mount: IO failure",
        "EXT4-fs warning (device vdb1): Marked fs in need of filesystem check.",
        "EXT4-fs (vdb1): warning: mounting fs with errors, running e2fsck is recommended",
        "EXT4-fs (vdb1): filesystem check required",
        "EXT4-fs (vdb1): filesystem needs checking",
        "EXT4-fs (vdb1): I/O failure",
    ],
)
@pytest.mark.parametrize("uppercase", [False, True])
def test_storage_warning_cannot_be_overridden_by_success(warning, uppercase):
    warning = warning.upper() if uppercase else warning
    result = classify_storage_health(
        kernel_log=f"EXT4-fs (vdb1): recovery complete\n{warning}\nEXT4-fs (vdb1): recovery complete; mounted r/w",
        service_log="Docker API ready; images readable; tests passed",
        evidence_complete=True,
        boot_matches=True,
        prior_blocker=None,
    )
    assert result.status == "BLOCKED_FILESYSTEM_CHECK_REQUIRED"
    assert result.matched_lines
    assert result.may_continue_testing is False


@pytest.mark.parametrize(
    "complete,boot_matches",
    [
        (False, True),
        (True, False),
        (False, False),
    ],
)
def test_incomplete_or_wrong_boot_capture_fails_closed(complete, boot_matches):
    result = classify_storage_health(
        kernel_log="",
        service_log="Docker API ready",
        evidence_complete=complete,
        boot_matches=boot_matches,
        prior_blocker=None,
    )
    assert result.status == "UNVERIFIED"
    assert result.may_continue_testing is False


def test_superseding_blocker_persists_when_images_are_readable():
    result = classify_storage_health(
        kernel_log="ordinary boot",
        service_log="images readable",
        evidence_complete=True,
        boot_matches=True,
        prior_blocker="BLOCKED_FILESYSTEM_CHECK_REQUIRED",
    )
    assert result.status == "BLOCKED_FILESYSTEM_CHECK_REQUIRED"
    assert result.may_continue_testing is False
```

Also require: every existing hard-error pattern and case variation; combined
warnings without trailing newline; empty/truncated/undecodable capture despite
exit 0; collection nonzero exits/timeouts; wrong VM/disk/UUID; stale boot IDs;
exact replay of the retained 510-line boot capture; benign ACPI I/O messages
not classified as corruption; e2fsck exit bitmask combinations/partial output;
skipped journal never represented as replayed; unsupported tool never healthy;
missing read-only/unmounted proof prevents checking; post-hash mismatch blocks;
historical exit 0 cannot resolve live blocker; superseding review wins over the
original optimistic JSON; no infrastructure test dispatch after a blocked or
unverified classification. Run these first with synthetic inputs only after
implementation approval; keep real infrastructure acceptance separately gated.

The independent audit's existing application-test gaps also remain open:
directly assert failure → fix → rejection → changed patch → fresh exact-patch
review, and distinguish proven PM repository reads from unproven Architect/EM
reads. This safety review neither implements nor reruns those tests.

## 14. Exact approvals needed and stop boundary

There is **no executable assessment approval yet**, and the proposed capacity
gate currently fails. Request these separately, with final paths/tool identified:

1. **Prerequisites:** approve a specific trusted native tool and its provisioning
   effects/storage budget, or supply an approved binary. No general environment
   upgrades. Restore at least the proposed 8 GiB available gate plus any separately
   budgeted installation needs; no cleanup is authorized by this report.
2. **Historical offline assessment only:** approve one new same-volume APFS
   clone of the named preserved data disk under
   `/Users/thedeepakreddy/SYNTRA/.syntra/phase10-offline-assessment/<timestamp>/`,
   integrity verification, unmounted read-only host attachment, one exact
   no-write checker invocation against its verified partition, exact-device
   detach without force, and separate evidence writes. Original backup and live
   VM are excluded from writes. Device-access privilege approval, if needed,
   must name the resolved device and exact command before use.
3. **Classifier work, separately:** approve implementation and synthetic negative
   tests for the proposed correction. This does not authorize Phase 10
   infrastructure tests or modification of historical recovery evidence.

No approval above implies repair, journal replay, another Colima stop/start,
current-live snapshot, disk promotion/restore, deletion, package cleanup, Docker
mutation, or further Phase 10 infrastructure/manual verification. Each would
require a new narrowly scoped plan and authorization.

## Verification verdict retained

| Status | Item |
|---|---|
| PASSED | Preserved backup available; all 15 content hashes/sizes reverified |
| PASSED | GPT/ext4 location identified by read-only byte inspection |
| PASSED, historical | Real infrastructure: 18 passed/1 skipped; QA/planning: 110 passed |
| FAILED | Original classifier missed ext4 warnings; proposed 8 GiB capacity gate currently unmet |
| BLOCKED | Filesystem health sign-off; further infrastructure/full-suite/static/manual reruns |
| UNVERIFIED | Offline consistency, current live data integrity, native checker compatibility, repair necessity |
| UNVERIFIED | Live Gemini; successful retained workflows used deterministic providers with real infrastructure |

Full regression previously stopped with harness exit 130 and no completed suite
result. No new test result is claimed here. Real sandbox/Git/QA/review/debugging
artifacts remain preserved, but do not override the storage blocker. Independent
review findings remain open; this safety review is not an independent completion
sign-off. No Phase 11–13 or SYNTRA frontend work was started.

Only this new safety report was created in this review. No disk was attached or
mounted; no filesystem checker, repair, Colima lifecycle operation, Docker
mutation, implementation change, cleanup or Phase 10 test was performed.

**STOP: await explicit, narrowly scoped authorization after prerequisites pass.**
