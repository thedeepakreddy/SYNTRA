"""Unit tests for Phase 13 Benchmark Architecture and Target Fixture Scaffolding (Milestone 13.1 & 13.2)."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from syntra.benchmarks.collector import BenchmarkCollector
from syntra.benchmarks.models import (
    BenchmarkMetric,
    BenchmarkResult,
    BenchmarkRunConfig,
    BenchmarkStatus,
    EvaluationMode,
    RunManifest,
)
from syntra.benchmarks.reporters import BenchmarkIntegrityError, BenchmarkReporter
from syntra.benchmarks.runner import BenchmarkRunner


# ==============================================================================
# 1. Benchmark Domain Model & Schema Validation Tests
# ==============================================================================
def test_evaluation_modes_enum():
    """EvaluationMode defines the 4 canonical evaluation modes."""
    assert EvaluationMode.MODE_A_DETERMINISTIC_MOCK.value == "mode_a_deterministic_mock"
    assert EvaluationMode.MODE_B_REAL_INFRASTRUCTURE.value == "mode_b_real_infrastructure"
    assert EvaluationMode.MODE_C_LIVE_MODEL.value == "mode_c_live_model"
    assert EvaluationMode.MODE_D_FAULT_RECOVERY.value == "mode_d_fault_recovery"


def test_benchmark_metric_validation():
    """BenchmarkMetric captures quantitative metrics and threshold evaluations."""
    metric = BenchmarkMetric(
        name="TASK_SUCCESS_RATE",
        value=1.0,
        unit="ratio",
        threshold=1.0,
        passed=True,
        details="All DAG tasks succeeded",
    )
    assert metric.name == "TASK_SUCCESS_RATE"
    assert metric.value == 1.0
    assert metric.passed is True

    # Serialization
    data = json.loads(metric.model_dump_json())
    assert data["name"] == "TASK_SUCCESS_RATE"
    assert data["value"] == 1.0


def test_benchmark_run_config_defaults():
    """BenchmarkRunConfig defaults to Mode A deterministic mock."""
    config = BenchmarkRunConfig()
    assert config.mode == EvaluationMode.MODE_A_DETERMINISTIC_MOCK
    assert config.iterations == 1
    assert config.seed == 42
    assert config.budget_usd == Decimal("2.00")
    assert config.fixture_path == Path("tests/fixtures/phase13_inventory")


def test_run_manifest_reproducibility():
    """RunManifest captures git commit, mode, seed, and environment."""
    run_id = uuid4().hex[:12]
    manifest = RunManifest(
        run_id=run_id,
        git_commit="998c00c4a7384851667dd5ea648533eddf29b92d",
        mode=EvaluationMode.MODE_A_DETERMINISTIC_MOCK,
        seed=42,
    )
    assert manifest.run_id == run_id
    assert manifest.git_commit == "998c00c4a7384851667dd5ea648533eddf29b92d"
    assert manifest.python_version != ""
    assert manifest.platform != ""


def test_benchmark_result_add_metric():
    """BenchmarkResult accumulates metrics and serializes cleanly."""
    result = BenchmarkResult(
        run_id="run-123456",
        mode=EvaluationMode.MODE_B_REAL_INFRASTRUCTURE,
        status=BenchmarkStatus.PASSED,
        duration_ms=4500,
    )
    result.add_metric("TASK_SUCCESS_RATE", 1.0, "ratio", threshold=1.0, passed=True)
    result.add_metric("REGRESSION_RATE", 0.0, "ratio", threshold=0.0, passed=True)
    result.add_metric("FUNCTIONAL_CORRECTNESS", True, "bool", threshold=True, passed=True)

    assert len(result.metrics) == 3
    assert result.metrics["TASK_SUCCESS_RATE"].passed is True
    assert result.metrics["REGRESSION_RATE"].value == 0.0

    raw_json = result.model_dump_json()
    assert "run-123456" in raw_json
    assert "FUNCTIONAL_CORRECTNESS" in raw_json


# ==============================================================================
# 2. Target Fixture Scaffolding & Defect Verification Tests
# ==============================================================================
def test_target_fixture_structure_exists():
    """Target fixture repository exists with complete source, config, and tests."""
    fixture_dir = Path("tests/fixtures/phase13_inventory")
    assert fixture_dir.exists() and fixture_dir.is_dir()

    assert (fixture_dir / "pyproject.toml").exists()
    assert (fixture_dir / "README.md").exists()
    assert (fixture_dir / "src" / "inventory" / "models.py").exists()
    assert (fixture_dir / "src" / "inventory" / "service.py").exists()
    assert (fixture_dir / "src" / "inventory" / "api.py").exists()
    assert (fixture_dir / "tests" / "test_items.py").exists()
    assert (fixture_dir / "tests" / "test_transfers.py").exists()
    assert (fixture_dir / "tests" / "test_stock.py").exists()


def test_fixture_baseline_and_intentional_defects():
    """Programmatic execution of fixture tests verifies passing baseline and failing defects."""
    import sys
    from pathlib import Path

    fixture_src = Path("tests/fixtures/phase13_inventory/src").resolve()
    if str(fixture_src) not in sys.path:
        sys.path.insert(0, str(fixture_src))

    from fastapi.testclient import TestClient
    from inventory.api import app
    from inventory.database import Base, engine

    Base.metadata.create_all(bind=engine)

    try:
        with TestClient(app) as client:
            # 1. Baseline passing test: Item catalog
            resp = client.post(
                "/items/",
                json={"sku": "SKU-TEST-BM", "name": "Benchmark Item", "unit_price": 25.0},
            )
            assert resp.status_code == 201

            # 2. Intentional Defect 1: Overdraft transfer is erroneously allowed (status 200 instead of 422)
            wh1 = client.post("/warehouses/", json={"code": "WH-T1", "name": "Warehouse 1"}).json()["id"]
            wh2 = client.post("/warehouses/", json={"code": "WH-T2", "name": "Warehouse 2"}).json()["id"]
            item_id = resp.json()["id"]

            # Initialize stock = 3
            client.post("/stock/adjust", json={"item_id": item_id, "warehouse_id": wh1, "delta": 3})

            # Attempt to transfer 10 (overdraw)
            transfer_resp = client.post(
                "/transfers/",
                json={
                    "item_id": item_id,
                    "source_warehouse_id": wh1,
                    "dest_warehouse_id": wh2,
                    "quantity": 10,
                },
            )
            # Confirms Defect 1: returned 200 instead of 422, causing stock to become -7
            assert transfer_resp.status_code == 200, "Defect 1 verification: transfer should erroneously succeed"
            assert client.get(f"/stock/{wh1}/{item_id}").json()["quantity"] == -7

            # 3. Intentional Defect 2: Timezone offset query causes 500 error
            from datetime import datetime, timedelta, timezone

            past_utc = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
            tz_resp = client.get(f"/stock/{wh1}/ledger?from_time={past_utc}")
            # Confirms Defect 2: returned 500 comparison error
            assert tz_resp.status_code == 500, "Defect 2 verification: timezone comparison should crash with 500"
            assert "Timezone comparison error" in tz_resp.json()["detail"]

    finally:
        Base.metadata.drop_all(bind=engine)


def test_anti_self_targeting_constraint():
    """Crucial constraint: SYNTRA's own repository is never the target fixture."""
    syntra_src = Path("src/syntra")
    assert syntra_src.exists()

    # SYNTRA source must not contain inventory fixture models
    assert not (syntra_src / "inventory").exists()
    assert not (syntra_src / "models" / "inventory.py").exists()

    # The fixture path must strictly reside under tests/fixtures
    fixture_dir = Path("tests/fixtures/phase13_inventory").resolve()
    assert "fixtures" in fixture_dir.parts


