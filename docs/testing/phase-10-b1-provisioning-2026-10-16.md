# Phase 10 B1 — controlled tool provisioning result

Date: 2026-10-16, Europe/Budapest. **B1: PASSED. Phase 10: REQUIRES_WORK.**
Infrastructure remains `BLOCKED_FILESYSTEM_CHECK_REQUIRED`.

## Authority and evidence

The user explicitly approved B1 Option 2: controlled dry-run plus conditional
installation of the reviewed e2fsprogs 1.47.4 ARM64 bottle. No B2 authority was
inferred. A later “continue where you left off” resumed the same authorization.
The continuation occurred hours later; resources, official metadata and the
non-installing preview were refreshed before installation.

New evidence, separate from all previous recovery/assessment records:

```text
/Users/thedeepakreddy/SYNTRA/.syntra/phase10-evidence/20261016T015443+0200-b1-provisioning/
```

Its directory timestamp is campaign creation, not installation time. Initial
readiness/preview ran around 01:55–01:58 CEST; fetch, refreshed checks, installation
and verification ran after the continuation around 12:28–12:34 CEST.
JSON records retain exact command arguments, exit codes, stdout/stderr, controlled
Homebrew environment, resource measurements and timing. Observer/verification
source is retained with the evidence. `evidence-sha256.json` indexes the records.

## Actual results

| Requirement | Result | Evidence |
|---|---|---|
| Separate B1 resource gates | PASSED | Both readiness windows and operation samples |
| Verified non-installing preview | PASSED | Two successful `brew install --dry-run` results; package receipts, versions, source and prefix links unchanged after first preview |
| Exact package selection | PASSED | 1.47.4 revision 0, ARM64 Tahoe, official formula plus actual Homebrew resolution |
| Download integrity | PASSED | Downloaded bottle SHA-256 exactly matches approved digest |
| Bottle installation | PASSED | Exit 0, only `e2fsprogs--1.47.4.arm64_tahoe.bottle.tar.gz` poured |
| Native binary/version | PASSED | Mach-O arm64; `e2fsck -V` exit 0, e2fsck and EXT2FS library 1.47.4 |
| Library closure | PASSED | Existing gettext/libintl and bundled ext2fs/com_err/blkid/uuid/e2p resolve; all inspected non-system libraries are ARM64; version-only invocation loads successfully |
| Installed payload integrity | PASSED | Final comparison accounts for all 142 regular archive members, including expected relocation/re-signing and SBOM metadata |
| No unrelated package changes | PASSED | All 49 old receipt hashes unchanged; only e2fsprogs keg/receipt added; no old keg removed; unrelated prefix links and Homebrew Git HEAD unchanged |
| Backup preservation | PASSED, limited to metadata/manifests this B1 | Both original manifest hashes unchanged; data-disk metadata unchanged; no full disk rehash claimed here |
| Native read-only partition-device operation | UNVERIFIED | Requires separately authorized B2; no disk was attached or checked |
| Historical filesystem assessment | BLOCKED_BY_AUTHORIZATION | B2 not performed |
| Current live filesystem health | BLOCKED_FILESYSTEM_CHECK_REQUIRED | B1 cannot certify filesystem consistency |
| Phase 10 regression/manual/live Gemini | UNVERIFIED fresh | No infrastructure tests or provider calls in B1 |

No unresolved B1 failure remains. An auxiliary attempt to read
`INSTALL_RECEIPT.json` inside the archive failed: this bottle stores its build tab
in the OCI index instead. That original error is retained, followed by the
successful OCI metadata review. The first payload comparison also assumed staged
configuration had been installed globally; inspection corrected that assumption.
These are diagnostic corrections, not hidden successful checks. Earlier records
are not overwritten by the final verification.

## Storage and memory

Initial window, 01:55:48–01:57:53: five NORMAL samples over 124.749 seconds;
minimum proxy headroom 1.843 GiB; zero additional swap-outs.

