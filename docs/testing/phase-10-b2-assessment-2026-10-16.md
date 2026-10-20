# Phase 10 B2 completion — historical offline assessment

Date: 2026-10-16, Europe/Budapest (CEST).

**Procedure: PASSED — completed safely, with unchanged original/clone hashes.**
**Filesystem finding: FILESYSTEM_INCONSISTENCIES_DETECTED.**
**Historical cleanliness: FAILED. Current live integrity: UNVERIFIED.**
**Authoritative infrastructure: BLOCKED_FILESYSTEM_CHECK_REQUIRED.**
**Phase 10: PHASE_10_REQUIRES_WORK.**

Exactly one direct APFS analysis clone, one read-only attachment, and one native
no-write assessment were performed under the user's explicit B2 authorization.
The checker completed all five passes and returned **4**, not 0. No repair,
journal replay, second assessment, Colima lifecycle operation or infrastructure
test occurred. The new derivative and all output remain preserved.

## 1. Authorization, procedure and evidence

Read and followed the current B2 procedure in the B1 provisioning report,
consolidated execution plan and original offline safety review. B1 evidence
review rechecked all 40 indexed campaign files without a mismatch. Native checker
version/hash were freshly verified. Historical statements that B2 was unapproved
or tooling absent remain unchanged in their original dated reports; this report
and consolidated-plan section 14 supersede those statuses only.

User authorization attachment SHA-256:
`36d14ec4a7779c69a2b222250b7ed4e220accd419f6e965ead8b0343c69248e9`.

New owner-only evidence directory (0700):

```text
/Users/thedeepakreddy/SYNTRA/.syntra/phase10-evidence/20261016T153334+0200-b2-assessment/
```

`authorization.json`, retained stage-helper source, exact command records,
raw outputs, resource events, before/after hashes, `completion.json` and
`evidence-sha256.json` are stored there. Old reports, manifests, helpers and
engineering evidence were not rewritten. New helpers stream generated results
to stdout; recorded evidence was saved separately. No secret values were printed.

## 2. Resource and activity prerequisites — PASSED

Strict pre-execution window: **15:33:51.315–15:35:56.114**, five samples over
**124.798 seconds**. All NORMAL; conservative headroom **2.038–2.057 GiB**;
no additional swap-outs. Available capacity remained above 8 GiB.

Before each clone/attach/check stage, capacity and memory were rechecked. Across
**66 monitored stage samples**, pressure was NORMAL and minimum headroom was
**1.956 GiB**. Swap-out counter stayed **3,152,481** throughout. Final resource
sample is additional to those 66. No 5 GiB reserve breach or resource stop.
The proxy remains free + inactive + speculative pages, not guaranteed RAM;
swap occupancy alone was not used to certify readiness.

Read-only infrastructure inventory before and after: same `default` Colima
profile Running, aarch64, 2 CPUs, 4 GiB VM RAM, 100 GiB configured disk.
No running Docker containers. Protected container
`a178d7fd14286308ee1b11e0ccb0678804dbdfd34573f2bf9b5aa910cba40252`
remains Exited (137). Host processes were inspected; no assessment/test activity
requiring interruption was identified. No process was terminated, and no
guest SSH or live-disk content inspection was performed.

One checker, with full inode-map optimization and readahead disabled, fit the
approved resource envelope. Actual checker `time -l` peak RSS was **9,650,176
bytes** (not an advance guarantee); elapsed wall time **0.15 seconds**, observer
elapsed **0.1614 seconds**. It finished before the 2-second in-flight resource
sampler fired, so before/after samples and native process accounting, not a
fabricated continuous peak measurement, support the short-run resource result.

## 3. Preserved backup integrity — PASSED before and after

Original remains exclusively at:

```text
/Users/thedeepakreddy/SYNTRA/.syntra/infrastructure-backups/20261016T002121+0200/
```

All **15 files** were fully rehashed before cloning and after detachment.
Every expected size, mode, owner, backup inode and SHA-256 matched the original
verified manifest. Private backup directory modes remain 0700. No symlink
redirection or alias to the live source was accepted. Files were opened `rb`;
per-descriptor `F_NOCACHE` avoided filling the host cache during large reads.
No backup permissions/content or historical manifests were changed.

