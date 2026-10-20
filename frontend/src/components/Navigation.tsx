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
  badge?: number | string;
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
      className={`relative flex flex-col border-r border-slate-800 bg-slate-950 text-slate-300 transition-all duration-200 select-none ${
        isCollapsed ? 'w-16' : 'w-64'
      }`}
      aria-label="Main Navigation"
    >
      {/* Brand Header */}
      <div className="flex h-16 items-center justify-between px-4 border-b border-slate-800/80">
        <div className="flex items-center space-x-3 overflow-hidden">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-md shadow-indigo-500/20">
            <ShieldCheck className="h-5 w-5" />
          </div>
          {!isCollapsed && (
            <div className="truncate">
              <span className="font-semibold text-slate-100 tracking-tight">SYNTRA</span>
              <span className="ml-1.5 text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-950 text-indigo-400 border border-indigo-800/60">
                P14
              </span>
            </div>
          )}
        </div>
        <button
          onClick={onToggleCollapse}
          className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 space-y-1 overflow-y-auto p-2 scrollbar-thin scrollbar-thumb-slate-800">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeRoute === item.id;
          const hasBadge = item.id === 'approvals' && pendingApprovalsCount > 0;

          return (
            <button
              key={item.id}
              data-testid={`nav-${item.id}`}
              onClick={() => onRouteChange(item.id)}
              className={`group flex w-full items-center rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
              }`}
              title={isCollapsed ? item.label : undefined}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon
                className={`h-4 w-4 flex-shrink-0 ${
                  isActive ? 'text-indigo-400' : 'text-slate-400 group-hover:text-slate-200'
                }`}
              />
              {!isCollapsed && (
                <span className="ml-3 flex-1 text-left truncate">{item.label}</span>
              )}
              {hasBadge && (
                <span
                  className={`inline-flex items-center justify-center rounded-full bg-amber-500 text-[10px] font-bold text-slate-950 ${
                    isCollapsed ? 'absolute top-1 right-1 h-2 w-2 p-0' : 'ml-auto px-1.5 py-0.2'
                  }`}
                >
                  {!isCollapsed && pendingApprovalsCount}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer info */}
      <div className="border-t border-slate-800/80 p-3 text-[11px] text-slate-500">
        {!isCollapsed ? (
          <div className="truncate">
            <p className="font-medium text-slate-400">Autonomous Engineering</p>
            <p className="font-mono text-[10px] text-slate-600">Contract & Evidence Governed</p>
          </div>
        ) : (
          <div className="text-center font-mono text-[9px] text-slate-600">ORG</div>
        )}
      </div>
    </aside>
  );
};