# ==============================================================================
# 3. Runner & Collector Tests (Milestone 13.2: Modes A & B)
# ==============================================================================
@pytest.mark.asyncio
async def test_runner_mode_a_deterministic():
    """Verify Mode A produces PASSED result with correct metrics."""
    runner = BenchmarkRunner()
    config = BenchmarkRunConfig(
        run_id="bm-mode-a-test",
        mode=EvaluationMode.MODE_A_DETERMINISTIC_MOCK,
        seed=42,
    )
    result = await runner.run(config)
    assert result.status == BenchmarkStatus.PASSED
    assert result.mode == EvaluationMode.MODE_A_DETERMINISTIC_MOCK
    assert result.unified_diff is not None
    assert result.verification_hash is not None
    assert len(result.metrics) == 6
    assert result.metrics["TASK_SUCCESS_RATE"].passed is True
    assert result.metrics["FUNCTIONAL_CORRECTNESS"].passed is True
    assert result.metrics["REGRESSION_RATE"].passed is True
    assert result.metrics["MEAN_TASK_DURATION_MS"].passed is True
    assert result.metrics["TOKEN_USAGE"].passed is True
    assert result.metrics["ESTIMATED_MODEL_COST_USD"].passed is True


@pytest.mark.asyncio
async def test_runner_mode_a_reproducibility():
    """Run Mode A twice with the same seed and verify identical patch hash and metrics."""
    runner = BenchmarkRunner()
    config1 = BenchmarkRunConfig(
        run_id="bm-rep-1",
        mode=EvaluationMode.MODE_A_DETERMINISTIC_MOCK,
        seed=42,
    )
    config2 = BenchmarkRunConfig(
        run_id="bm-rep-2",
        mode=EvaluationMode.MODE_A_DETERMINISTIC_MOCK,
        seed=42,
    )
    res1 = await runner.run(config1)
    res2 = await runner.run(config2)

    assert res1.status == BenchmarkStatus.PASSED
    assert res2.status == BenchmarkStatus.PASSED

    assert res1.unified_diff is not None
    assert res2.unified_diff is not None
    hash1 = hashlib.sha256(res1.unified_diff.encode("utf-8")).hexdigest()
    hash2 = hashlib.sha256(res2.unified_diff.encode("utf-8")).hexdigest()
    assert hash1 == hash2

    assert res1.metrics["TASK_SUCCESS_RATE"].value == res2.metrics["TASK_SUCCESS_RATE"].value
    assert res1.metrics["FUNCTIONAL_CORRECTNESS"].value == res2.metrics["FUNCTIONAL_CORRECTNESS"].value
    assert res1.metrics["REGRESSION_RATE"].value == res2.metrics["REGRESSION_RATE"].value


