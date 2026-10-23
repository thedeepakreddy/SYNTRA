import React, { useState } from 'react';
import { apiClient } from '../api/client';
import { MembershipRole, UserContext } from '../types';
import { User, Lock, Save, CheckCircle2, ShieldCheck } from 'lucide-react';

interface SettingsPageProps {
  userContext: UserContext;
  onUserContextChange: (ctx: UserContext) => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ userContext, onUserContextChange }) => {
  const [formData, setFormData] = useState<UserContext>({ ...userContext });
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    apiClient.setUserContext(formData);
    onUserContextChange(formData);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  return (
    <div className="space-y-8 pb-12">
      {/* Top Hero: Machined Hardware Double-Bezel Enclosure */}
      <div className="double-bezel-outer">
        <div className="double-bezel-inner p-6 sm:p-8 relative overflow-hidden">
          {/* Ambient Photon Atmosphere */}
          <div className="absolute -top-24 -right-24 w-96 h-96 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />
          <div className="absolute -bottom-24 left-1/3 w-80 h-80 rounded-full bg-emerald-500/10 blur-3xl pointer-events-none" />

          <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="eyebrow-pill text-cyan-400 border-cyan-500/30">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
                  PLATFORM PARAMS // MULTI-TENANT CONFIG
                </span>
                <span className="px-2.5 py-0.5 rounded-full bg-slate-900/80 border border-white/10 text-[10px] font-mono text-slate-400">
                  RBAC SECURITY BOUNDARY
                </span>
              </div>
              <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-white font-sans drop-shadow-[0_0_14px_rgba(0,240,255,0.3)]">
                Tenant Settings &amp; RBAC Context Configuration
              </h2>
              <p className="text-xs sm:text-sm text-slate-300 max-w-2xl font-sans leading-relaxed">
                Configure tenant parameters, test RBAC role transitions, and verify security redactor boundaries with
                cryptographic authorization checks.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
              <span className="inline-flex items-center space-x-2 rounded-full bg-cyan-950/80 px-4 py-2 text-xs font-mono font-semibold text-cyan-300 border border-cyan-400/40 shadow-[0_0_14px_rgba(0,240,255,0.2),inset_0_1px_1px_rgba(255,255,255,0.25)]">
                <ShieldCheck className="h-4 w-4 text-cyan-400" />
                <span>Multi-Tenant Enforced</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {savedSuccess && (
        <div className="double-bezel-outer">
          <div className="double-bezel-inner p-4 text-xs text-emerald-300 flex items-center space-x-3 bg-emerald-950/40">
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            <span className="font-sans font-medium">Active operator context updated successfully.</span>
          </div>
        </div>
      )}

      {/* User Context & Dev Auth Config */}
      <div className="double-bezel-outer">
        <div className="double-bezel-inner p-6 sm:p-7 space-y-6">
          <div className="flex items-center space-x-2.5 pb-4 border-b border-white/[0.08]">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-500/10 border border-cyan-400/30 text-cyan-300">
              <User className="h-4 w-4" />
            </div>
            <h3 className="text-sm font-bold text-white font-sans tracking-wide">
              Active Operator Identity (RBAC Matrix)
            </h3>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5 max-w-xl">
            <div>
              <label className="block text-xs font-mono font-bold uppercase tracking-wider text-slate-300 mb-1.5">
                Membership Role
              </label>
              <select
                value={formData.role}
                onChange={(e) => setFormData({ ...formData, role: e.target.value as MembershipRole })}
                className="liquid-control w-full rounded-xl border border-white/[0.1] bg-slate-950/80 px-4 py-2.5 text-xs text-slate-200 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400 transition-all font-sans"
              >
                <option value="admin" className="bg-slate-950 text-slate-200">
                  Admin (Full administrative &amp; delivery gate approval access)
                </option>
                <option value="developer" className="bg-slate-950 text-slate-200">
                  Developer (Project/mission management &amp; code approvals)
                </option>
                <option value="viewer" className="bg-slate-950 text-slate-200">
                  Viewer (Read-only access, mutations and delivery blocked)
                </option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-mono font-bold uppercase tracking-wider text-slate-300 mb-1.5">
                Operator Email
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="liquid-control w-full rounded-xl border border-white/[0.1] bg-slate-950/80 px-4 py-2.5 text-xs text-cyan-200 font-mono focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400 transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-mono font-bold uppercase tracking-wider text-slate-300 mb-1.5">
                User UUID (sub)
              </label>
              <input
                type="text"
                value={formData.userId}
                onChange={(e) => setFormData({ ...formData, userId: e.target.value })}
                className="liquid-control w-full rounded-xl border border-white/[0.1] bg-slate-950/80 px-4 py-2.5 text-xs text-cyan-200 font-mono focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400 transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-mono font-bold uppercase tracking-wider text-slate-300 mb-1.5">
                Organization UUID (org_id)
              </label>
              <input
                type="text"
                value={formData.orgId}
                onChange={(e) => setFormData({ ...formData, orgId: e.target.value })}
                className="liquid-control w-full rounded-xl border border-white/[0.1] bg-slate-950/80 px-4 py-2.5 text-xs text-cyan-200 font-mono focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400 transition-all"
              />
            </div>

            <div className="pt-2">
              <button
                type="submit"
                className="btn-island-primary group"
              >
                <span>Apply Context Changes</span>
                <span className="btn-island-icon">
                  <Save className="w-3.5 h-3.5 text-slate-950" />
                </span>
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Security & Isolation Configuration */}
      <div className="double-bezel-outer">
        <div className="double-bezel-inner p-6 sm:p-7 space-y-6">
          <div className="flex items-center space-x-2.5 pb-4 border-b border-white/[0.08]">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-400/30 text-emerald-300">
              <Lock className="h-4 w-4" />
            </div>
            <h3 className="text-sm font-bold text-white font-sans tracking-wide">
              Security &amp; Isolation Architecture
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-xs font-mono">
            <div className="liquid-glass-card rounded-xl p-4 border border-white/[0.08]">
              <span className="text-slate-400 text-[10px] uppercase font-mono font-bold">Secret Scrubber</span>
              <p className="mt-1 font-bold text-emerald-300">FAIL_CLOSED (Active)</p>
              <p className="mt-1.5 text-[11px] text-slate-300 font-sans leading-relaxed">
                Scrubs passwords, Bearer tokens, API keys, and nested secrets from logs, spans, and sandboxes.
              </p>
            </div>

            <div className="liquid-glass-card rounded-xl p-4 border border-white/[0.08]">
              <span className="text-slate-400 text-[10px] uppercase font-mono font-bold">Telemetry Exporter</span>
              <p className="mt-1 font-bold text-emerald-300">IN_MEMORY_ISOLATED</p>
              <p className="mt-1.5 text-[11px] text-slate-300 font-sans leading-relaxed">
                Zero telemetry leaks over external network; spans are scrubbed and held in-process.
              </p>
            </div>

            <div className="liquid-glass-card rounded-xl p-4 border border-white/[0.08]">
              <span className="text-slate-400 text-[10px] uppercase font-mono font-bold">Execution Sandbox</span>
              <p className="mt-1 font-bold text-cyan-300">SUBPROCESS_WORKTREE</p>
              <p className="mt-1.5 text-[11px] text-slate-300 font-sans leading-relaxed">
                Ephemeral git worktrees with strict environment variable scrubbing and timeout enforcement.
              </p>
            </div>

            <div className="liquid-glass-card rounded-xl p-4 border border-white/[0.08]">
              <span className="text-slate-400 text-[10px] uppercase font-mono font-bold">Cryptographic Delivery Gate</span>
              <p className="mt-1 font-bold text-cyan-300">HMAC_SHA256_ACTIVE</p>
              <p className="mt-1.5 text-[11px] text-slate-300 font-sans leading-relaxed">
                Tamper-evident cryptographic signature digest verified before any patch merge or deployment.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
