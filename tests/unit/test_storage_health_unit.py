"""Synthetic policy tests only: no guest, disks, Docker or filesystem checker."""

import json
import os
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from syntra.core.storage_health import (
    LogCapture,
    OfflineAssessment,
    StorageEvidence,
    classify_storage_health,
    decode_e2fsck_exit,
)

NOW = datetime(2026, 10, 16, 22, tzinfo=UTC)


def evidence():
    return StorageEvidence(
        boot_id="current-boot",
        filesystem_uuid="current-filesystem",
        kernel=LogCapture("current-boot", "current-filesystem", NOW, "EXT4-fs: recovery complete", 0, True),
        services=LogCapture("current-boot", "current-filesystem", NOW, "containerd: started", 0, True),
        assessment=OfflineAssessment(
            "assessment-1",
            "current-filesystem",
            NOW,
            0,
            "Pass 5: Checking group summary information\nfilesystem: clean",
            current_state=True,
            complete=True,
            supported=True,
            read_only=True,
            unmounted=True,
            hashes_match=True,
        ),
    )


@pytest.mark.parametrize(
    "line",
    [
        "EXT4-fs warning (device vdb1): ext4_clear_journal_err:6340: Filesystem error recorded from previous mount: IO failure",
        "EXT4-fs warning (device vdb1): ext4_clear_journal_err:6348: Marked fs in need of filesystem check.",
        "EXT4-fs (vdb1): warning: mounting fs with errors, running e2fsck is recommended",
        "EXT4-fs (vdb1): mounting filesystem with errors",
        "JBD2: Aborting journal on device vdb1-8.",
        "EXT4-fs: aborted journal",
        "Buffer I/O error on dev vdb1",
        "failed to read blob: input/output error",
        "IO failure during metadata read",
        "No space left on device",
        "write failed: ENOSPC",
        "EXT4-fs error (device vdb1): corrupted metadata",
        "Remounting filesystem read-only",
    ],
)
def test_storage_errors_block_even_after_later_success(line):
    e = evidence()
    result = classify_storage_health(
        replace(e, kernel=replace(e.kernel, text=line + "\nrecovery complete\nmounted r/w")), now=NOW
    )
    assert result.status == "BLOCKED_FILESYSTEM_CHECK_REQUIRED"
    assert any(f.line == 1 and f.source == "kernel" and f.text == line for f in result.findings)
    assert not result.test_dispatch_allowed


@pytest.mark.parametrize(
    "field,value",
    [
        ("complete", False),
        ("exit_code", 1),
        ("text", ""),
        ("text", "   \n"),
        ("boot_id", "old-boot"),
        ("filesystem_uuid", "another-disk"),
        ("captured_at", NOW - timedelta(minutes=6)),
        ("captured_at", NOW + timedelta(seconds=1)),
        ("captured_at", NOW.replace(tzinfo=None)),
    ],
)
def test_invalid_log_capture_fails_closed(field, value):
    e = evidence()
    result = classify_storage_health(replace(e, services=replace(e.services, **{field: value})), now=NOW)
    assert result.status == "UNVERIFIED"
    assert result.reasons and not result.test_dispatch_allowed


@pytest.mark.parametrize(
    "field,value",
    [
        ("current_state", False),
        ("complete", False),
        ("supported", False),
        ("read_only", False),
        ("unmounted", False),
        ("hashes_match", False),
        ("filesystem_uuid", "historical-filesystem"),
        ("captured_at", NOW - timedelta(minutes=6)),
        ("assessment_id", ""),
        ("output", ""),
        ("output", "Warning: skipping journal recovery because doing a read-only filesystem check."),
        ("output", "unsupported feature(s): orphan_file"),
        ("output", "Filesystem has unsupported features"),
        ("output", "The superblock could not be read"),
    ],
)
def test_invalid_offline_assessment_does_not_clear_health(field, value):
    e = evidence()
    result = classify_storage_health(replace(e, assessment=replace(e.assessment, **{field: value})), now=NOW)
    assert result.status != "PASSED"
    assert result.reasons and not result.test_dispatch_allowed


@pytest.mark.parametrize(
    "exit_code,bits",
    [
        (0, ()),
        (1, (1,)),
        (2, (2,)),
        (4, (4,)),
        (8, (8,)),
        (16, (16,)),
        (32, (32,)),
        (128, (128,)),
        (5, (1, 4)),
        (12, (4, 8)),
        (255, (1, 2, 4, 8, 16, 32, 128)),
    ],
)
def test_checker_exit_bitmask_is_decoded_and_nonzero_never_passes(exit_code, bits):
    assert tuple(bit for bit, _ in decode_e2fsck_exit(exit_code)) == bits
    e = evidence()
    result = classify_storage_health(replace(e, assessment=replace(e.assessment, exit_code=exit_code)), now=NOW)
    assert (result.status == "PASSED") == (exit_code == 0)
    assert not result.test_dispatch_allowed  # Classifier output never grants execution authority.


@pytest.mark.parametrize("exit_code", [-1, 64, 256, True, None])
def test_unknown_or_missing_checker_exit_is_not_success(exit_code):
    e = evidence()
    result = classify_storage_health(replace(e, assessment=replace(e.assessment, exit_code=exit_code)), now=NOW)
    assert result.status == "UNVERIFIED"


