# SYNTRA Phase 10 — B3-P-A measured storage optimization proposal

2026-10-16, Europe/Budapest. Scope: planning and read-only measurement ONLY.

**Recommendation:** propose an **8 GiB P-A-only entry gate**, contingent on explicit approval of the amendment and bounded-output controls. No gate has been changed or preservation executed. Existing authorization still requires 12 GiB; it currently fails. Later P-B/P-C resource gates, backup integrity requirements, producer hold and memory criteria remain unchanged.

## 1. Capacity and memory measurements

Last paired resource sample: **23:28:48 CEST**.

| Measurement | Bytes | Decimal GB | Binary GiB |
|---|---:|---:|---:|
| df available: 11,908,000 × 1024 | 12,193,792,000 | 12.193792000 | 11.356353760 |
| diskutil APFSContainerFree | 12,193,783,808 | 12.193783808 | 11.356346130 |
| Conservative available: smaller value | **12,193,783,808** | **12.193783808** | **11.356346130** |

The 8192-byte difference reflects separate observations/accounting; use the smaller value, not Finder's rounded or purgeable estimate. Storage fluctuates; this is not a reservation.

Five samples spanning **124.842 seconds**, 23:26:44–23:28:48, showed NORMAL pressure throughout, conservative headroom proxy **1.791–1.935 GiB**, and **zero additional swap-out pages**. Swap used was 3614.81 MiB at both endpoints. The proxy is free + speculative + inactive pages, not guaranteed immediately allocatable RAM. This window passes the previously specified observation criteria, not a guarantee of future readiness. Fresh qualification remains mandatory before execution.

## 2. Measured preservation scope versus output requirements

File metadata snapshot: 23:27:00. Database catalog snapshot: 23:25:12. PostgreSQL queries were bounded, authenticated, read-only transactions with statement/lock/connect timeouts; no row-content scan or dump was used.

| Item | Measured existing size | Planned new storage treatment |
|---|---:|---|
| syntra_dev | Database 9,600,023 bytes; user relations including indexes/TOAST 974,848 bytes | New custom archive; propose 128 MiB per-file output ceiling |
| syntra_test | Database 18,684,951 bytes; user relations including indexes/TOAST 5,595,136 bytes | Separate new custom archive; propose 128 MiB per-file output ceiling |
| Existing entire Redis RDB | 11,800 bytes logical; 12,288 allocated | Direct same-volume file clone; verify complete file |
| Source and nonignored untracked files | 453 files; 3,046,395 bytes logical | Enumerated direct file clones |
| Git directory | 1234 files; 2,836,486 bytes logical | Enumerated direct file clones under no-Git-writer hold |
| Existing engineering evidence | 288 files; 3,494,409 bytes logical | Enumerated direct file clones, no edits to old evidence |
| Configuration | 198,543 bytes including .env and seven native/profile config files | Direct file clones into private destination |
| Legacy SQLite | 561,152 bytes; no WAL/SHM observed in snapshot | Clone only after proving closed/stable; changed scope stops execution |
| New manifests/logs | Not yet created for P-A | Propose 32 MiB ceiling; expected much smaller |

**Total measured existing file set:** 1985 distinct regular paths, **10,148,785 logical bytes (9.679 MiB)**. Sum of file allocated-block sizes: **15,912,960 bytes (15.176 MiB)**. This sum is NOT unique APFS extent ownership or the incremental cost of cloning.

The source + Git subtotal is **5,882,881 logical bytes**. This includes uncommitted source state; one worktree and local Git common directory were observed. HEAD: `998c00c4a7384851667dd5ea648533eddf29b92d`. Necessary ignored .env/SQLite and explicitly enumerated evidence are additional to Git enumeration.

No files were found in the separately checked artifact/log/host-data/sandbox directories. This does not prove every future or arbitrary ignored path unnecessary: the execution manifest must be reviewed against the approved scope. A new required directory, external Git dependency, WAL, symlink or materially larger scope requires remeasurement. New planning evidence and this report postdate the file snapshot and must enter the future frozen manifest.