Fresh pre-installation window, 12:29:06–12:31:11: five WARNING/noncritical samples
over 124.799 seconds; headroom 1.629–1.777 GiB; swap-out counter fixed at 3,105,129;
available storage at least 12,298,739,712 bytes (11.454 GiB). This passes the
previously approved **B1 installation** gate (stable noncritical, >=1.5 GiB,
>=8.25 GiB storage, no sustained swap-outs), not the stricter B2 NORMAL gate.
The earlier 3,075,353 counter was hours old; its difference is not attributed to
the brief package operation or presented as a current sustained-growth trend.

Installation, 12:31:43–12:31:45: all three operation samples NORMAL; minimum
headroom 1.782 GiB; zero additional swap-outs; storage remained above 11.54 GiB.
`time -l`: 2.38 seconds, maximum resident set 100,384,768 bytes; one sampled
process tree summed 121,824 KiB RSS. Neither is a guaranteed total peak physical
charge. Preview/fetch finished too quickly for the 2-second process-tree sampler;
their before/after samples and `time -l` measurements are retained.

Post-installation measurement at **12:33:40 CEST**:

| Measurement | Actual |
|---|---|
| `df` availability | 12,368,957,440 bytes |
| `diskutil` APFS availability | 12,368,957,440 bytes |
| Available decimal/binary units | **12.368957 GB / 11.519489 GiB** |
| Memory pressure | NORMAL |
| Conservative headroom proxy | 1.792 GiB |
| Swap usage | 3,188.25 MiB; not itself a readiness verdict |
| Swap-out counter | 3,105,129; unchanged throughout resumed provisioning |
| Operating reserve | PASSED: >5 GiB |

Proxy = free + inactive + speculative pages, without double-counting purgeable
or file-backed pages. It is not guaranteed allocatable RAM. No user process was
terminated and no OS/VM memory configuration was changed.

Measured keg allocation: 8,032 KiB = 8,224,768 bytes (7.844 MiB).
Verified compressed bottle: 2,465,453 bytes (2.351 MiB), plus its 21,154-byte
manifest/cache and small Homebrew/evidence metadata. The bottle advertised
9,077,613 installed bytes; logical payload size and allocated disk usage differ.
The 256 MiB provisioning allowance remained ample. Host free-space changes
include unrelated activity; they are not an exact package footprint measurement.

## Exact executed Homebrew operations

Homebrew 7.0.9 native command source/help was inspected before use. The dry-run
branch returns before package installation and skips bottle download queues;
preinstall diagnostics/cache/metadata writes can still occur. It is non-installing,
not a globally zero-write operation. Actual output, twice:

```text
==> Would install 1 formula:
e2fsprogs 1.47.4
```

Each operation used these per-process controls, without editing shell startup or
Homebrew configuration:

```sh
HOMEBREW_NO_AUTO_UPDATE=1
HOMEBREW_NO_INSTALL_CLEANUP=1
HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK=1
HOMEBREW_NO_INSTALL_UPGRADE=1
HOMEBREW_NO_ANALYTICS=1
```

The observer removed inherited `HOMEBREW_*` overrides before setting those
controls; none were present. Exact commands, wrapped in `/usr/bin/time -l` and
resource monitoring:

```sh
/opt/homebrew/bin/brew install --dry-run --formula --force-bottle --skip-post-install e2fsprogs
/opt/homebrew/bin/brew fetch --formula --bottle-tag=arm64_tahoe e2fsprogs
/opt/homebrew/bin/brew install --formula --force-bottle --skip-post-install e2fsprogs
```

Actual read-only package queries were `brew info --json=v2 --formula e2fsprogs`
and `brew --cache --formula --bottle-tag=arm64_tahoe e2fsprogs`, under the same
controls. The installation did not compile source, provision pkgconf, upgrade
dependencies, run cleanup, start a service, or run post-install hooks. Homebrew's
warning about disabled dependent checks is expected and retained.