@pytest.mark.asyncio
async def test_runner_mode_b_infrastructure():
    """Verify Mode B creates real worktree, applies patch, and runs verification."""
    runner = BenchmarkRunner()
    config = BenchmarkRunConfig(
        run_id="bm-mode-b-test",
        mode=EvaluationMode.MODE_B_REAL_INFRASTRUCTURE,
        seed=100,
    )
    result = await runner.run(config)
    assert result.status == BenchmarkStatus.PASSED
    assert result.mode == EvaluationMode.MODE_B_REAL_INFRASTRUCTURE
    assert result.metrics["FUNCTIONAL_CORRECTNESS"].passed is True
    assert result.metrics["TASK_SUCCESS_RATE"].passed is True


def test_collector_metric_completeness():
    """Verify collector emits all 6 required metrics."""
    collector = BenchmarkCollector()
    metrics = collector.collect(
        run_id="test-col-1",
        mode=EvaluationMode.MODE_A_DETERMINISTIC_MOCK,
    )
    required_names = {
        "TASK_SUCCESS_RATE",
        "FUNCTIONAL_CORRECTNESS",
        "REGRESSION_RATE",
        "MEAN_TASK_DURATION_MS",
        "TOKEN_USAGE",
        "ESTIMATED_MODEL_COST_USD",
    }
    assert required_names.issubset(set(metrics.keys()))
    assert metrics["TASK_SUCCESS_RATE"].unit == "ratio"
    assert metrics["FUNCTIONAL_CORRECTNESS"].unit == "bool"
    assert metrics["REGRESSION_RATE"].unit == "ratio"
    assert metrics["MEAN_TASK_DURATION_MS"].unit == "ms"
    assert metrics["TOKEN_USAGE"].unit == "tokens"
    assert metrics["ESTIMATED_MODEL_COST_USD"].unit == "USD"


