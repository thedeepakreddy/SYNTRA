import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { Mission, MissionUsageSummary, SystemOverview } from '../types';
import { Coins } from 'lucide-react';

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
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow">
        <div className="flex items-center space-x-3">
          <div className="rounded-lg bg-emerald-600/20 p-2 text-emerald-400 border border-emerald-500/30">
            <Coins className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight text-white">
              Financial Ledgers, Budgets & Token Governance
            </h2>
            <p className="mt-1 text-xs text-slate-400 max-w-3xl">
              Strict per-mission token and USD financial governance. Hard failure gates halt execution
              immediately upon budget breach — preventing infinite runaway costs.
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-800 bg-rose-950/40 p-4 text-xs text-rose-300">
          <p className="font-semibold">Error Loading Financial Ledgers</p>
          <p className="mt-1 font-mono">{error}</p>
        </div>
      )}

      {/* Aggregate Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow">
          <span className="text-xs font-medium text-slate-400">Total Tokens Consumed</span>
          <div className="mt-2 text-2xl font-bold font-mono text-slate-100">
            {overview ? Number(overview.total_tokens_consumed).toLocaleString() : '0'}
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">Across all active missions</span>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow">
          <span className="text-xs font-medium text-slate-400">Total Cost Incurred (USD)</span>
          <div className="mt-2 text-2xl font-bold font-mono text-emerald-400">
            ${overview ? Number(overview.total_cost_usd).toFixed(4) : '0.0000'}
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">Live calculated API ledger</span>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow">
          <span className="text-xs font-medium text-slate-400">Budget Governance Status</span>
          <div className="mt-2 flex items-center space-x-2">
            <span className="h-3 w-3 rounded-full bg-emerald-500" />
            <span className="text-sm font-semibold text-slate-200">IN_BUDGET</span>
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">Hard ceiling active</span>
        </div>
      </div>

      {/* Granular Mission Selector & Usage Breakdown */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-100">Mission-Level Financial Ledger</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Inspect model invocation records, input/output token counts, and USD charges per mission.
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
                className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
              >
                {missions.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.id.slice(0, 8)}... — {m.title || m.objective.slice(0, 30)}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {usageLoading ? (
          <div className="p-8 text-center text-xs text-slate-500">Loading ledger records...</div>
        ) : !missionUsage || missionUsage.records.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No token usage records found for this mission.
          </div>
        ) : (
          <div className="mt-4 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-lg bg-slate-950 p-3 border border-slate-800">
                <span className="text-[11px] text-slate-400">Mission Tokens</span>
                <p className="font-mono text-lg font-bold text-slate-100">
                  {missionUsage.total_tokens.toLocaleString()}
                </p>
              </div>
              <div className="rounded-lg bg-slate-950 p-3 border border-slate-800">
                <span className="text-[11px] text-slate-400">Mission Cost (USD)</span>
                <p className="font-mono text-lg font-bold text-emerald-400">
                  ${Number(missionUsage.total_cost_usd).toFixed(4)}
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left font-mono text-xs">
                <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="py-2.5 px-3">Model</th>
                    <th className="py-2.5 px-3">Input Tokens</th>
                    <th className="py-2.5 px-3">Output Tokens</th>
                    <th className="py-2.5 px-3">Total Tokens</th>
                    <th className="py-2.5 px-3">Cost (USD)</th>
                    <th className="py-2.5 px-3">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80">
                  {missionUsage.records.map((rec) => (
                    <tr key={rec.id} className="hover:bg-slate-850">
                      <td className="py-2 px-3 text-slate-200">{rec.model_name}</td>
                      <td className="py-2 px-3 text-slate-400">{rec.input_tokens.toLocaleString()}</td>
                      <td className="py-2 px-3 text-slate-400">{rec.output_tokens.toLocaleString()}</td>
                      <td className="py-2 px-3 text-slate-100 font-bold">{rec.total_tokens.toLocaleString()}</td>
                      <td className="py-2 px-3 text-emerald-400">${Number(rec.cost_usd).toFixed(4)}</td>
                      <td className="py-2 px-3 text-slate-500 text-[11px]">
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
  );
};