Both manifest hashes matched before/after:

```text
manifest-verified.json
c81349d1a8c1173ffc741c5876594cd88a0b8d7f20749e7051461e082320fbf5
manifest-unverified.json
03c188c48180f8717c88ac1b4810b1e42be88fabb704daea05575fb8ca8329a2
```

Original/live source metadata was recorded and checked for distinct identity;
live source contents were not hashed or assessed. Some live runtime files have
changed/replaced identities since restart, as their retained metadata shows.
That does not imply backup corruption or current-state consistency: preservation
is checked against the historical manifest, not mutable live-file contents.

## 4. Exactly one analysis clone — PASSED

Direct libSystem `clonefile(source, target, 0)` returned 0 at
**15:42:03.445 CEST**. One call, no hard-link substitution, full copy or fallback.
The source was freshly fully rehashed immediately before that call. Clone full
hash/geometry verification completed at **15:42:55.176** before attachment.

```text
Source:
/Users/thedeepakreddy/SYNTRA/.syntra/infrastructure-backups/20261016T002121+0200/data/datadisk
Derivative:
/Users/thedeepakreddy/SYNTRA/.syntra/phase10-offline-assessment/20261016T153334+0200/datadisk.analysis.raw
```

Both analysis root and timestamped directory are 0700. File metadata:

| Property | Original | Analysis |
|---|---:|---:|
| Inode | 97698031 | 97738504 |
| Filesystem device ID | 16777233 | 16777233 |
| Logical bytes | 107,374,182,400 | 107,374,182,400 |
| Reported allocated bytes | 966,623,232 | 966,623,232 |

Reported allocation includes shared extents; it does not mean a new independent
966 MB physical copy. The direct clone API and same-volume identities establish
the intended method. Neither a 100 GiB materialized copy nor another clone was
created. The original and derivative, before and after assessment, all match:

```text
9de7d661f8d4c4a7fce36ad6a54f74d235df57e0d6328da080a8aa3aaf2b12dd
```

## 5. Attachment, target identity and protection — PASSED

Actual command, **15:43:12.419–15:43:12.856**, exit 0:

```sh
/usr/bin/hdiutil attach -imagekey diskimage-class=CRawDiskImage \
  -readonly -nomount -noautofsck -plist \
  /Users/thedeepakreddy/SYNTRA/.syntra/phase10-offline-assessment/20261016T153334+0200/datadisk.analysis.raw
```

The successful attachment plist returned `/dev/disk4` and `/dev/disk4s1`;
neither was guessed. `hdiutil info` mapped those devices to the exact derivative,
owner UID 501, `writeable=false`, `autodiskmount=false`.

| Protection | Whole `/dev/disk4` | Partition `/dev/disk4s1` |
|---|---|---|
| `WritableMedia` | false | false |
| Effective `Writable` | false | false |
| `WritableVolume` | false | false |
| Mount point | empty | empty |
| Mount inventory | absent | absent |

Protection/provenance/mount status were rechecked immediately before execution.
The framework's `image-type=read/write` and registry media label describe raw
image format, not effective access: explicit `writeable=false` and all three
device read-only properties establish the enforced access mode.

GPT header/partition-array CRCs passed for source, clone and attached whole
device. Direct partition superblock reads independently confirmed:

- Exactly GPT partition 1; Linux filesystem type
  `0fc63daf-8483-4772-8e79-3d69d8477de4`.
- Sector size 512, LBAs 2048–209713151.
- Offset **1,048,576**, length **107,372,085,248 bytes**.
- Partition GUID **17300ecd-f3b8-4833-9d55-18ffc2a130b8**.
- ext4 UUID **3de9071f-0361-4f65-88a3-f223f8faacb2**; magic 0xEF53,
  4096-byte blocks; feature masks **0x3c / 0x2c6 / 0x46b** unchanged.