def test_collector_metric_thresholds():
    """Verify threshold pass/fail evaluations are correct."""
    from syntra.domain.entities import VerificationEvidence, VerificationRecord, VerificationStatus

    collector = BenchmarkCollector()

    # Failing case: 0 succeeded out of 1 attempted
    metrics_fail = collector.collect(
        run_id="test-col-fail",
        mode=EvaluationMode.MODE_A_DETERMINISTIC_MOCK,
        tasks_attempted=1,
        tasks_succeeded=0,
        verification_record=None,
        new_test_failures=5,
        task_durations_ms=[45000],
    )
    assert metrics_fail["TASK_SUCCESS_RATE"].passed is False
    assert metrics_fail["FUNCTIONAL_CORRECTNESS"].passed is False
    assert metrics_fail["REGRESSION_RATE"].passed is False
    assert metrics_fail["MEAN_TASK_DURATION_MS"].passed is False

    # Passing case
    rec = VerificationRecord(
        id=uuid4(),
        org_id=uuid4(),
        mission_id=uuid4(),
        task_id=uuid4(),
        task_attempt_id=uuid4(),
        plan_version=1,
        status=VerificationStatus.PASSED,
        clean_base_commit="0" * 64,
        patch_hash="1" * 64,
        protected_test_suite_hash="2" * 64,
        evidence=VerificationEvidence(
            exit_code=0,
            execution_duration_ms=250,
            stdout_digest="x" * 64,
            stderr_digest="y" * 64,
            tests_passed=7,
        ),
        verifier_signature="0" * 64,
    )
    metrics_pass = collector.collect(
        run_id="test-col-pass",
        mode=EvaluationMode.MODE_A_DETERMINISTIC_MOCK,
        tasks_attempted=1,
        tasks_succeeded=1,
        verification_record=rec,
        new_test_failures=0,
        task_durations_ms=[500],
    )
    assert metrics_pass["TASK_SUCCESS_RATE"].passed is True
    assert metrics_pass["FUNCTIONAL_CORRECTNESS"].passed is True
    assert metrics_pass["REGRESSION_RATE"].passed is True
    assert metrics_pass["MEAN_TASK_DURATION_MS"].passed is True


@pytest.mark.asyncio
async def test_runner_fixture_isolation():
    """Verify runner never modifies SYNTRA source (src/syntra/) or fixture in-place."""
    fixture_service = Path("tests/fixtures/phase13_inventory/src/inventory/service.py")
    original_fixture_content = fixture_service.read_text(encoding="utf-8")

    syntra_init = Path("src/syntra/__init__.py")
    original_syntra_content = syntra_init.read_text(encoding="utf-8")

    runner = BenchmarkRunner()
    config = BenchmarkRunConfig(
        run_id="bm-isolation-test",
        mode=EvaluationMode.MODE_A_DETERMINISTIC_MOCK,
    )
    await runner.run(config)

    # Verify fixture source remained untouched (still contains intentional defects)
    assert fixture_service.read_text(encoding="utf-8") == original_fixture_content
    assert "if source_stock.quantity <= 0:" in fixture_service.read_text(encoding="utf-8")

    # Verify SYNTRA root code remained untouched
    assert syntra_init.read_text(encoding="utf-8") == original_syntra_content


@pytest.mark.asyncio
async def test_runner_mode_d_worker_interruption_recovery():
    """Verify Mode D executes active worker interruption via SIGKILL, fences token, and recovers."""
    runner = BenchmarkRunner()
    config = BenchmarkRunConfig(
        run_id="bm-mode-d-test",
        mode=EvaluationMode.MODE_D_FAULT_RECOVERY,
        seed=101,
    )
    result = await runner.run(config)

    # Status must be RECOVERED or PASSED
    assert result.status in (BenchmarkStatus.RECOVERED, BenchmarkStatus.PASSED)
    assert result.mode == EvaluationMode.MODE_D_FAULT_RECOVERY

    # Must contain RECOVERY_SUCCESS_RATE metric meeting threshold >= 1.0
    assert "RECOVERY_SUCCESS_RATE" in result.metrics
    recovery_metric = result.metrics["RECOVERY_SUCCESS_RATE"]
    assert recovery_metric.value == 1.0
    assert recovery_metric.unit == "ratio"
    assert recovery_metric.threshold == 1.0
    assert recovery_metric.passed is True
    assert "SIGKILL" in (recovery_metric.details or "")

    # Verification must have passed on second attempt
    assert result.metrics["FUNCTIONAL_CORRECTNESS"].passed is True
    assert result.verification_hash is not None
    assert result.unified_diff is not None


