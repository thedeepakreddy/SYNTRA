import React, { useState } from 'react';
import { MembershipRole, SystemOverview, UserContext } from '../types';
import { StatusBadge } from './StatusBadge';
import { RefreshCw, Shield, User, Building2, Check, Copy } from 'lucide-react';

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
  const [copiedOrg, setCopiedOrg] = useState(false);

  const handleCopyOrg = () => {
    navigator.clipboard.writeText(userContext.orgId);
    setCopiedOrg(true);
    setTimeout(() => setCopiedOrg(false), 2000);
  };

  return (
    <header className="sticky top-0 z-20 flex h-16 w-full items-center justify-between border-b border-cyan-500/15 bg-[#030712]/80 px-6 backdrop-blur-2xl shadow-[0_4px_24px_rgba(0,0,0,0.7),inset_0_-1px_1px_rgba(0,240,255,0.06)]">
      {/* Route Title & Cyberpunk HUD Breadcrumb */}
      <div className="flex items-center space-x-3">
        <div className="hidden sm:flex items-center space-x-1.5 text-xs font-mono text-cyan-400/70 font-semibold tracking-wider">
          <span>SYS://CONTROL</span>
          <span className="text-slate-600">/</span>
        </div>
        <h1 className="text-base font-bold tracking-tight text-white font-sans drop-shadow-[0_0_10px_rgba(255,255,255,0.15)]">
          {currentRouteTitle}
        </h1>
        {overview && (
          <span className="hidden md:inline-flex ml-2">
            <StatusBadge status={overview.system_health} />
          </span>
        )}
      </div>

      {/* Right Controls: Environment, Tenant, Role Switcher, Refresh */}
      <div className="flex items-center space-x-3">
        {/* Environment Badge */}
        <div className="hidden md:flex items-center space-x-2 px-3 py-1 rounded-full bg-cyan-950/40 border border-cyan-500/30 text-[11px] font-mono text-cyan-200 shadow-[inset_0_1px_1px_rgba(255,255,255,0.15)]">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400 shadow-[0_0_8px_#00FF9D]" />
          </span>
          <span className="tracking-wider uppercase font-bold">{overview?.environment?.toUpperCase() || 'DEVELOPMENT'}</span>
        </div>

        {/* Tenant/Org Badge */}
        <button
          onClick={handleCopyOrg}
          className="hidden lg:flex items-center space-x-1.5 px-3 py-1 rounded-full bg-slate-900/70 hover:bg-slate-800/80 border border-white/[0.1] text-[11px] font-mono text-slate-300 transition-all duration-150 active:scale-[0.97] shadow-[inset_0_1px_1px_rgba(255,255,255,0.08)]"
          title="Click to copy Org UUID"
        >
          <Building2 className="h-3.5 w-3.5 text-cyan-400" />
          <span className="truncate max-w-[100px]">{userContext.orgId.slice(0, 8)}...</span>
          {copiedOrg ? (
            <Check className="h-3 w-3 text-emerald-400" />
          ) : (
            <Copy className="h-3 w-3 text-slate-500" />
          )}
        </button>

        {/* Role Switcher Pill - Liquid Glass Pill */}
        <div className="flex items-center space-x-2 bg-gradient-to-r from-cyan-950/40 via-slate-900/80 to-slate-900/80 border border-cyan-500/35 rounded-full px-3 py-1 shadow-[inset_0_1px_1.5px_rgba(255,255,255,0.3),0_0_15px_rgba(0,240,255,0.15)]">
          <Shield className="h-3.5 w-3.5 text-cyan-400" />
          <label htmlFor="role-select" className="text-xs text-slate-400 sr-only">
            Role
          </label>
          <select
            id="role-select"
            value={userContext.role}
            onChange={(e) => onRoleChange(e.target.value as MembershipRole)}
            className="bg-transparent text-xs font-semibold text-cyan-200 focus:outline-none cursor-pointer tracking-tight capitalize"
            aria-label="Switch User Role"
          >
            <option value="admin" className="bg-[#050914] text-slate-100">
              Admin
            </option>
            <option value="developer" className="bg-[#050914] text-slate-100">
              Developer
            </option>
            <option value="viewer" className="bg-[#050914] text-slate-100">
              Viewer
            </option>
          </select>
        </div>

        {/* User Identity Chip */}
        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-slate-900/60 border border-white/[0.08] text-xs text-slate-400 font-mono">
          <User className="h-3.5 w-3.5 text-slate-400" />
          <span className="hidden sm:inline text-[11px] font-medium text-slate-300">
            {userContext.email.split('@')[0]}
          </span>
        </div>

        {/* Refresh Button */}
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="rounded-full p-2 text-slate-400 hover:bg-cyan-500/10 hover:text-cyan-300 border border-white/[0.08] hover:border-cyan-500/30 transition-all duration-150 active:scale-[0.95] disabled:opacity-50"
          title="Refresh Live Data"
          aria-label="Refresh Data"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? 'animate-spin text-cyan-400' : ''}`} />
        </button>
      </div>
    </header>
  );
};
