"""SYNTRA Benchmarking and Evaluation Subsystem.

Provides reproducible multi-mode evaluation harnesses across deterministic mock models,
real infrastructure integration, live model evaluation, and controlled fault injection.
"""

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

__all__ = [
    "EvaluationMode",
    "BenchmarkStatus",
    "BenchmarkMetric",
    "BenchmarkRunConfig",
    "RunManifest",
    "BenchmarkResult",
    "BenchmarkCollector",
    "BenchmarkRunner",
    "BenchmarkReporter",
    "BenchmarkIntegrityError",
]