def test_collector_mode_d_metrics():
    """Verify RECOVERY_SUCCESS_RATE metric is recorded and evaluated against threshold in Mode D."""
    collector = BenchmarkCollector()

    # Successful recovery scenario
    metrics_success = collector.collect(
        run_id="test-col-d-success",
        mode=EvaluationMode.MODE_D_FAULT_RECOVERY,
        recovery_scenarios_attempted=1,
        recovery_scenarios_succeeded=1,
        recovery_duration_ms=450,
        interrupted_worker_pid=12345,
        interruption_signal="SIGKILL",
        retry_attempts=2,
    )
    assert "RECOVERY_SUCCESS_RATE" in metrics_success
    m_succ = metrics_success["RECOVERY_SUCCESS_RATE"]
    assert m_succ.value == 1.0
    assert m_succ.unit == "ratio"
    assert m_succ.threshold == 1.0
    assert m_succ.passed is True
    assert "12345" in (m_succ.details or "")
    assert "SIGKILL" in (m_succ.details or "")

    # Failed recovery scenario (0 succeeded)
    metrics_fail = collector.collect(
        run_id="test-col-d-fail",
        mode=EvaluationMode.MODE_D_FAULT_RECOVERY,
        recovery_scenarios_attempted=1,
        recovery_scenarios_succeeded=0,
        recovery_duration_ms=5000,
        interrupted_worker_pid=12346,
        interruption_signal="SIGKILL",
        retry_attempts=1,
    )
    assert "RECOVERY_SUCCESS_RATE" in metrics_fail
    m_fail = metrics_fail["RECOVERY_SUCCESS_RATE"]
    assert m_fail.value == 0.0
    assert m_fail.passed is False