## Package identity and installed integrity

Official source: [Homebrew formula API](https://formulae.brew.sh/api/formula/e2fsprogs.json).
Local Homebrew resolution and the downloaded OCI index independently selected:

```text
Version/revision: 1.47.4 / 0
Bottle tag: arm64_tahoe, Darwin macOS 26
Bottle SHA-256:
f8024861ae8b5a645374d7960a5b5e3c41576c792712925d55deb186a74a1d06

Installed binary:
/opt/homebrew/Cellar/e2fsprogs/1.47.4/sbin/e2fsck
Opt alias:
/opt/homebrew/opt/e2fsprogs/sbin/e2fsck
Installed binary SHA-256:
40dd92042872a4f39c1954a3588a77c08ef05c8e05898172058ff4407e8c2f60
```

Only this version-only invocation was performed; no filesystem argument:

```sh
env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin LC_ALL=C E2FSCK_CONFIG=/dev/null \
  /opt/homebrew/Cellar/e2fsprogs/1.47.4/sbin/e2fsck -V
```

It reports `e2fsck 1.47.4 (6-Mar-2025)` and matching EXT2FS library 1.47.4,
exit 0. That printed version date is recorded literally, not inferred from the
bottle build date. No assessment, dry repair or journal replay was performed.

Direct formula dependency is existing gettext 1.0. Recorded bottle runtime
dependencies are gettext 1.0 and libunistring 1.4.2; installed receipt additionally
records existing gettext's json-c 0.19 transitive dependency and actual bottle
rebuild metadata. Those installed receipts match the pre-operation baseline.
This receipt enrichment is not a newly installed/changed dependency.

Final archive comparison:

- 105 regular files: byte-for-byte identical, including the staged configuration.
- 28 Mach-O files: all parsed file-backed section contents identical; dynamic
  library paths are exact Homebrew prefix/Cellar placeholder replacements;
  every relocated binary/library passes `codesign --verify --strict`.
- Eight scripts/pkg-config files: exact expected prefix/Cellar text replacements.
- One SBOM: only `creationInfo` changed, to installation-receipt time and
  `Homebrew/brew@7.0.9`, matching the inspected Homebrew pour implementation.

All six archive hard links also retain their expected same-inode/content
relationships inside the keg. There were no archive symbolic links.

The installed executable hash therefore legitimately differs from its archive
member hash. No byte-for-byte archive equivalence is claimed for relocated files.
This verifies package/pour integrity; it is not an independent supply-chain audit.

The package remains keg-only. Existing global bin/sbin/library/header links are
unchanged; only its opt alias was added. `--skip-post-install` leaves
`mke2fs.conf` inside the keg's `.bottle/etc/`; no global config installation or
PATH changes were performed. B2 uses `E2FSCK_CONFIG=/dev/null` explicitly.

## B2 procedure — READY FOR CONDITIONAL APPROVAL, NOT EXECUTED

The installed manual documents `-n` as read-only/noninteractive and includes
`nodiscard`, `no_inode_count_fullmap`, and `readahead_kb=0`. Runtime access to an
actual macOS unmounted Linux partition remains UNVERIFIED until B2; do not test
that interface without authorization or silently substitute a writable method.

1. **Fresh strict resource gate:** NORMAL pressure in >=3 samples spanning >=2
   minutes; >=1.5 GiB proxy headroom, no sustained swap-outs, >=8 GiB entry
   capacity, >=5 GiB operating reserve throughout. The last dedicated window was
   WARNING, followed by NORMAL operation samples; revalidate rather than reuse
   the more permissive B1 gate. Keep the 1.5 GiB analysis/evidence/COW allowance.
2. **Preservation gate:** verify both immutable manifests and rehash all 15
   preserved files against `manifest-verified.json`, including the full original
   data image. Validate regular-file/path ancestry, no symlink redirection and
   same APFS filesystem. Do not change original permissions or contents.
3. **Exactly one direct APFS clonefile**, no materialized copy/hard-link/fallback,
   using the reviewed libSystem `clonefile` procedure in the safety review.
   New private destination only:

   ```text
   /Users/thedeepakreddy/SYNTRA/.syntra/phase10-offline-assessment/<new-timestamp>/datadisk.analysis.raw
   ```

   Source is exclusively:

   ```text
   /Users/thedeepakreddy/SYNTRA/.syntra/infrastructure-backups/20261016T002121+0200/data/datadisk
   ```

   Require distinct inode, 107,374,182,400 logical bytes, exact original/clone
   SHA-256 `9de7d661f8d4c4a7fce36ad6a54f74d235df57e0d6328da080a8aa3aaf2b12dd`.
4. **Attach the derivative only**, capturing all outputs separately:

   ```sh
   hdiutil attach -imagekey diskimage-class=CRawDiskImage -readonly -nomount -noautofsck -plist "$ANALYSIS_IMAGE"
   ```

   Resolve whole disk and partition from this successful attachment's plist;
   never guess `/dev/diskN`. Record `hdiutil info -plist`, device-specific
   `diskutil info/list -plist`, mount inventory and independent read-only identity
   reads. Require false `WritableMedia`/effective `Writable`, no mounted children,
   exact attachment provenance and partition 1 geometry:

   - Offset 1,048,576; length 107,372,085,248 bytes.
   - Partition GUID `17300ecd-f3b8-4833-9d55-18ffc2a130b8`.
   - ext4 UUID `3de9071f-0361-4f65-88a3-f223f8faacb2`, block size 4096.
   - Previously read feature masks `0x3c/0x2c6/0x46b`; unexpected features stop.
5. **One no-write checker invocation**, only after every gate passes:

   ```sh
   env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin LC_ALL=C E2FSCK_CONFIG=/dev/null \
     /opt/homebrew/Cellar/e2fsprogs/1.47.4/sbin/e2fsck -f -n -v \
     -E nodiscard,no_inode_count_fullmap,readahead_kb=0 "$PARTITION_DEVICE"
   ```

   Monitor host resources; retain stdout/stderr, exit bitmask, timing, exact tool,
   image identity and hashes. This is an assessment, not repair; no mounts,
   journal replay, discard, bad-block scans, alternate target or flags.
6. **Detach only the new whole device**, `hdiutil detach "$WHOLE_DEVICE"`, without
   force. Verify disappearance, rehash original/clone, require unchanged bytes;
   preserve derivative and every result. No automatic deletion or clone reuse.

Stop on mismatched identity/hash, missing read-only proof, device-access denial,
unsupported features/options, warning/critical assessment pressure, inadequate
headroom/reserve, new swap-out trend, I/O/ENOSPC, signal or incomplete output.
Do not escalate to blanket sudo, writable attachment, forced detach, guest Linux
or repair. If an exact device command needs additional privileges, request that
specific permission before proceeding. Checker exit bits 4 indicate uncorrected
findings; 8/16/128 indicate incomplete/error paths, not a clean filesystem.
Unexpected write-indicating exit bits 1/2 or any changed image hash require an
immediate protection/provenance investigation.

**Historical limitation:** this backup predates the latest Colima restart and
test activity. `-n` skips journal recovery and cannot repair. A clean historical
assessment cannot clear current-state health. A later current-state snapshot,
Colima lifecycle, journal replay or repair each requires the applicable separate
B3/Category C authorization.

## Stop boundary

Await explicit B2 approval for the six-stage derivative-only procedure above,
conditional on all strict gates. No disk clone, attachment, mount, filesystem
check/repair, Colima command, Docker write, infrastructure test, model call,
commit/push or Phase 11–13/frontend work occurred in B1. Existing implementation
and all prior engineering/recovery evidence are preserved. Documentation changes
in this campaign are isolated and checked separately from their initial hashes.
