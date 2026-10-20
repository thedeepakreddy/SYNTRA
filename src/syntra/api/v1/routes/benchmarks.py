"""Benchmark results and evaluation telemetry endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from syntra.api.auth.dependencies import require_viewer_or_above
from syntra.api.auth.models import AuthenticatedUser

router = APIRouter(prefix="/benchmarks", tags=["Benchmarks"])

BENCHMARK_RESULTS_DIR = Path("benchmarks/results")


class BenchmarkRunSummary(BaseModel):
    """Summary of a completed benchmark evaluation run."""

    run_id: str
    mode: str
    status: str
    duration_ms: int
    verification_hash: str | None = None
    created_at: str | None = None
    metrics_count: int = 0


class BenchmarkRunDetail(BaseModel):
    """Detailed benchmark evaluation run including all metrics and manifest."""

    run_id: str
    mode: str
    status: str
    duration_ms: int
    verification_hash: str | None = None
    created_at: str | None = None
    manifest: dict[str, Any] = {}
    summary: dict[str, Any] = {}
    verification: dict[str, Any] = {}


@router.get("", response_model=list[BenchmarkRunSummary])
async def list_benchmarks(
    user: Annotated[AuthenticatedUser, Depends(require_viewer_or_above)],
) -> list[BenchmarkRunSummary]:
    """List all completed benchmark runs persisted on disk."""
    if not BENCHMARK_RESULTS_DIR.exists():
        return []

    summaries: list[BenchmarkRunSummary] = []
    for run_dir in sorted(BENCHMARK_RESULTS_DIR.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue
        summary_file = run_dir / "summary.json"
        if summary_file.is_file():
            try:
                data = json.loads(summary_file.read_text(encoding="utf-8"))
                metrics = data.get("metrics", {})
                summaries.append(
                    BenchmarkRunSummary(
                        run_id=data.get("run_id", run_dir.name),
                        mode=data.get("mode", "unknown"),
                        status=data.get("status", "UNKNOWN"),
                        duration_ms=data.get("duration_ms", 0),
                        verification_hash=data.get("verification_hash"),
                        created_at=data.get("created_at"),
                        metrics_count=len(metrics),
                    )
                )
            except Exception:
                pass
    return summaries


@router.get("/{run_id}", response_model=BenchmarkRunDetail)
async def get_benchmark_detail(
    run_id: str,
    user: Annotated[AuthenticatedUser, Depends(require_viewer_or_above)],
) -> BenchmarkRunDetail:
    """Retrieve full artifacts and metrics for a specific benchmark evaluation run."""
    run_dir = BENCHMARK_RESULTS_DIR / run_id
    if not run_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark run '{run_id}' not found.",
        )

    summary_file = run_dir / "summary.json"
    manifest_file = run_dir / "manifest.json"
    verification_file = run_dir / "verification.json"

    if not summary_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Summary artifact missing for benchmark run '{run_id}'.",
        )

    summary_data = json.loads(summary_file.read_text(encoding="utf-8"))
    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.is_file() else {}
    verification_data = json.loads(verification_file.read_text(encoding="utf-8")) if verification_file.is_file() else {}

    return BenchmarkRunDetail(
        run_id=summary_data.get("run_id", run_id),
        mode=summary_data.get("mode", "unknown"),
        status=summary_data.get("status", "UNKNOWN"),
        duration_ms=summary_data.get("duration_ms", 0),
        verification_hash=summary_data.get("verification_hash"),
        created_at=summary_data.get("created_at"),
        manifest=manifest_data,
        summary=summary_data,
        verification=verification_data,
    )