@pytest.mark.asyncio
async def test_reporter_generates_all_artifacts(tmp_path):
    """Execute runner in Mode A, generate report, and assert all 4 artifacts exist and parse cleanly."""
    runner = BenchmarkRunner()
    config = BenchmarkRunConfig(
        run_id="bm-rep-mode-a",
        mode=EvaluationMode.MODE_A_DETERMINISTIC_MOCK,
        seed=42,
    )
    result = await runner.run(config)
    manifest = RunManifest(
        run_id=config.run_id,
        git_commit="test-commit-sha",
        mode=config.mode,
        seed=config.seed,
    )

    reporter = BenchmarkReporter()
    report_dir = reporter.generate_report(result, manifest, output_dir=tmp_path / "mode_a_report")

    # Assert all 4 canonical artifacts exist
    manifest_file = report_dir / "manifest.json"
    summary_file = report_dir / "summary.json"
    audit_file = report_dir / "audit.jsonl"
    verification_file = report_dir / "verification.json"

    assert manifest_file.is_file()
    assert summary_file.is_file()
    assert audit_file.is_file()
    assert verification_file.is_file()

    # Parse and validate contents
    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest_data["run_id"] == "bm-rep-mode-a"
    assert manifest_data["mode"] == EvaluationMode.MODE_A_DETERMINISTIC_MOCK.value

    summary_data = json.loads(summary_file.read_text(encoding="utf-8"))
    assert summary_data["run_id"] == "bm-rep-mode-a"
    assert summary_data["status"] == BenchmarkStatus.PASSED.value
    assert "metrics" in summary_data
    assert "TASK_SUCCESS_RATE" in summary_data["metrics"]
    assert "FUNCTIONAL_CORRECTNESS" in summary_data["metrics"]

    v_data = json.loads(verification_file.read_text(encoding="utf-8"))
    assert v_data["status"] == "PASSED"
    assert v_data["exit_code"] == 0
    assert v_data["tests_passed"] >= 7
    assert "verifier_signature" in v_data

    # Audit file contains JSONL records
    audit_lines = [line.strip() for line in audit_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(audit_lines) >= 1
    first_record = json.loads(audit_lines[0])
    assert "sha256" in first_record
    assert "event_type" in first_record


@pytest.mark.asyncio
async def test_reporter_mode_d_artifacts(tmp_path):
    """Execute runner in Mode D, generate report, and assert summary includes RECOVERY_SUCCESS_RATE."""
    runner = BenchmarkRunner()
    config = BenchmarkRunConfig(
        run_id="bm-rep-mode-d",
        mode=EvaluationMode.MODE_D_FAULT_RECOVERY,
        seed=102,
    )
    result = await runner.run(config)
    manifest = RunManifest(
        run_id=config.run_id,
        git_commit="test-commit-sha-d",
        mode=config.mode,
        seed=config.seed,
    )

    reporter = BenchmarkReporter()
    report_dir = reporter.generate_report(result, manifest, output_dir=tmp_path / "mode_d_report")

    summary_file = report_dir / "summary.json"
    assert summary_file.is_file()
    summary_data = json.loads(summary_file.read_text(encoding="utf-8"))
    assert summary_data["status"] == BenchmarkStatus.RECOVERED.value
    assert "RECOVERY_SUCCESS_RATE" in summary_data["metrics"]
    rec_metric = summary_data["metrics"]["RECOVERY_SUCCESS_RATE"]
    assert rec_metric["value"] == 1.0
    assert rec_metric["passed"] is True
    assert "SIGKILL" in rec_metric["details"]


@pytest.mark.asyncio
async def test_reporter_integrity_and_tamper_detection(tmp_path):
    """Assert verify_report_integrity returns True on valid output, and detects tampering."""
    runner = BenchmarkRunner()
    config = BenchmarkRunConfig(
        run_id="bm-rep-integrity",
        mode=EvaluationMode.MODE_A_DETERMINISTIC_MOCK,
        seed=42,
    )
    result = await runner.run(config)
    manifest = RunManifest(
        run_id=config.run_id,
        git_commit="test-commit-sha",
        mode=config.mode,
        seed=config.seed,
    )

    reporter = BenchmarkReporter()
    report_dir = reporter.generate_report(result, manifest, output_dir=tmp_path / "integrity_report")

    # 1. Valid report verifies True
    assert reporter.verify_report_integrity(report_dir) is True

    # 2. Tamper with audit.jsonl: modify payload
    audit_file = report_dir / "audit.jsonl"
    original_audit = audit_file.read_text(encoding="utf-8")
    lines = [json.loads(line_str) for line_str in original_audit.splitlines() if line_str.strip()]
    lines[0]["payload"]["tampered"] = True
    audit_file.write_text("\n".join(json.dumps(rec) for rec in lines) + "\n", encoding="utf-8")

    assert reporter.verify_report_integrity(report_dir, raise_on_error=False) is False
    with pytest.raises(BenchmarkIntegrityError):
        reporter.verify_report_integrity(report_dir, raise_on_error=True)

    # Restore audit.jsonl
    audit_file.write_text(original_audit, encoding="utf-8")
    assert reporter.verify_report_integrity(report_dir) is True

    # 3. Tamper with verification.json: modify exit_code
    v_file = report_dir / "verification.json"
    original_v = v_file.read_text(encoding="utf-8")
    v_data = json.loads(original_v)
    v_data["exit_code"] = 99
    v_file.write_text(json.dumps(v_data), encoding="utf-8")

    assert reporter.verify_report_integrity(report_dir, raise_on_error=False) is False
    with pytest.raises(BenchmarkIntegrityError):
        reporter.verify_report_integrity(report_dir, raise_on_error=True)

    # Restore verification.json
    v_file.write_text(original_v, encoding="utf-8")
    assert reporter.verify_report_integrity(report_dir) is True

    # 4. Missing file detection
    (report_dir / "manifest.json").unlink()
    assert reporter.verify_report_integrity(report_dir, raise_on_error=False) is False
    with pytest.raises(BenchmarkIntegrityError):
        reporter.verify_report_integrity(report_dir, raise_on_error=True)
