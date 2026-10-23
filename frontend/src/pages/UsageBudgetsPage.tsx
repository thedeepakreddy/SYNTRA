import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { Mission, MissionUsageSummary, SystemOverview } from '../types';
import { ShieldCheck, FileSpreadsheet, DollarSign, Cpu } from 'lucide-react';

export const UsageBudgetsPage: React.FC = () => {
  const [overview, setOverview] = useState<SystemOverview | null>(null);
  const [missions, setMissions] = useState<Mission[]>([]);
  const [selectedMissionId, setSelectedMissionId] = useState<string>('');
  const [missionUsage, setMissionUsage] = useState<MissionUsageSummary | null>(null);
  const [usageLoading, setUsageLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadInitial = async () => {
    try {
      setError(null);
      const [ov, mis] = await Promise.all([
        apiClient.getSystemOverview(),
        apiClient.getMissions(),
      ]);
      setOverview(ov);
      setMissions(mis);
      if (mis.length > 0) {
        setSelectedMissionId(mis[0].id);
        await loadMissionUsage(mis[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load usage & financial ledger data.');
    }
  };

  const loadMissionUsage = async (missionId: string) => {
    try {
      setUsageLoading(true);
      const u = await apiClient.getMissionUsage(missionId);
      setMissionUsage(u);
    } catch {
      setMissionUsage(null);
    } finally {
      setUsageLoading(false);
    }
  };

  useEffect(() => {
    loadInitial();
  }, []);

  const handleMissionChange = (mId: string) => {
    setSelectedMissionId(mId);
    loadMissionUsage(mId);
  };

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
                  TREASURY // TOKEN &amp; COST GOVERNANCE
                </span>
                <span className="px-2.5 py-0.5 rounded-full bg-slate-900/80 border border-white/10 text-[10px] font-mono text-slate-400">
                  HARD CEILING ENFORCEMENT
                </span>
              </div>
              <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-white font-sans drop-shadow-[0_0_14px_rgba(0,255,157,0.3)]">
                Financial Ledgers, Budgets &amp; Token Governance
              </h2>
              <p className="text-xs sm:text-sm text-slate-300 max-w-2xl font-sans leading-relaxed">
                Strict per-mission token quotas and USD financial accounting. Real-time circuit breakers halt execution
                immediately upon budget breach — preventing runaway API expenses with zero leakage.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
              <span className="inline-flex items-center space-x-2 rounded-full bg-emerald-950/80 px-4 py-2 text-xs font-mono font-semibold text-emerald-300 border border-emerald-400/40 shadow-[0_0_14px_rgba(0,255,157,0.2),inset_0_1px_1px_rgba(255,255,255,0.25)]">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                <span>Budget Enforcer Active</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-2xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 backdrop-blur-xl shadow-[0_0_20px_rgba(255,0,85,0.2)]">
          <p className="font-semibold font-sans">Error Loading Financial Ledgers</p>
          <p className="mt-1 font-mono text-[11px]">{error}</p>
        </div>
      )}

      {/* Aggregate KPI Cards - Machined Hardware Double-Bezel Architecture */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="double-bezel-outer group">
          <div className="double-bezel-inner p-5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest">
                Total Tokens Consumed
              </span>
              <div className="w-8 h-8 rounded-full bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 group-hover:scale-110 transition-transform">
                <Cpu className="w-4 h-4" />
              </div>
            </div>
            <div className="text-3xl font-bold font-mono text-cyan-300 drop-shadow-[0_0_12px_rgba(0,240,255,0.3)]">
              {overview ? Number(overview.total_tokens_consumed).toLocaleString() : '0'}
            </div>
            <p className="text-[11px] text-slate-400 font-sans">Across all orchestrated missions &amp; agent tasks</p>
          </div>
        </div>

        <div className="double-bezel-outer group">
          <div className="double-bezel-inner p-5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest">
                Total Incurred Cost
              </span>
              <div className="w-8 h-8 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 group-hover:scale-110 transition-transform">
                <DollarSign className="w-4 h-4" />
              </div>
            </div>
            <div className="text-3xl font-bold font-mono text-emerald-300 drop-shadow-[0_0_12px_rgba(0,255,157,0.3)]">
              ${overview ? Number(overview.total_cost_usd).toFixed(4) : '0.0000'}
            </div>
            <p className="text-[11px] text-slate-400 font-sans">Live calculated ledger with exact provider rates</p>
          </div>
        </div>

        <div className="double-bezel-outer group">
          <div className="double-bezel-inner p-5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest">
                Governance Ceiling
              </span>
              <div className="w-8 h-8 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#00FF9D] animate-pulse" />
              </div>
            </div>
            <div className="text-2xl font-bold text-white font-mono tracking-wider flex items-center gap-2">
              <span className="text-emerald-400">IN_BUDGET</span>
            </div>
            <p className="text-[11px] text-slate-400 font-sans">Hard token &amp; dollar cap active per mission</p>
          </div>
        </div>
      </div>

      {/* Mission-Level Financial Ledger Section */}
      <div className="double-bezel-outer">
        <div className="double-bezel-inner p-6 sm:p-7 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-5 border-b border-white/[0.08] gap-4">
            <div className="space-y-1">
              <div className="flex items-center space-x-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-400/30 text-emerald-300">
                  <FileSpreadsheet className="h-4 w-4" />
                </div>
                <h3 className="text-base font-bold text-white font-sans tracking-wide">
                  Mission-Level Financial Ledger
                </h3>
              </div>
              <p className="text-xs text-slate-400 font-sans">
                Inspect granular model invocation records, input/output token counts, and micro-dollar charges per mission.
              </p>
            </div>

            {missions.length > 0 && (
              <div className="flex items-center space-x-2">
                <label htmlFor="mission-select" className="text-xs text-slate-400 sr-only">
                  Select Mission
                </label>
                <select
                  id="mission-select"
                  value={selectedMissionId}
                  onChange={(e) => handleMissionChange(e.target.value)}
                  className="liquid-control rounded-xl border border-white/[0.1] bg-slate-950/80 px-4 py-2.5 text-xs text-cyan-200 font-mono focus:border-cyan-400 focus:outline-none"
                >
                  {missions.map((m) => (
                    <option key={m.id} value={m.id} className="bg-slate-950 text-slate-200">
                      {m.id.slice(0, 8)}... — {m.title || m.objective.slice(0, 32)}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {usageLoading ? (
            <div className="p-12 text-center text-xs text-slate-400 font-mono tracking-wider">
              <span className="inline-block animate-spin mr-2 text-cyan-400">◓</span>
              SYNCHRONIZING FINANCIAL LEDGER RECORDS...
            </div>
          ) : !missionUsage || missionUsage.records.length === 0 ? (
            <div className="p-12 text-center text-xs text-slate-400 font-mono tracking-wider">
              NO TOKEN USAGE RECORDS FOUND FOR THE SELECTED MISSION.
            </div>
          ) : (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="liquid-glass-card rounded-xl p-4 border border-white/[0.08]">
                  <span className="text-[10px] text-slate-400 uppercase tracking-widest font-mono font-bold block">
                    Selected Mission Tokens
                  </span>
                  <p className="font-mono text-2xl font-bold text-white mt-1.5">
                    {missionUsage.total_tokens.toLocaleString()}
                  </p>
                </div>
                <div className="liquid-glass-card rounded-xl p-4 border border-white/[0.08]">
                  <span className="text-[10px] text-slate-400 uppercase tracking-widest font-mono font-bold block">
                    Selected Mission Cost (USD)
                  </span>
                  <p className="font-mono text-2xl font-bold text-emerald-300 mt-1.5 drop-shadow-[0_0_8px_rgba(0,255,157,0.3)]">
                    ${Number(missionUsage.total_cost_usd).toFixed(4)}
                  </p>
                </div>
              </div>

              <div className="overflow-x-auto rounded-xl border border-white/[0.08]">
                <table className="w-full text-left font-mono text-xs">
                  <thead className="bg-slate-950/90 text-cyan-400/90 border-b border-white/[0.08] uppercase text-[10px] tracking-wider font-bold">
                    <tr>
                      <th className="py-3 px-4">Model Engine</th>
                      <th className="py-3 px-4">Input Tokens</th>
                      <th className="py-3 px-4">Output Tokens</th>
                      <th className="py-3 px-4">Total Tokens</th>
                      <th className="py-3 px-4">Incurred Cost (USD)</th>
                      <th className="py-3 px-4">Timestamp (UTC)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04]">
                    {missionUsage.records.map((rec) => (
                      <tr key={rec.id} className="hover:bg-cyan-500/[0.04] transition-colors">
                        <td className="py-3 px-4 text-white font-bold">{rec.model_name}</td>
                        <td className="py-3 px-4 text-slate-300">{rec.input_tokens.toLocaleString()}</td>
                        <td className="py-3 px-4 text-slate-300">{rec.output_tokens.toLocaleString()}</td>
                        <td className="py-3 px-4 text-cyan-200 font-bold">{rec.total_tokens.toLocaleString()}</td>
                        <td className="py-3 px-4 text-emerald-300 font-bold">${Number(rec.cost_usd).toFixed(4)}</td>
                        <td className="py-3 px-4 text-slate-400 text-[11px]">
                          {new Date(rec.created_at).toLocaleTimeString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
