import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { SystemOverview } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import {
  FolderGit2,
  Target,
  CheckSquare,
  Users,
  Coins,
  Activity,
  ArrowRight,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';

interface OverviewPageProps {
  onNavigate: (route: string) => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ onNavigate }) => {
  const [overview, setOverview] = useState<SystemOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getSystemOverview();
      setOverview(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load system overview.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="rounded-xl border border-indigo-900/60 bg-gradient-to-r from-indigo-950/40 via-slate-900 to-slate-900 p-6 shadow-lg">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <Sparkles className="h-5 w-5 text-indigo-400" />
              <h2 className="text-xl font-bold tracking-tight text-white">
                SYNTRA Autonomous Engineering Organization
              </h2>
            </div>
            <p className="mt-1 text-sm text-slate-400 max-w-2xl">
              Evidence-driven, contract-governed autonomous software engineering team operating under
              strict separation of powers and cryptographic verification gates.
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => onNavigate('missions')}
              className="inline-flex items-center space-x-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-400"
            >
              <span>View Missions</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-800 bg-rose-950/40 p-4 text-sm text-rose-300">
          <p className="font-semibold">Unable to fetch live system overview</p>
          <p className="mt-1 font-mono text-xs">{error}</p>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Active Projects */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total Projects</span>
            <FolderGit2 className="h-4 w-4 text-slate-500" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-slate-100 font-mono">
              {loading ? '...' : overview?.projects_count ?? 0}
            </span>
            <button
              onClick={() => onNavigate('projects')}
              className="text-xs text-indigo-400 hover:text-indigo-300 inline-flex items-center"
            >
              Manage <ArrowRight className="h-3 w-3 ml-0.5" />
            </button>
          </div>
        </div>

        {/* Missions */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Active Missions</span>
            <Target className="h-4 w-4 text-slate-500" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-slate-100 font-mono">
              {loading ? '...' : overview?.missions_count ?? 0}
            </span>
            <button
              onClick={() => onNavigate('missions')}
              className="text-xs text-indigo-400 hover:text-indigo-300 inline-flex items-center"
            >
              Inspect <ArrowRight className="h-3 w-3 ml-0.5" />
            </button>
          </div>
        </div>

        {/* Pending Approvals */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Pending Approvals</span>
            <CheckSquare className="h-4 w-4 text-amber-500" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span
              className={`text-2xl font-bold font-mono ${
                (overview?.pending_approvals_count ?? 0) > 0 ? 'text-amber-400' : 'text-slate-100'
              }`}
            >
              {loading ? '...' : overview?.pending_approvals_count ?? 0}
            </span>
            <button
              onClick={() => onNavigate('approvals')}
              className="text-xs text-amber-400 hover:text-amber-300 inline-flex items-center"
            >
              Review Gate <ArrowRight className="h-3 w-3 ml-0.5" />
            </button>
          </div>
        </div>

        {/* Engineering Personas */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Engineering Personas</span>
            <Users className="h-4 w-4 text-slate-500" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-slate-100 font-mono">
              {loading ? '...' : overview?.active_agents_count ?? 10}
            </span>
            <button
              onClick={() => onNavigate('agents')}
              className="text-xs text-indigo-400 hover:text-indigo-300 inline-flex items-center"
            >
              Team Specs <ArrowRight className="h-3 w-3 ml-0.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Financial & Health Subgrid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Token & Financial Consumption */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center space-x-2">
              <Coins className="h-4 w-4 text-indigo-400" />
              <h3 className="text-sm font-semibold text-slate-200">Financial Ledger & Tokens</h3>
            </div>
            <button
              onClick={() => onNavigate('usage-budgets')}
              className="text-xs text-indigo-400 hover:text-indigo-300"
            >
              View Ledgers
            </button>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-slate-400">Total Tokens Consumed</p>
              <p className="mt-1 font-mono text-xl font-bold text-slate-100">
                {loading ? '...' : Number(overview?.total_tokens_consumed ?? 0).toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-400">Total Cost (USD)</p>
              <p className="mt-1 font-mono text-xl font-bold text-emerald-400">
                ${loading ? '...' : Number(overview?.total_cost_usd ?? 0).toFixed(4)}
              </p>
            </div>
          </div>
        </div>

        {/* System Health */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center space-x-2">
              <Activity className="h-4 w-4 text-emerald-400" />
              <h3 className="text-sm font-semibold text-slate-200">System Health & Tenancy</h3>
            </div>
            <button
              onClick={() => onNavigate('system-health')}
              className="text-xs text-indigo-400 hover:text-indigo-300"
            >
              Diagnostic Details
            </button>
          </div>
          <div className="mt-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400">Health Status</p>
              <div className="mt-1">
                <StatusBadge status={overview?.system_health || 'HEALTHY'} />
              </div>
            </div>
            <div>
              <p className="text-xs text-slate-400 text-right">Active Tenant</p>
              <p className="mt-1 font-mono text-xs text-slate-300 text-right">
                {overview?.active_tenant_id ? overview.active_tenant_id.slice(0, 13) + '...' : 'Default Org'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Access Matrix */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
        <h3 className="text-sm font-semibold text-slate-200 mb-4">Autonomous Engineering Subsystems</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <button
            onClick={() => onNavigate('model-routing')}
            className="flex items-start space-x-3 p-3 rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-850 hover:border-indigo-500/50 transition-colors text-left"
          >
            <div className="p-2 rounded bg-indigo-950 text-indigo-400 border border-indigo-800/40">
              <Coins className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-200">Model Routing</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Tiered models & simulation</p>
            </div>
          </button>

          <button
            onClick={() => onNavigate('benchmarks')}
            className="flex items-start space-x-3 p-3 rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-850 hover:border-indigo-500/50 transition-colors text-left"
          >
            <div className="p-2 rounded bg-indigo-950 text-indigo-400 border border-indigo-800/40">
              <Activity className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-200">Benchmarks & Quality</p>
              <p className="text-[11px] text-slate-400 mt-0.5">6-metric evaluation suite</p>
            </div>
          </button>

          <button
            onClick={() => onNavigate('audit-history')}
            className="flex items-start space-x-3 p-3 rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-850 hover:border-indigo-500/50 transition-colors text-left"
          >
            <div className="p-2 rounded bg-indigo-950 text-indigo-400 border border-indigo-800/40">
              <ShieldAlert className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-200">Audit History</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Tamper-evident logs</p>
            </div>
          </button>

          <button
            onClick={() => onNavigate('artifacts')}
            className="flex items-start space-x-3 p-3 rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-850 hover:border-indigo-500/50 transition-colors text-left"
          >
            <div className="p-2 rounded bg-indigo-950 text-indigo-400 border border-indigo-800/40">
              <FolderGit2 className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-200">Artifacts & Diffs</p>
              <p className="text-[11px] text-slate-400 mt-0.5">SHA-256 hashed outputs</p>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
};
