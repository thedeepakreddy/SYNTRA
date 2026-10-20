"""Domain models, evaluation schemas, and metrics definitions for SYNTRA benchmarks."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

from syntra.domain.entities import VerificationRecord


class EvaluationMode(str, Enum):
    """The four canonical evaluation modes for Phase 13 benchmarking."""

    MODE_A_DETERMINISTIC_MOCK = "mode_a_deterministic_mock"
    MODE_B_REAL_INFRASTRUCTURE = "mode_b_real_infrastructure"
    MODE_C_LIVE_MODEL = "mode_c_live_model"
    MODE_D_FAULT_RECOVERY = "mode_d_fault_recovery"


class BenchmarkStatus(str, Enum):
    """Execution status of a benchmark evaluation run."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    RECOVERED = "RECOVERED"


class BenchmarkMetric(BaseModel):
    """Individual quantitative or qualitative metric captured during a benchmark run."""

    name: str
    value: float | int | str | bool
    unit: str
    threshold: float | int | str | bool | None = None
    passed: bool = True
    details: str | None = None


class BenchmarkRunConfig(BaseModel):
    """Configuration specification for executing a benchmark run."""

    run_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    mode: EvaluationMode = EvaluationMode.MODE_A_DETERMINISTIC_MOCK
    fixture_path: Path = Field(default=Path("tests/fixtures/phase13_inventory"))
    iterations: int = Field(default=1, ge=1)
    seed: int = Field(default=42)
    budget_usd: Decimal = Field(default=Decimal("2.00"))
    timeout_seconds: int = Field(default=300, ge=10)


class RunManifest(BaseModel):
    """Reproducibility manifest recording environment and execution metadata."""

    run_id: str
    git_commit: str
    mode: EvaluationMode
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    seed: int
    python_version: str = Field(default_factory=lambda: sys.version.split()[0])
    platform: str = Field(default_factory=lambda: sys.platform)


class BenchmarkResult(BaseModel):
    """Machine-readable final result and telemetry summary of a benchmark run."""

    run_id: str
    mode: EvaluationMode
    status: BenchmarkStatus
    metrics: dict[str, BenchmarkMetric] = Field(default_factory=dict)
    unified_diff: str | None = None
    verification_hash: str | None = None
    verification_record: VerificationRecord | None = None
    error_message: str | None = None
    duration_ms: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def add_metric(
        self,
        name: str,
        value: float | int | str | bool,
        unit: str,
        threshold: float | int | str | bool | None = None,
        passed: bool = True,
        details: str | None = None,
    ) -> None:
        """Record a single benchmark metric."""
        self.metrics[name] = BenchmarkMetric(
            name=name,
            value=value,
            unit=unit,
            threshold=threshold,
            passed=passed,
            details=details,
        )
