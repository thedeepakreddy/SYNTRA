import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { BenchmarkRunDetail, BenchmarkRunSummary } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { Award } from 'lucide-react';

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
    <div className="space-y-8 pb-12">
      {/* Top Hero: Machined Hardware Double-Bezel Enclosure */}
      <div className="double-bezel-outer">
        <div className="double-bezel-inner p-6 sm:p-8 relative overflow-hidden">
          {/* Ambient Photon Atmosphere */}
          <div className="absolute -top-24 -right-24 w-96 h-96 rounded-full bg-emerald-500/10 blur-3xl pointer-events-none" />
          <div className="absolute -bottom-24 left-1/3 w-80 h-80 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />

          <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="eyebrow-pill text-emerald-400 border-emerald-500/30">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                  BENCHMARK RIG // EMPIRICAL VALIDATION
                </span>
                <span className="px-2.5 py-0.5 rounded-full bg-slate-900/80 border border-white/10 text-[10px] font-mono text-slate-400">
                  PHASE 13 ACCREDITED
                </span>
              </div>
              <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-white font-sans drop-shadow-[0_0_14px_rgba(0,255,157,0.3)]">
                Benchmarking &amp; Quantitative Quality Evaluation
              </h2>
              <p className="text-xs sm:text-sm text-slate-300 max-w-2xl font-sans leading-relaxed">
                Empirical evaluation suite testing end-to-end multi-agent defect remediation, regression detection,
                worker fault interruption recovery, and cost efficiency against isolated target repository fixtures.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
              <span className="inline-flex items-center space-x-2 rounded-full bg-emerald-950/80 px-4 py-2 text-xs font-mono font-semibold text-emerald-300 border border-emerald-400/40 shadow-[0_0_14px_rgba(0,255,157,0.2),inset_0_1px_1px_rgba(255,255,255,0.25)]">
                <Award className="h-4 w-4 text-emerald-400" />
                <span>Phase 13 Baseline Verified</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-2xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 backdrop-blur-xl shadow-[0_0_20px_rgba(255,0,85,0.2)]">
          <p className="font-semibold font-sans">Error Loading Benchmarks</p>
          <p className="mt-1 font-mono text-[11px]">{error}</p>
        </div>
      )}

      {/* Main Content Grid: Runs List & Detailed Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Runs List */}
        <div className="double-bezel-outer">
          <div className="double-bezel-inner p-5 space-y-3">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                Run History ({runs.length})
              </h3>
              <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_8px_#00F0FF]" />
            </div>

            {loading ? (
              <div className="p-10 text-center text-xs text-slate-400 font-mono tracking-wider">
                <span className="inline-block animate-spin mr-2 text-cyan-400">◓</span>
                LOADING BENCHMARK RUNS...
              </div>
            ) : runs.length === 0 ? (
              <div className="p-10 text-center text-xs text-slate-400 font-mono tracking-wider">
                NO BENCHMARK RUNS RECORDED YET.
              </div>
            ) : (
              <div className="space-y-2.5 max-h-[540px] overflow-y-auto pr-1">
                {runs.map((r) => {
                  const isSelected = selectedRun?.run_id === r.run_id;
                  return (
                    <div
                      key={r.run_id}
                      onClick={() => selectRun(r.run_id)}
                      className={`cursor-pointer rounded-xl border p-3.5 text-xs transition-all duration-200 relative ${
                        isSelected
                          ? 'border-cyan-400/50 bg-gradient-to-r from-cyan-500/20 via-cyan-500/10 to-transparent shadow-[0_0_18px_rgba(0,240,255,0.2),inset_0_1px_1px_rgba(255,255,255,0.3)]'
                          : 'border-white/[0.08] bg-slate-950/70 hover:bg-white/[0.04] hover:border-white/[0.15]'
                      }`}
                    >
                      {isSelected && (
                        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 rounded-r bg-cyan-400 shadow-[0_0_12px_#00F0FF]" />
                      )}
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-white">{r.run_id}</span>
                        <StatusBadge status={r.status} />
                      </div>
                      <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400 font-mono">
                        <span className="text-cyan-400/80 font-bold uppercase">{r.mode.replace(/_/g, ' ')}</span>
                        <span>{(r.duration_ms / 1000).toFixed(1)}s</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right: Selected Run Evaluation Dashboard */}
        <div className="lg:col-span-2 space-y-4">
          {detailLoading ? (
            <div className="double-bezel-outer">
              <div className="double-bezel-inner p-14 text-center text-xs text-slate-400 font-mono tracking-wider">
                <span className="inline-block animate-spin mr-2 text-cyan-400">◓</span>
                COMPILING EVALUATION REPORT...
              </div>
            </div>
          ) : selectedRun ? (
            <div className="double-bezel-outer">
              <div className="double-bezel-inner p-6 sm:p-7 space-y-6">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-5 border-b border-white/[0.08] gap-3">
                  <div>
                    <div className="flex items-center space-x-3">
                      <StatusBadge status={selectedRun.status} />
                      <h3 className="font-mono text-base font-bold text-white tracking-wider">
                        {selectedRun.run_id}
                      </h3>
                    </div>
                    <p className="text-xs text-cyan-400/90 mt-1 font-mono font-semibold uppercase">
                      Execution Mode: {selectedRun.mode}
                    </p>
                  </div>
                  <div className="text-xs text-slate-300 font-mono text-left sm:text-right space-y-0.5">
                    <div>
                      Duration: <span className="text-white font-bold">{(selectedRun.duration_ms / 1000).toFixed(2)}s</span>
                    </div>
                    {selectedRun.audit_count !== undefined && (
                      <div className="text-[10px] text-slate-400">
                        Audit Records: {selectedRun.audit_count}
                      </div>
                    )}
                  </div>
                </div>

                {/* 6 Canonical Evaluation Metrics */}
                <div className="space-y-3.5">
                  <h4 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-widest">
                    Canonical Evaluation Suite Metrics (Phase 13 Baseline)
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
                          className="liquid-glass-card rounded-xl p-4 border border-white/[0.08] font-mono text-xs"
                        >
                          <div className="flex items-center justify-between text-slate-400">
                            <span className="text-xs font-sans font-semibold text-white">{m.label}</span>
                            <span className="text-[10px] text-slate-400">Threshold: {m.threshold}</span>
                          </div>
                          <div className="mt-3 flex items-baseline justify-between">
                            <span className="text-xl font-bold text-cyan-300 drop-shadow-[0_0_8px_rgba(0,240,255,0.4)]">
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
                                className={`text-[10px] font-mono font-bold px-3 py-1 rounded-full ${
                                  passed
                                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-400/40 shadow-[0_0_10px_rgba(0,255,157,0.2)]'
                                    : 'bg-rose-950 text-rose-300 border border-rose-500/40 shadow-[0_0_10px_rgba(255,0,85,0.2)]'
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
                  <div className="liquid-glass-card rounded-xl p-4 border border-white/[0.08]">
                    <span className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider block mb-2">
                      Run Manifest &amp; Cryptographic Integrity
                    </span>
                    <pre className="overflow-x-auto text-[11px] font-mono text-cyan-200 bg-slate-950/90 p-4 rounded-xl border border-white/[0.06] leading-relaxed">
                      {JSON.stringify(selectedRun.manifest, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="double-bezel-outer">
              <div className="double-bezel-inner p-14 text-center text-xs text-slate-400 font-sans">
                Select a benchmark run from the list to view full performance metrics.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
