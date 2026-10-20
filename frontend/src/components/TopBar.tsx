import React from 'react';
import { MembershipRole, SystemOverview, UserContext } from '../types';
import { StatusBadge } from './StatusBadge';
import { RefreshCw, Shield, User, Building2 } from 'lucide-react';

interface TopBarProps {
  currentRouteTitle: string;
  overview: SystemOverview | null;
  userContext: UserContext;
  onRoleChange: (newRole: MembershipRole) => void;
  onRefresh: () => void;
  isRefreshing?: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({
  currentRouteTitle,
  overview,
  userContext,
  onRoleChange,
  onRefresh,
  isRefreshing = false,
}) => {
  return (
    <header className="flex h-16 w-full items-center justify-between border-b border-slate-800 bg-slate-950/80 px-6 backdrop-blur-sm">
      {/* Route Title & Breadcrumbs */}
      <div className="flex items-center space-x-3">
        <h1 className="text-lg font-semibold tracking-tight text-slate-100">
          {currentRouteTitle}
        </h1>
        {overview && (
          <span className="hidden sm:inline-flex">
            <StatusBadge status={overview.system_health} />
          </span>
        )}
      </div>

      {/* Right Controls: Org, Role Switcher, Refresh */}
      <div className="flex items-center space-x-4">
        {/* Environment Badge */}
        <div className="hidden md:flex items-center space-x-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-xs font-mono text-slate-400">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>{overview?.environment?.toUpperCase() || 'DEVELOPMENT'}</span>
        </div>

        {/* Tenant/Org Badge */}
        <div className="hidden lg:flex items-center space-x-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-xs font-mono text-slate-300" title={`Org ID: ${userContext.orgId}`}>
          <Building2 className="h-3.5 w-3.5 text-slate-400" />
          <span className="truncate max-w-[120px]">{userContext.orgId.slice(0, 8)}...</span>
        </div>

        {/* Role Switcher */}
        <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 rounded-md px-2 py-1">
          <Shield className="h-3.5 w-3.5 text-indigo-400" />
          <label htmlFor="role-select" className="text-xs text-slate-400 sr-only">
            Role
          </label>
          <select
            id="role-select"
            value={userContext.role}
            onChange={(e) => onRoleChange(e.target.value as MembershipRole)}
            className="bg-transparent text-xs font-medium text-slate-200 focus:outline-none cursor-pointer"
            aria-label="Switch User Role"
          >
            <option value="admin" className="bg-slate-900 text-slate-200">
              Admin
            </option>
            <option value="developer" className="bg-slate-900 text-slate-200">
              Developer
            </option>
            <option value="viewer" className="bg-slate-900 text-slate-200">
              Viewer
            </option>
          </select>
        </div>

        {/* User Badge */}
        <div className="flex items-center space-x-1.5 text-xs text-slate-400">
          <User className="h-4 w-4 text-slate-400" />
          <span className="hidden sm:inline font-mono">{userContext.email.split('@')[0]}</span>
        </div>

        {/* Refresh Button */}
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="rounded p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
          title="Refresh Data"
          aria-label="Refresh Data"
        >
          <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin text-indigo-400' : ''}`} />
        </button>
      </div>
    </header>
  );
};
