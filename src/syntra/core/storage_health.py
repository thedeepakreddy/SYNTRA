"""Pure, fail-closed storage-evidence classification, never recovery authority.

PASSED describes supplied evidence only. It cannot supersede an unresolved
incident or authorize test dispatch, shutdown, repair, replay or restart. An
operator must record an independently justified superseding health decision.
No infrastructure command or filesystem operation is executed by this module.
"""

import json
import os
import re
import stat
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class LogCapture:
    boot_id: str
    filesystem_uuid: str
    captured_at: datetime
    text: str
    exit_code: int | None
    complete: bool


@dataclass(frozen=True)
class OfflineAssessment:
    assessment_id: str
    filesystem_uuid: str
    captured_at: datetime
    exit_code: int | None
    output: str
    current_state: bool
    complete: bool
    supported: bool
    read_only: bool
    unmounted: bool
    hashes_match: bool


@dataclass(frozen=True)
class StorageEvidence:
    boot_id: str
    filesystem_uuid: str
    kernel: LogCapture
    services: LogCapture
    assessment: OfflineAssessment | None = None
    unresolved_blockers: tuple[str, ...] = ()


@dataclass(frozen=True)
class StorageFinding:
    source: str
    line: int
    reason: str
    text: str


@dataclass(frozen=True)
class StorageDecision:
    status: str
    reasons: tuple[str, ...]
    findings: tuple[StorageFinding, ...]
    test_dispatch_allowed: bool = False


_PATTERNS = (
    (
        "FILESYSTEM_CHECK_REQUIRED",
        r"marked (?:fs|filesystem) in need of (?:a )?filesystem check|mounting (?:fs|filesystem) with errors|e2fsck is recommended",
    ),
    ("STORAGE_IO_FAILURE", r"\bI/?O (?:error|failure)\b|input/output error|buffer I/O"),
    ("JOURNAL_ABORT", r"abort(?:ing|ed)? journal|journal (?:has been )?abort(?:ed)?"),
    (
        "FILESYSTEM_ERROR",
        r"EXT4-fs (?:error|warning)|filesystem error recorded|corrupt(?:ed|ion)? (?:filesystem|metadata)|metadata corruption",
    ),
    ("READ_ONLY_REMOUNT", r"remounting filesystem read.only"),
    ("STORAGE_EXHAUSTED", r"no space left|\bENOSPC\b"),
)
_CHECKER_INCOMPLETE = re.compile(
    r"unsupported|could not be read|skipping journal recovery|journal recovery (?:was )?skipped|needs journal recovery|recover(?:ing|y of) journal|short read|interrupted|cancelled|canceled|read-only filesystem check.*skip|unexpected inconsistency|file\s*system (?:was modified|still has errors)|errors left uncorrected",
    re.I,
)
_CHECKER_BITS = {
    1: "ERRORS_CORRECTED",
    2: "REBOOT_REQUIRED",
    4: "ERRORS_UNCORRECTED",
    8: "OPERATIONAL_ERROR",
    16: "USAGE_ERROR",
    32: "CANCELLED",
    128: "SHARED_LIBRARY_ERROR",
}
_CHECKER_COMPLETED = re.compile(r": clean\b|Pass 5:.*\n[\s\S]*\d+/\d+ files.*\d+/\d+ blocks", re.I)


def decode_e2fsck_exit(exit_code: int) -> tuple[tuple[int, str], ...]:
    """Decode recognized e2fsck bit flags; validity is checked separately."""
    return tuple((bit, reason) for bit, reason in _CHECKER_BITS.items() if exit_code & bit)


def _fresh(captured_at: datetime, now: datetime, max_age_seconds: int) -> bool:
    if captured_at.utcoffset() is None or now.utcoffset() is None:
        return False
    return 0 <= (now - captured_at).total_seconds() <= max_age_seconds