Installed 1.47.4 library headers list support for the observed features;
the actual five-pass run reported no unsupported-feature/device errors.
Feature mask 0x2c6 includes needs-recovery, consistent with the skipped journal.
Devices were readable by UID 501, mode 0440; no root, sudo, device chmod or
additional privilege grant was used. The original and live disks were never
attached. No filesystem was mounted.

## 6. Checker, exact invocation and complete result

Native binary/version freshly verified:

```text
/opt/homebrew/Cellar/e2fsprogs/1.47.4/sbin/e2fsck
Mach-O arm64; e2fsck 1.47.4 and EXT2FS library 1.47.4
SHA-256: 40dd92042872a4f39c1954a3588a77c08ef05c8e05898172058ff4407e8c2f60
```

Exactly one invocation, clean environment:

```sh
env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin LC_ALL=C E2FSCK_CONFIG=/dev/null \
  /opt/homebrew/Cellar/e2fsprogs/1.47.4/sbin/e2fsck -f -n -v \
  -E nodiscard,no_inode_count_fullmap,readahead_kb=0 /dev/disk4s1
```

The observer ran `/usr/bin/time -l` around that native command with exactly
those three environment entries, no inherited configuration and stdin closed.
Start **15:45:02.744**, completion **15:45:02.905 CEST**. Native exit **4**.
Helper exit 0 means observation finished, **not** that the filesystem was clean.

Complete stdout and stderr/timing are retained, not reconstructed:

- [Complete stdout](/Users/thedeepakreddy/SYNTRA/.syntra/phase10-evidence/20261016T153334+0200-b2-assessment/e2fsck.stdout)
- [Complete stderr stream, including time -l](/Users/thedeepakreddy/SYNTRA/.syntra/phase10-evidence/20261016T153334+0200-b2-assessment/e2fsck.stderr-and-timing.txt)
- [Structured exact result](/Users/thedeepakreddy/SYNTRA/.syntra/phase10-evidence/20261016T153334+0200-b2-assessment/checker-result.json)

All five passes completed: inodes/blocks/sizes, directory structure,
connectivity, reference counts and group summary information. Actual findings:

1. **Journal recovery skipped**, explicitly: read-only filesystem check.
2. Unconnected directory **inode 2097183**, formerly under
   `/docker/rootfs/overlayfs`. Reconnection to `/lost+found` declined.
3. That inode's `..` entry points to inode **2097180** rather than the reported
   expected null inode. Correction declined.
4. Inode 2097183 reference count **2**, counted expectation **1**. Fix declined.
5. Block bitmap difference **+8396851**. Fix declined.
6. Group **256** free blocks **24522**, counted **24523**; total free blocks
   **25611878**, counted **25611879**. Both corrections declined.
7. Group 256 block-bitmap checksum mismatch, reported **IGNORED** by the checker.
   That line does not erase the errors or make the result clean.
8. Final warning: **Filesystem still has errors**.

Summary: 6,532 inodes used out of 6,553,600; 602,010 blocks used out of
26,213,888; 6,776 files in the printed classification. Its “0 bad blocks” is
not a physical-media scan result: no bad-block scan or file-content audit ran.

**Exit bitmask interpretation:** 4 = filesystem errors left uncorrected.
Bits 1/2 (correction/reboot), 8 (operational error), 16 (usage error),
32 (cancellation) and 128 (shared-library error) are not set. No retry, repair,
unsupported option/feature warning, attempted-write warning, I/O/ENOSPC error,
resource interrupt or timeout occurred. All offered fixes received **no**.

## 7. Journal limitation and detachment/integrity

This is a complete supported no-write scan of the **unreplayed historical
state**, not evidence of the state that journal replay would produce. The
reported allocation/link inconsistencies may be affected by skipped journal
transactions. They cannot establish whether these same errors persist now,
whether a repair is necessary, or whether application data was lost.
No journal replay or state/error-flag clearing was attempted.

After completion, only the resolved analysis whole disk was detached:

```sh
/usr/bin/hdiutil detach /dev/disk4
```

