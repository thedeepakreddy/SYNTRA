import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { BenchmarkRunDetail, BenchmarkRunSummary } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { Gauge } from 'lucide-react';

const CANONICAL_METRICS = [
  { key: 'TASK_SUCCESS_RATE', label: 'Task Success Rate', unit: '%', isPct: true, threshold: '>= 85%' },
  { key: 'VERIFICATION_PASS_RATE', label: 'Verification Pass Rate', unit: '%', isPct: true, threshold: '>= 90%' },
  { key: 'REGRESSION_DETECTION_RATE', label: 'Regression Detection Rate', unit: '%', isPct: true, threshold: '>= 95%' },
  { key: 'MEAN_TIME_TO_REMEDIATE_MS', label: 'Mean Time to Remediate', unit: 'ms', isPct: false, threshold: '<= 120,000 ms' },
  { key: 'RECOVERY_SUCCESS_RATE', label: 'Recovery Success Rate', unit: '%', isPct: true, threshold: '>= 90%' },
  { key: 'COST_PER_SUCCESSFUL_FIX_USD', label: 'Cost / Fix', unit: '$', isPct: false, threshold: '<= $0.50' },
];

export const BenchmarksPage: React.FC = () => {
  const [runs, setRuns] = useState<BenchmarkRunSummary[]>([]);
  const [selectedRun, setSelectedRun] = useState<BenchmarkRunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRuns = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getBenchmarks();
      setRuns(data);
      if (data.length > 0) {
        await selectRun(data[0].run_id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load benchmark runs.');
    } finally {
      setLoading(false);
    }
  };

  const selectRun = async (runId: string) => {
    try {
      setDetailLoading(true);
      const detail = await apiClient.getBenchmarkRun(runId);
      setSelectedRun(detail);
    } catch {
      setSelectedRun(null);
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, []);

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow">
        <div className="flex items-center space-x-3">
          <div className="rounded-lg bg-emerald-600/20 p-2 text-emerald-400 border border-emerald-500/30">
            <Gauge className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight text-white">
              Benchmarking & Quantitative Quality Evaluation
            </h2>
            <p className="mt-1 text-xs text-slate-400 max-w-3xl">
              Evaluation suite testing end-to-end multi-agent defect remediation, regression detection,
              worker fault interruption recovery, and financial efficiency against real code fixtures.
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-800 bg-rose-950/40 p-4 text-xs text-rose-300">
          <p className="font-semibold">Error Loading Benchmarks</p>
          <p className="mt-1 font-mono">{error}</p>
        </div>
      )}

      {/* Main Content Grid: Runs List & Detailed Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Runs List */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-3">
          <h3 className="text-xs font-semibold text-slate-300 pb-2 border-b border-slate-800">
            Benchmark Run History ({runs.length})
          </h3>

          {loading ? (
            <div className="p-4 text-center text-xs text-slate-500">Loading runs...</div>
          ) : runs.length === 0 ? (
            <div className="p-4 text-center text-xs text-slate-500">
              No benchmark runs recorded in this environment yet.
            </div>
          ) : (
            <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
              {runs.map((r) => {
                const isSelected = selectedRun?.run_id === r.run_id;
                return (
                  <div
                    key={r.run_id}
                    onClick={() => selectRun(r.run_id)}
                    className={`cursor-pointer rounded-lg border p-3 text-xs transition-colors ${
                      isSelected
                        ? 'border-indigo-500 bg-indigo-950/30'
                        : 'border-slate-800 bg-slate-950 hover:bg-slate-900'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-semibold text-slate-200">{r.run_id}</span>
                      <StatusBadge status={r.status} />
                    </div>
                    <div className="mt-1.5 flex items-center justify-between text-[11px] text-slate-400 font-mono">
                      <span>{r.mode.replace(/_/g, ' ')}</span>
                      <span>{(r.duration_ms / 1000).toFixed(1)}s</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right: Selected Run Evaluation Dashboard */}
        <div className="lg:col-span-2 space-y-4">
          {detailLoading ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-8 text-center text-xs text-slate-500">
              Loading benchmark report...
            </div>
          ) : selectedRun ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-5">
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-3">
                <div>
                  <div className="flex items-center space-x-2">
                    <StatusBadge status={selectedRun.status} />
                    <h3 className="font-mono text-sm font-bold text-slate-100">
                      {selectedRun.run_id}
                    </h3>
                  </div>
                  <p className="text-xs text-slate-400 mt-1 font-mono">Mode: {selectedRun.mode}</p>
                </div>
                <div className="text-xs text-slate-400 font-mono text-right">
                  <div>Duration: {(selectedRun.duration_ms / 1000).toFixed(2)}s</div>
                  {selectedRun.audit_count !== undefined && (
                    <div className="text-[10px] text-slate-500">
                      Audit Records: {selectedRun.audit_count}
                    </div>
                  )}
                </div>
              </div>

              {/* 6 Canonical Evaluation Metrics */}
              <div>
                <h4 className="text-xs font-semibold text-slate-300 mb-3">
                  Canonical Evaluation Suite Metrics (Phase 13 Baseline)
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {CANONICAL_METRICS.map((m) => {
                    const raw = selectedRun.metrics[m.key];
                    let val: number | null = null;
                    let passed: boolean | null = null;
                    if (typeof raw === 'number') {
                      val = raw;
                    } else if (raw && typeof raw === 'object' && 'value' in raw) {
                      val = raw.value;
                      passed = raw.passed ?? null;
                    }

                    return (
                      <div
                        key={m.key}
                        className="rounded-lg bg-slate-950 p-3 border border-slate-800 font-mono text-xs"
                      >
                        <div className="flex items-center justify-between text-slate-400">
                          <span className="text-[11px] font-sans font-medium">{m.label}</span>
                          <span className="text-[10px] text-slate-500">Threshold: {m.threshold}</span>
                        </div>
                        <div className="mt-2 flex items-baseline justify-between">
                          <span className="text-base font-bold text-slate-100">
                            {val !== null
                              ? m.isPct
                                ? `${(val * 100).toFixed(1)}%`
                                : m.unit === '$'
                                ? `$${val.toFixed(4)}`
                                : `${val.toFixed(0)} ms`
                              : 'N/A'}
                          </span>
                          {passed !== null && (
                            <span
                              className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                                passed
                                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                                  : 'bg-rose-950 text-rose-300 border border-rose-800'
                              }`}
                            >
                              {passed ? 'PASS' : 'FAIL'}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Manifest Metadata */}
              {selectedRun.manifest && (
                <div className="rounded-lg bg-slate-950 p-3 border border-slate-800">
                  <span className="text-xs font-semibold text-slate-400 block mb-1">
                    Run Manifest & Integrity
                  </span>
                  <pre className="overflow-x-auto text-[10px] font-mono text-slate-400">
                    {JSON.stringify(selectedRun.manifest, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-8 text-center text-xs text-slate-500">
              Select a benchmark run from the list to view full performance metrics.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