def classify_storage_health(evidence: StorageEvidence, *, now: datetime, max_age_seconds: int = 300) -> StorageDecision:
    """Evaluate captures, not infrastructure; retain blockers over later success.

    Every caller must supply boot/disk provenance, capture completeness and explicit
    unresolved incident IDs. Empty services output must not be fabricated as success:
    collect an authenticated complete no-events record instead. No list of healthy
    images, API responses or successful tests can clear a filesystem blocker.
    """
    reasons: list[str] = []
    findings: list[StorageFinding] = []
    blocked = bool(evidence.unresolved_blockers)
    reasons.extend("UNRESOLVED_BLOCKER:" + b for b in evidence.unresolved_blockers)
    if not evidence.boot_id or not evidence.filesystem_uuid or max_age_seconds <= 0 or now.utcoffset() is None:
        reasons.append("INVALID_CONTEXT")
    for name, capture in (("kernel", evidence.kernel), ("services", evidence.services)):
        if not (
            capture.complete is True
            and type(capture.exit_code) is int
            and capture.exit_code == 0
            and capture.text.strip()
            and capture.boot_id == evidence.boot_id
            and capture.filesystem_uuid == evidence.filesystem_uuid
            and _fresh(capture.captured_at, now, max_age_seconds)
        ):
            reasons.append("INVALID_CAPTURE:" + name)
        for number, line in enumerate(capture.text.splitlines(), 1):
            for reason, pattern in _PATTERNS:
                if re.search(pattern, line, re.I):
                    findings.append(StorageFinding(name, number, reason, line))
                    reasons.append(reason)
                    blocked = True
    assessment = evidence.assessment
    if assessment is None:
        reasons.append("CURRENT_ASSESSMENT_MISSING")
    else:
        if not (
            assessment.assessment_id
            and assessment.filesystem_uuid == evidence.filesystem_uuid
            and all(
                x is True
                for x in (
                    assessment.current_state,
                    assessment.complete,
                    assessment.supported,
                    assessment.read_only,
                    assessment.unmounted,
                    assessment.hashes_match,
                )
            )
            and assessment.output.strip()
            and not _CHECKER_INCOMPLETE.search(assessment.output)
            and _CHECKER_COMPLETED.search(assessment.output)
            and _fresh(assessment.captured_at, now, max_age_seconds)
        ):
            reasons.append("INVALID_OR_INCOMPLETE_ASSESSMENT")
        code = assessment.exit_code
        if type(code) is not int or code < 0 or code & ~191:
            reasons.append("INVALID_CHECKER_EXIT")
        elif code:
            reasons.extend("CHECKER_" + reason for _, reason in decode_e2fsck_exit(code))
            blocked = True
        # Diagnostics contradicting exit 0 must still fail closed.
        for number, line in enumerate(assessment.output.splitlines(), 1):
            for reason, pattern in _PATTERNS:
                if re.search(pattern, line, re.I):
                    findings.append(StorageFinding("assessment", number, reason, line))
                    reasons.append(reason)
                    blocked = True
    status = "BLOCKED_FILESYSTEM_CHECK_REQUIRED" if blocked else "UNVERIFIED" if reasons else "PASSED"
    return StorageDecision(status, tuple(dict.fromkeys(reasons)), tuple(findings))


def main(argv: list[str] | None = None) -> int:
    """Replay one bounded saved JSON input; no guest collection or writes.

    Usage: python -m syntra.core.storage_health SAVED_EVIDENCE.json
    The input schema is the StorageEvidence dataclass, with ISO timestamps. Failed
    collection/provenance must be represented explicitly, not silently defaulted.
    """
    from syntra.llm.context import redact_secrets

    try:
        args = sys.argv[1:] if argv is None else argv
        if len(args) != 1:
            raise ValueError("One saved JSON input required")
        path = Path(args[0])
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_size > 8 * 1024**2:
            raise ValueError("Bounded regular input required")

        # A checked pathname can be replaced before open. Never block on a FIFO
        # or follow a replacement symlink; validate the object actually opened.
        def identity(info):
            return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns

        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or identity(opened) != identity(before):
                raise ValueError("Input changed before open")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(8 * 1024**2 + 1)
            finished = os.fstat(fd)
        finally:
            os.close(fd)
        after = path.lstat()
        if len(raw) > 8 * 1024**2 or identity(before) != identity(finished) or identity(before) != identity(after):
            raise ValueError("Input changed")
        payload = json.loads(raw)
        for key in ("kernel", "services", "assessment"):
            value = payload.get(key)
            if value is not None:
                value["captured_at"] = datetime.fromisoformat(value["captured_at"])
                payload[key] = OfflineAssessment(**value) if key == "assessment" else LogCapture(**value)
        blockers = payload["unresolved_blockers"]
        if not isinstance(blockers, list) or any(not isinstance(b, str) or not b for b in blockers):
            raise ValueError("Explicit incident identifiers required")
        payload["unresolved_blockers"] = tuple(blockers)
        decision = classify_storage_health(StorageEvidence(**payload), now=datetime.now(UTC))
        output = asdict(decision)
        for finding in output["findings"]:
            finding["text"] = redact_secrets(finding["text"])[:1024]
        print(json.dumps(output))
        return 0 if decision.status == "PASSED" else 2
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        print(
            json.dumps(
                {"status": "UNVERIFIED", "reasons": ["MALFORMED_OR_UNREADABLE_INPUT"], "test_dispatch_allowed": False}
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