It reported `"disk4" ejected.`; `hdiutil info` showed no attached images, and
both analysis device nodes disappeared. No force flag or unrelated device
operation. The combined detach/probe shell returned 1 because its final `ls`
expectedly found no device nodes; this is **not** a detach failure or a separately
captured detach exit code. Independent follow-up at **15:46:36.924** confirmed
the exact image absent and both nodes absent.

Post-assessment integrity finished **15:48:31.865 CEST**: all 15 original backup
hashes/sizes/modes/inodes match; original data image and derivative full hashes
match the expected pre-assessment SHA-256. No content change detected.
Original/analysis size, inode, mode, mtime and ctime are unchanged. The analysis
clone was retained, not deleted. New B2 evidence directory alone was restricted
to 0700; historical permissions were untouched.

Final read-only inventory at **15:49:02.780 CEST**:

| Measurement | Actual |
|---|---|
| Conservative APFS availability | **12,268,552,192 bytes** |
| Decimal/binary availability | **12.268552 GB / 11.425980 GiB** |
| Pressure / proxy headroom | NORMAL / **1.990 GiB** |
| Swap used | **3,688.12 MiB**; not itself a pass/fail criterion |
| Swap-out counter | **3,152,481**, unchanged throughout B2 |
| 8 GiB entry / 5 GiB operating reserve | PASSED |
| Colima / Docker inventory | Same Running profile; no running containers; old exited container preserved |
| Analysis attachments | None |

## 8. Verdict, remaining risks and next approval boundary

| Status | Requirement / interpretation |
|---|---|
| PASSED | Preflight, backup integrity, one direct clone, correct target, read-only/unmounted protection, native supported assessment, safe detach and post-integrity |
| FAILED | Historical snapshot cleanliness: exit 4, uncorrected metadata inconsistencies |
| BLOCKED | Current-state filesystem health remains `BLOCKED_FILESYSTEM_CHECK_REQUIRED`; no infrastructure tests may resume |
| UNVERIFIED | Current live ext4 consistency, post-replay historical state, application data completeness, need for repair, final Phase 10 acceptance |

No STORAGE_OR_RESOURCE_FAILURE, UNSUPPORTED_CHECKER_OR_DEVICE,
INCOMPLETE_ASSESSMENT or UNEXPECTED_WRITE_OR_INTEGRITY_FAILURE was observed.
The applicable outcome is **FILESYSTEM_INCONSISTENCIES_DETECTED**, not
CLEAN_HISTORICAL_SNAPSHOT. “Procedure PASSED” is not filesystem health sign-off.

Recommended next decision: **preserve and review; do not repair from this result
alone**. The backup predates the latest restart and subsequent tests. To determine
the actual current condition, prepare a separately approved B3 current-state
preservation/assessment plan. A same-volume APFS clone still shares physical
media and is not protection against host-device failure. Host capacity remains
limited and is not reserved; future writes/rework need fresh budgets/gates.

Further authority must be explicit and scoped:

1. **B3 interruption/preservation:** fresh activity/resources/downtime review,
   graceful stop of the same default profile, a new verified stopped-state backup
   of current disks/configuration/logs, and a separately specified current-state
   derivative assessment. These require approval for their exact targets, clone
   count and budget; no additional clone or lifecycle permission remains in B2.
2. **Category C, separate from B3:** any journal replay, filesystem repair,
   corrected-disk promotion, restore/replacement or start that may replay the
   journal needs an explicit evidence-based write plan and approval. No automatic
   reuse/modification/deletion of this historical clone or original backup.
3. **Infrastructure tests:** only after genuinely accepted current-state health
   and authorization to resume; no permission inferred from a completed B2 scan.

No current snapshot, Colima stop/start, repair, journal replay, Docker mutation,
database/Redis write, package operation, infrastructure test, Gemini call, commit,
push, Phase 11–13 or SYNTRA frontend work occurred. Existing source/Git/engineering
evidence remains preserved. This B2 result is native infrastructure evidence,
not model-provider/mock verification or an independent Phase 10 completion audit.

**STOP after B2. Await the user's next authorization.**
