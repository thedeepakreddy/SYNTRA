import React from 'react';
import {
  LayoutDashboard,
  FolderGit2,
  Target,
  Users,
  CheckSquare,
  Cpu,
  Coins,
  Terminal,
  FileCode2,
  Gauge,
  History,
  Activity,
  Settings,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react';

export interface NavItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

export const NAV_ITEMS: NavItem[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'projects', label: 'Projects', icon: FolderGit2 },
  { id: 'missions', label: 'Missions & Tasks', icon: Target },
  { id: 'agents', label: 'Agents & Teams', icon: Users },
  { id: 'approvals', label: 'Approvals', icon: CheckSquare },
  { id: 'model-routing', label: 'Model Routing', icon: Cpu },
  { id: 'usage-budgets', label: 'Usage & Budgets', icon: Coins },
  { id: 'runs-logs', label: 'Runs & Logs', icon: Terminal },
  { id: 'artifacts', label: 'Artifacts & Results', icon: FileCode2 },
  { id: 'benchmarks', label: 'Benchmarks & Quality', icon: Gauge },
  { id: 'audit-history', label: 'Audit History', icon: History },
  { id: 'system-health', label: 'System Health', icon: Activity },
  { id: 'settings', label: 'Settings & Config', icon: Settings },
];

interface NavigationProps {
  activeRoute: string;
  onRouteChange: (route: string) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  pendingApprovalsCount?: number;
}

export const Navigation: React.FC<NavigationProps> = ({
  activeRoute,
  onRouteChange,
  isCollapsed,
  onToggleCollapse,
  pendingApprovalsCount = 0,
}) => {
  return (
    <aside
      className={`relative z-30 flex flex-col border-r border-cyan-500/15 bg-gradient-to-b from-[#060D1E]/95 via-[#030712]/95 to-[#010308]/98 backdrop-blur-2xl transition-all duration-300 ease-spring shadow-[0_0_50px_rgba(0,0,0,0.9),inset_-1px_0_1px_rgba(0,240,255,0.08)] ${
        isCollapsed ? 'w-18' : 'w-64'
      }`}
    >
      {/* Brand Header with Liquid Specular Glass Glow */}
      <div className="flex h-16 items-center justify-between px-4 border-b border-white/[0.08] relative">
        <div className="flex items-center space-x-3 overflow-hidden">
          {/* Holographic Logo Shield */}
          <div className="relative flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400/20 via-slate-900 to-emerald-400/10 border border-cyan-400/40 shadow-[0_0_20px_rgba(0,240,255,0.35),inset_0_1px_1px_rgba(255,255,255,0.4)]">
            <ShieldCheck className="h-5 w-5 text-cyan-400" />
            <span className="absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#00FF9D]" />
          </div>

          {!isCollapsed && (
            <div className="flex flex-col">
              <div className="flex items-center space-x-1.5">
                <span className="font-bold tracking-tight text-white font-sans text-sm drop-shadow-[0_0_12px_rgba(0,240,255,0.4)]">
                  SYNTRA
                </span>
                <span className="rounded-md bg-cyan-950/80 px-1.5 py-0.2 text-[9px] font-mono font-bold text-cyan-300 border border-cyan-500/30">
                  v1.4
                </span>
              </div>
              <p className="text-[10px] text-cyan-400/70 font-mono tracking-wider uppercase font-semibold">
                NEURAL ORG
              </p>
            </div>
          )}
        </div>

        <button
          onClick={onToggleCollapse}
          className="rounded-lg p-1.5 text-slate-400 hover:bg-cyan-500/10 hover:text-cyan-300 transition-colors duration-150 active:scale-[0.96] border border-transparent hover:border-cyan-500/20"
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-3 scrollbar-thin scrollbar-thumb-cyan-500/20">
        {!isCollapsed && (
          <div className="px-3 pt-1 pb-2 flex items-center justify-between">
            <span className="text-[10px] font-mono tracking-[0.2em] uppercase font-bold text-slate-500">
              TACTICAL HUBS
            </span>
            <span className="h-1 w-1 rounded-full bg-cyan-400 animate-ping" />
          </div>
        )}

        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeRoute === item.id;
          const hasBadge = item.id === 'approvals' && pendingApprovalsCount > 0;

          return (
            <button
              key={item.id}
              data-testid={`nav-${item.id}`}
              onClick={() => onRouteChange(item.id)}
              className={`group relative flex w-full items-center rounded-xl px-3 py-2.5 text-xs font-medium transition-all duration-200 active:scale-[0.98] ${
                isActive
                  ? 'bg-gradient-to-r from-cyan-500/20 via-cyan-500/10 to-transparent text-white font-semibold border border-cyan-400/40 shadow-[inset_0_1px_1px_rgba(255,255,255,0.35),0_0_20px_rgba(0,240,255,0.2)]'
                  : 'text-slate-400 hover:bg-white/[0.05] hover:text-slate-200 border border-transparent hover:border-white/[0.06]'
              }`}
              title={isCollapsed ? item.label : undefined}
              aria-current={isActive ? 'page' : undefined}
            >
              {/* Active Laser Photon Pip */}
              {isActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 rounded-r bg-cyan-400 shadow-[0_0_12px_#00F0FF]" />
              )}

              <Icon
                className={`h-4 w-4 flex-shrink-0 transition-transform duration-200 group-hover:scale-110 ${
                  isActive ? 'text-cyan-300 drop-shadow-[0_0_8px_rgba(0,240,255,0.8)]' : 'text-slate-400 group-hover:text-cyan-300'
                }`}
              />

              {!isCollapsed && (
                <span className="ml-3 flex-1 text-left truncate tracking-tight font-sans">{item.label}</span>
              )}

              {hasBadge && (
                <span
                  className={`inline-flex items-center justify-center rounded-full bg-amber-400 text-[10px] font-mono font-bold text-slate-950 shadow-[0_0_12px_rgba(255,184,0,0.8)] ${
                    isCollapsed ? 'absolute top-1.5 right-1.5 h-2.5 w-2.5 p-0' : 'ml-auto px-2 py-0.5'
                  }`}
                >
                  {!isCollapsed && pendingApprovalsCount}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer System Status Box */}
      <div className="border-t border-white/[0.08] p-3">
        {!isCollapsed ? (
          <div className="rounded-xl border border-cyan-500/20 bg-slate-950/80 p-2.5 text-[11px] shadow-[inset_0_1px_1px_rgba(255,255,255,0.06)]">
            <div className="flex items-center justify-between">
              <span className="flex items-center space-x-1.5 text-emerald-400 font-mono text-[10px]">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_#00FF9D]" />
                <span className="font-semibold uppercase tracking-wider">ALL NODES ONLINE</span>
              </span>
              <span className="text-[10px] text-cyan-400 font-mono">HERMETIC</span>
            </div>
            <div className="mt-1.5 text-[10px] text-slate-400 font-mono flex items-center justify-between pt-1 border-t border-white/[0.04]">
              <span>TIER-1 SECURITY</span>
              <span className="text-emerald-400 font-bold">PASS</span>
            </div>
          </div>
        ) : (
          <div className="flex justify-center py-1">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#00FF9D]" title="All systems normal" />
          </div>
        )}
      </div>
    </aside>
  );
};