def test_historical_clean_check_missing_check_and_previous_blocker_remain_sticky():
    e = evidence()
    assert classify_storage_health(replace(e, assessment=None), now=NOW).status == "UNVERIFIED"
    assert (
        classify_storage_health(replace(e, assessment=replace(e.assessment, current_state=False)), now=NOW).status
        != "PASSED"
    )
    result = classify_storage_health(replace(e, unresolved_blockers=("health-review.json",)), now=NOW)
    assert result.status == "BLOCKED_FILESYSTEM_CHECK_REQUIRED"
    assert "UNRESOLVED_BLOCKER:health-review.json" in result.reasons


def test_complete_current_evidence_is_only_a_candidate_not_execution_authority():
    e = evidence()
    e = replace(e, kernel=replace(e.kernel, text="ACPI: IOAPIC mapping initialized\nEXT4-fs: mounted ro"))
    result = classify_storage_health(e, now=NOW)
    assert result.status == "PASSED" and not result.findings
    assert not result.test_dispatch_allowed


def test_service_error_and_invalid_context_are_not_masked_by_clean_kernel():
    e = evidence()
    result = classify_storage_health(replace(e, services=replace(e.services, text="metadata I/O error")), now=NOW)
    assert result.status == "BLOCKED_FILESYSTEM_CHECK_REQUIRED"
    assert classify_storage_health(replace(e, boot_id=""), now=NOW).status == "UNVERIFIED"


@pytest.mark.parametrize(
    "text",
    [
        "success",
        "Pass 1: Checking inodes",
        "UNEXPECTED INCONSISTENCY; RUN fsck MANUALLY",
        "FILE SYSTEM WAS MODIFIED",
        "Filesystem still has errors",
    ],
)
def test_exit_zero_without_complete_supported_result_is_not_accepted(text):
    e = evidence()
    result = classify_storage_health(replace(e, assessment=replace(e.assessment, output=text)), now=NOW)
    assert result.status != "PASSED" and not result.test_dispatch_allowed


def test_saved_evidence_cli_is_read_only_and_rejects_missing_context(tmp_path, capsys):
    from syntra.core.storage_health import main

    path = tmp_path / "input.json"
    e = evidence()
    e = replace(e, kernel=replace(e.kernel, text="Marked fs in need of filesystem check."))
    text = json.dumps(asdict(e), default=lambda value: value.isoformat())
    path.write_text(text)
    assert main([str(path)]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "BLOCKED_FILESYSTEM_CHECK_REQUIRED"
    assert result["test_dispatch_allowed"] is False
    assert path.read_text() == text
    path.write_text("{}")
    assert main([str(path)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "UNVERIFIED"


def test_saved_evidence_cli_requires_explicit_incident_list(tmp_path, capsys):
    from syntra.core.storage_health import main

    payload = asdict(evidence())
    del payload["unresolved_blockers"]
    path = tmp_path / "missing-incidents.json"
    path.write_text(json.dumps(payload, default=lambda value: value.isoformat()))
    assert main([str(path)]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "UNVERIFIED"
    assert result["reasons"] == ["MALFORMED_OR_UNREADABLE_INPUT"]


@pytest.mark.parametrize("replacement", ["fifo", "symlink", "regular"])
def test_saved_evidence_cli_rejects_replacement_before_open_without_blocking(
    tmp_path, capsys, monkeypatch, replacement
):
    from syntra.core.storage_health import main

    path = tmp_path / "raced.json"
    path.write_text("{}")
    other = tmp_path / "replacement.json"
    other.write_text("{}")
    original_lstat, original_open = Path.lstat, Path.open
    original_os_open = os.open
    replaced = False
    descriptors = []

    def swap_after_check(candidate, *args, **kwargs):
        nonlocal replaced
        result = original_lstat(candidate, *args, **kwargs)
        if candidate == path and not replaced:
            replaced = True
            path.unlink()
            if replacement == "fifo":
                os.mkfifo(path)
            elif replacement == "symlink":
                path.symlink_to(other)
            else:
                other.rename(path)
        return result

    def refuse_unsafe_path_open(candidate, *args, **kwargs):
        if candidate == path:
            # Never let the regression test itself hang on the old FIFO open.
            raise AssertionError("Unsafe pathname open after the checked file was replaced")
        return original_open(candidate, *args, **kwargs)

    def track_descriptor(candidate, flags, *args, **kwargs):
        fd = original_os_open(candidate, flags, *args, **kwargs)
        if Path(candidate) == path:
            descriptors.append(fd)
        return fd

    monkeypatch.setattr(Path, "lstat", swap_after_check)
    monkeypatch.setattr(Path, "open", refuse_unsafe_path_open)
    monkeypatch.setattr(os, "open", track_descriptor)
    assert main([str(path)]) == 2
    assert replaced
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "UNVERIFIED"
    assert not result["test_dispatch_allowed"]
    for fd in descriptors:
        with pytest.raises(OSError):
            os.fstat(fd)
