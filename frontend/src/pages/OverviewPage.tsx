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
  Cpu,
  Zap,
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
      {/* Top Hero Banner - Double-Bezel Hardware Enclosure with HUD Brackets */}
      <div className="double-bezel-outer hud-corner relative overflow-hidden">
        {/* Optical Prismatic Ambient Orbs */}
        <div className="absolute top-0 right-10 -mt-16 w-96 h-96 rounded-full bg-cyan-500/15 blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-1/4 -mb-20 w-80 h-80 rounded-full bg-emerald-500/10 blur-3xl pointer-events-none" />
        
        {/* Subtle Specular Top Rim */}
        <div className="absolute top-0 left-1/4 right-1/4 h-[1px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-80" />
        
        <div className="double-bezel-inner p-6 md:p-8 backdrop-blur-2xl">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-3">
              <div className="flex items-center space-x-2.5">
                <span className="eyebrow-pill">
                  <Zap className="h-3 w-3 text-cyan-400" />
                  <span>AUTONOMOUS ENGINEERING PLANE</span>
                </span>
                <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-emerald-950/60 border border-emerald-400/30 text-[10px] font-mono text-emerald-300 shadow-[0_0_10px_rgba(0,255,157,0.2)]">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_#00FF9D]" />
                  <span className="font-bold tracking-wider">TIER-1 VERIFIED</span>
                </span>
              </div>
              <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white font-sans drop-shadow-[0_2px_14px_rgba(0,240,255,0.25)]">
                SYNTRA Autonomous Engineering Organization
              </h2>
              <p className="text-xs md:text-sm text-slate-300 max-w-2xl leading-relaxed font-sans">
                Evidence-driven, contract-governed multi-agent engineering team operating under strict
                separation of powers, deterministic verification, and cryptographic delivery gates.
              </p>
            </div>

            {/* Nested Island Liquid Glass CTA Button */}
            <div className="flex items-center space-x-3 flex-shrink-0">
              <button
                onClick={() => onNavigate('missions')}
                className="btn-island-primary group"
              >
                <span>Launch Missions</span>
                <span className="btn-island-icon">
                  <ArrowRight className="h-3.5 w-3.5 stroke-[2.5]" />
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-2xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 backdrop-blur-md shadow-layered-sm">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="h-4 w-4 text-rose-400 flex-shrink-0" />
            <p className="font-semibold font-sans">Unable to fetch live system overview</p>
          </div>
          <p className="mt-1 font-mono text-[11px] text-rose-400/80">{error}</p>
        </div>
      )}

      {/* KPI Cards Grid - Apple Liquid Glass Tiles with Specular Glare */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Projects */}
        <div className="liquid-glass-card rounded-2xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono tracking-wider uppercase text-cyan-400 font-semibold">
              Total Projects
            </span>
            <div className="p-2 rounded-xl bg-cyan-950/50 text-cyan-300 border border-cyan-500/30 shadow-[0_0_12px_rgba(0,240,255,0.2)]">
              <FolderGit2 className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span className="text-3xl font-extrabold text-white font-mono tabular-nums tracking-tight drop-shadow-[0_0_10px_rgba(255,255,255,0.2)]">
              {loading ? '...' : overview?.projects_count ?? 0}
            </span>
            <button
              onClick={() => onNavigate('projects')}
              className="text-xs font-semibold text-cyan-400 hover:text-cyan-200 inline-flex items-center transition-colors font-mono uppercase"
            >
              Manage <ArrowRight className="h-3 w-3 ml-0.5" />
            </button>
          </div>
        </div>

        {/* Active Missions */}
        <div className="liquid-glass-card rounded-2xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono tracking-wider uppercase text-cyan-400 font-semibold">
              Active Missions
            </span>
            <div className="p-2 rounded-xl bg-cyan-950/50 text-cyan-300 border border-cyan-500/30 shadow-[0_0_12px_rgba(0,240,255,0.2)]">
              <Target className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span className="text-3xl font-extrabold text-white font-mono tabular-nums tracking-tight drop-shadow-[0_0_10px_rgba(255,255,255,0.2)]">
              {loading ? '...' : overview?.missions_count ?? 0}
            </span>
            <button
              onClick={() => onNavigate('missions')}
              className="text-xs font-semibold text-cyan-400 hover:text-cyan-200 inline-flex items-center transition-colors font-mono uppercase"
            >
              Inspect <ArrowRight className="h-3 w-3 ml-0.5" />
            </button>
          </div>
        </div>

        {/* Pending Approvals */}
        <div className="liquid-glass-card rounded-2xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono tracking-wider uppercase text-amber-400 font-semibold">
              Pending Approvals
            </span>
            <div className="p-2 rounded-xl bg-amber-950/50 text-amber-300 border border-amber-500/30 shadow-[0_0_12px_rgba(255,184,0,0.2)]">
              <CheckSquare className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span
              className={`text-3xl font-extrabold font-mono tabular-nums tracking-tight ${
                (overview?.pending_approvals_count ?? 0) > 0 ? 'text-amber-400 drop-shadow-[0_0_12px_rgba(255,184,0,0.4)]' : 'text-white'
              }`}
            >
              {loading ? '...' : overview?.pending_approvals_count ?? 0}
            </span>
            <button
              onClick={() => onNavigate('approvals')}
              className="text-xs font-semibold text-amber-400 hover:text-amber-200 inline-flex items-center transition-colors font-mono uppercase"
            >
              Review Gate <ArrowRight className="h-3 w-3 ml-0.5" />
            </button>
          </div>
        </div>

        {/* Engineering Personas */}
        <div className="liquid-glass-card rounded-2xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono tracking-wider uppercase text-emerald-400 font-semibold">
              Engineering Personas
            </span>
            <div className="p-2 rounded-xl bg-emerald-950/50 text-emerald-300 border border-emerald-500/30 shadow-[0_0_12px_rgba(0,255,157,0.2)]">
              <Users className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span className="text-3xl font-extrabold text-white font-mono tabular-nums tracking-tight drop-shadow-[0_0_10px_rgba(255,255,255,0.2)]">
              {loading ? '...' : overview?.active_agents_count ?? 10}
            </span>
            <button
              onClick={() => onNavigate('agents')}
              className="text-xs font-semibold text-emerald-400 hover:text-emerald-200 inline-flex items-center transition-colors font-mono uppercase"
            >
              Team Specs <ArrowRight className="h-3 w-3 ml-0.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Financial & Health Subgrid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Token & Financial Consumption */}
        <div className="liquid-glass-card rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 rounded-xl bg-cyan-950/60 text-cyan-300 border border-cyan-500/30">
                <Coins className="h-4 w-4" />
              </div>
              <h3 className="text-sm font-bold text-white tracking-tight font-sans">
                Financial Ledger & Token Meter
              </h3>
            </div>
            <button
              onClick={() => onNavigate('usage-budgets')}
              className="text-xs font-semibold text-cyan-400 hover:text-cyan-200 transition-colors font-mono"
            >
              View Ledgers →
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3.5">
            <div className="rounded-xl bg-slate-950/70 border border-white/[0.08] p-4 shadow-[inset_0_1px_1px_rgba(255,255,255,0.06)]">
              <p className="text-[10px] font-mono tracking-wider uppercase text-slate-400">Total Tokens Consumed</p>
              <p className="mt-1 font-mono text-xl font-extrabold text-white tabular-nums drop-shadow-[0_0_8px_rgba(255,255,255,0.2)]">
                {loading ? '...' : Number(overview?.total_tokens_consumed ?? 0).toLocaleString()}
              </p>
              <span className="text-[10px] text-slate-500 mt-1 block font-mono">Live API telemetry sink</span>
            </div>
            <div className="rounded-xl bg-slate-950/70 border border-white/[0.08] p-4 shadow-[inset_0_1px_1px_rgba(255,255,255,0.06)]">
              <p className="text-[10px] font-mono tracking-wider uppercase text-slate-400">Total Cost (USD)</p>
              <p className="mt-1 font-mono text-xl font-extrabold text-emerald-400 tabular-nums drop-shadow-[0_0_8px_rgba(0,255,157,0.3)]">
                ${loading ? '...' : Number(overview?.total_cost_usd ?? 0).toFixed(4)}
              </p>
              <span className="text-[10px] text-emerald-400/80 mt-1 block font-mono">Zero paid API leaks</span>
            </div>
          </div>
        </div>

        {/* System Health */}
        <div className="liquid-glass-card rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 rounded-xl bg-emerald-950/60 text-emerald-400 border border-emerald-500/30">
                <Activity className="h-4 w-4" />
              </div>
              <h3 className="text-sm font-bold text-white tracking-tight font-sans">
                System Health & Tenancy
              </h3>
            </div>
            <button
              onClick={() => onNavigate('system-health')}
              className="text-xs font-semibold text-emerald-400 hover:text-emerald-200 transition-colors font-mono"
            >
              Diagnostic Probe →
            </button>
          </div>

          <div className="flex items-center justify-between p-4 rounded-xl bg-slate-950/70 border border-white/[0.08] shadow-[inset_0_1px_1px_rgba(255,255,255,0.06)]">
            <div>
              <p className="text-[10px] font-mono tracking-wider uppercase text-slate-400">Health Status</p>
              <div className="mt-1.5">
                <StatusBadge status={overview?.system_health || 'HEALTHY'} />
              </div>
            </div>
            <div className="text-right">
              <p className="text-[10px] font-mono tracking-wider uppercase text-slate-400">Active Tenant</p>
              <p className="mt-1 font-mono text-xs text-cyan-300 font-bold truncate max-w-[160px]">
                {overview?.active_tenant_id ? overview.active_tenant_id.slice(0, 13) + '...' : 'Default Org'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Subsystem Matrix - Liquid Glass Interactive Grid */}
      <div className="liquid-glass-card rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-white/[0.08]">
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight font-sans">
              Autonomous Engineering Subsystems
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5 font-sans">Direct access to operational control planes</p>
          </div>
          <span className="text-[10px] font-mono text-cyan-400 font-semibold bg-cyan-950/50 px-2 py-0.5 rounded-md border border-cyan-500/30">
            4 GATED MODULES
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          <button
            onClick={() => onNavigate('model-routing')}
            className="group flex items-start space-x-3.5 p-4 rounded-xl border border-white/[0.08] bg-slate-950/60 hover:bg-slate-900/80 hover:border-cyan-400/40 transition-all duration-200 text-left active:scale-[0.98] shadow-[inset_0_1px_1px_rgba(255,255,255,0.06)]"
          >
            <div className="p-2.5 rounded-xl bg-cyan-950/60 text-cyan-300 border border-cyan-500/30 group-hover:scale-105 group-hover:shadow-[0_0_12px_rgba(0,240,255,0.4)] transition-all duration-200">
              <Cpu className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs font-bold text-white group-hover:text-cyan-300 transition-colors font-sans">
                Model Routing
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5 font-sans">Tiered routing & simulator</p>
            </div>
          </button>

          <button
            onClick={() => onNavigate('benchmarks')}
            className="group flex items-start space-x-3.5 p-4 rounded-xl border border-white/[0.08] bg-slate-950/60 hover:bg-slate-900/80 hover:border-emerald-400/40 transition-all duration-200 text-left active:scale-[0.98] shadow-[inset_0_1px_1px_rgba(255,255,255,0.06)]"
          >
            <div className="p-2.5 rounded-xl bg-emerald-950/60 text-emerald-300 border border-emerald-500/30 group-hover:scale-105 group-hover:shadow-[0_0_12px_rgba(0,255,157,0.4)] transition-all duration-200">
              <Activity className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs font-bold text-white group-hover:text-emerald-300 transition-colors font-sans">
                Benchmarks & Quality
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5 font-sans">6-metric evaluation suite</p>
            </div>
          </button>

          <button
            onClick={() => onNavigate('audit-history')}
            className="group flex items-start space-x-3.5 p-4 rounded-xl border border-white/[0.08] bg-slate-950/60 hover:bg-slate-900/80 hover:border-amber-400/40 transition-all duration-200 text-left active:scale-[0.98] shadow-[inset_0_1px_1px_rgba(255,255,255,0.06)]"
          >
            <div className="p-2.5 rounded-xl bg-amber-950/60 text-amber-300 border border-amber-500/30 group-hover:scale-105 group-hover:shadow-[0_0_12px_rgba(255,184,0,0.4)] transition-all duration-200">
              <ShieldAlert className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs font-bold text-white group-hover:text-amber-300 transition-colors font-sans">
                Audit History
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5 font-sans">Tamper-evident logs</p>
            </div>
          </button>

          <button
            onClick={() => onNavigate('artifacts')}
            className="group flex items-start space-x-3.5 p-4 rounded-xl border border-white/[0.08] bg-slate-950/60 hover:bg-slate-900/80 hover:border-cyan-400/40 transition-all duration-200 text-left active:scale-[0.98] shadow-[inset_0_1px_1px_rgba(255,255,255,0.06)]"
          >
            <div className="p-2.5 rounded-xl bg-cyan-950/60 text-cyan-300 border border-cyan-500/30 group-hover:scale-105 group-hover:shadow-[0_0_12px_rgba(0,240,255,0.4)] transition-all duration-200">
              <FolderGit2 className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs font-bold text-white group-hover:text-cyan-300 transition-colors font-sans">
                Artifacts & Diffs
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5 font-sans">SHA-256 hashed outputs</p>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
};