Existing VM-backup and offline-analysis trees are excluded from duplication, not deletion. Retain and verify their existing manifests in place. Development environments, caches and node_modules remain untouched in situ; do not treat this proposal as a full-machine backup. Do not clone live PostgreSQL data directories.

Both databases had zero large-object metadata entries. The dev estimated-row count was zero, but this is a catalog estimate, not proof of an empty database. No exact archive sizes were measured: TOAST compression, logical encoding, catalog/index overhead and archive compression prevent deriving them reliably from database size. PostgreSQL documents this distinction through its [dump format](https://www.postgresql.org/docs/16/app-pgdump.html) and [TOAST storage](https://www.postgresql.org/docs/16/storage-toast.html) behavior. Do not change approved archive format/compression or omit data to meet a budget.

## 3. APFS clone eligibility and physical consumption

All enumerated files and the existing proposed parent
`/Users/thedeepakreddy/SYNTRA/.syntra/infrastructure-backups`
reported device **16777233** on APFS. The parent was not a symlink. Proposed P-A destination remains a new exclusive private `<RUN>-host-native` child, never an existing backup.

Eligible: stable regular source/Git/config/evidence files, closed SQLite and the existing completed RDB. Not eligible as a substitute for logical backup: live PostgreSQL files. PG archives and new manifests/logs necessarily allocate new data. No VM disk is part of P-A.

Use the already reviewed direct clonefile primitive, fail closed on error, no full-copy fallback. A successful APFS file clone initially shares file-data extents, but new metadata and subsequent COW writes consume space. Future private-block cost and transient allocation cannot be measured exactly without executing operations. See Apple's [clonefile specification](https://raw.githubusercontent.com/apple-oss-distributions/xnu/main/bsd/man/man2/clonefile.2). Existing completed RDB preservation still requires stable identity, persistence observations and full hashes, consistent with [Redis persistence guidance](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/).

Cloning does not give independent-media protection: both copies share the host APFS failure domain. A clone is not a live-database consistency mechanism. Preserve the existing integrity and consistency checks, including full source/destination hashes, file sizes, Git-state checks, archive exit statuses/listings and sealed manifests. Actual restores remain UNVERIFIED.

## 4. Proposed P-A physical budget and revised entry gate

These are **conservative planning allowances**, not observed archive sizes or a proved worst-case allocation bound.

| P-A task allowance | MiB |
|---|---:|
| syntra_dev archive ceiling | 128 |
| syntra_test archive ceiling | 128 |
| File-clone metadata/attributes and small-source COW allowance | 64 |
| New manifests and bounded logs/evidence ceiling | 32 |
| Backend transient allocation, filesystem overhead and task slack | 160 |
| Total task allowance | **512** |

Expected file payload sharing makes clone allocation substantially smaller than a materialized duplicate. No precise incremental physical-byte estimate is asserted. Planning for **up to 0.5 GiB task allowance** is proportionate to the small measured source/database scope, provided all caps and stop rules are enforced. Unknown expansion is handled by stopping an incomplete attempt, never by accepting a truncated backup.

Proposed **8 GiB admission gate**:

- **5 GiB operating reserve**, never intentionally spendable.
- **0.5 GiB task allowance** above.
- **2 GiB host/swap/background-write contingency**.
- **0.5 GiB additional slack**.

The original 12 GiB combined allowance included shutdown/COW and analysis budgets. P-A performs neither VM shutdown nor disk cloning/assessment; allocating those later-phase allowances to this host-native-only stage is unnecessarily restrictive. Reducing P-A only is justified as a new bounded plan, not as a finding that 12 GiB was previously satisfied.

At measured capacity, proposed 8 GiB margin is **3,603,849,216 bytes (3.356346130 GiB)**. **No additional cleanup is needed under this proposal.** At a hypothetical 11.816 GiB, the same conclusion holds.

Under the unchanged existing 12 GiB condition, the current shortfall is **691,118,080 bytes = 659.1015625 MiB = 0.643653870 GiB**. At exactly 11.816 GiB the shortfall is about **0.184 GiB / 197.568 MB**. Those are arithmetic minima, not recommended operating margins.

## 5. Controls required before lower-gate execution

1. Obtain explicit approval amending P-A only. Reverify historical backups, paths/ownership, permissions, frozen scope, no source writers and the full two-minute producer hold. This planning observation is not a hold.
2. Fresh >=8 GiB storage plus unchanged memory qualification: NORMAL throughout >=120 seconds, >=1.5 GiB conservative headroom, no sustained swap-out growth. Observe application/VM/background writes without stopping services.
3. Before using the lowered gate, review a bounded wrapper that applies **child-only RLIMIT_FSIZE=128 MiB** to each sequential pg_dump, private exclusive outputs, bounded transcripts and timeouts. Local read-only capability probe confirmed RLIMIT_FSIZE exists; no limits were set and no wrapper/dump was executed. [Python resource documentation](https://docs.python.org/3/library/resource.html) describes this facility. File-size limits do not constrain PostgreSQL server temporary files, APFS metadata or unrelated writers.
4. Monitor the smaller df/APFS available value and memory every second and before each operation. **Stop initiating work and abort only the newly owned backup client gracefully** on <=6 GiB free, rapid unexplained allocation, pressure no longer NORMAL, headroom below 1.5 GiB, sustained swap-outs, missing observations, scope drift or instability. No existing service/process termination or automatic cleanup.
5. Stop on clone failure, source inode/mtime/hash drift, Redis persistence activity/identity change, SQLite writer/WAL uncertainty, permission/ownership mismatch, archive/file cap, nonzero dump exit, unreadable archive, manifest mismatch or total task-growth budget breach. Keep partial files and evidence; an incomplete archive is FAILED, never a backup pass. Reassess before retrying.
6. No modifications to originals, credentials, historical backup, database contents or permission settings. No extra compression, deletions, moves, source-format changes, fallback copies, VM operations or infrastructure tests.

The 6 GiB trigger leaves 1 GiB above the mandatory floor. It is an early-stop policy, not a guarantee against unrelated instantaneous host allocations. APFS sharing and other processes prevent a global per-task physical allocation cap. If the user requires a guaranteed reserve against every host writer, these observations cannot certify that; a different separately approved isolation/storage arrangement would be needed.

## 6. Verdict and approval checkpoint

- **PASSED:** bounded measurements; same-volume file-clone eligibility; observed five-sample memory criteria; 5 GiB operating reserve.
- **FAILED:** current capacity against the still-authoritative 12 GiB P-A entry gate.
- **BLOCKED:** P-A execution pending explicit acceptance of the revised gate/controls, implementation review of guards, refreshed original integrity prerequisites and verified producer hold.
- **UNVERIFIED:** actual archive sizes, clone incremental physical cost, actual P-A backups/restores and current guest filesystem integrity.

P-B remains **12 GiB before shutdown**, **8 GiB before stopped clones**, with 5 GiB operating floor. P-C remains **8 GiB before clone/attach/check**, with unchanged memory and no-write safeguards. No future capacity is promised. Phase 10 remains **REQUIRES_WORK**.

Requested next decision: approve or reject the **P-A-only 8 GiB resource-plan amendment and bounded-output controls**. This report itself confers no execution authority. Stop after this planning response; no shutdown, clone, attachment, mount, filesystem check, repair, journal replay, testing, Gemini invocation or Phases 11–13 work occurred.

## 7. Evidence and limitations

New evidence only:
`/Users/thedeepakreddy/SYNTRA/.syntra/phase10-evidence/20261016T232332+0200-b3pa-storage-plan/`.

Files include initial/final file metadata aggregates, bounded PostgreSQL catalog results, five complete resource samples with command stdout/stderr, scope/capture disclosure and diagnostic scripts. Initial verbose inventory exceeded output capture; compact metadata remeasurement was retained instead. The aggregate inventory SHA-256 is a metadata fingerprint, NOT a full source-content verification. Existing evidence was not overwritten; original reports and task plans were not amended.
