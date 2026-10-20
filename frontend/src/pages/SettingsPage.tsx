import React, { useState } from 'react';
import { apiClient } from '../api/client';
import { MembershipRole, UserContext } from '../types';
import { Settings, User, Lock, Save, CheckCircle2 } from 'lucide-react';

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
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow">
        <div className="flex items-center space-x-3">
          <div className="rounded-lg bg-indigo-600/20 p-2 text-indigo-400 border border-indigo-500/30">
            <Settings className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight text-white">
              Tenant Settings & RBAC Context Configuration
            </h2>
            <p className="mt-1 text-xs text-slate-400 max-w-3xl">
              Configure tenant parameters, test RBAC role transitions, and verify security redactor boundaries.
            </p>
          </div>
        </div>
      </div>

      {savedSuccess && (
        <div className="rounded-lg border border-emerald-800 bg-emerald-950/40 p-3 text-xs text-emerald-300 flex items-center space-x-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          <span>Active user context updated successfully.</span>
        </div>
      )}

      {/* User Context & Dev Auth Config */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
        <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
          <User className="h-4 w-4 text-indigo-400" />
          <h3 className="text-sm font-semibold text-slate-100">Active Operator Identity (RBAC)</h3>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4 max-w-xl">
          <div>
            <label className="block text-xs font-medium text-slate-300">Membership Role</label>
            <select
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value as MembershipRole })}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            >
              <option value="admin">Admin (Full administrative & approval access)</option>
              <option value="developer">Developer (Project/mission management & approvals)</option>
              <option value="viewer">Viewer (Read-only access, mutations blocked)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300">Operator Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-200 font-mono focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300">User UUID (sub)</label>
            <input
              type="text"
              value={formData.userId}
              onChange={(e) => setFormData({ ...formData, userId: e.target.value })}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-200 font-mono focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300">Organization UUID (org_id)</label>
            <input
              type="text"
              value={formData.orgId}
              onChange={(e) => setFormData({ ...formData, orgId: e.target.value })}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-200 font-mono focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <button
            type="submit"
            className="inline-flex items-center space-x-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-medium text-white shadow hover:bg-indigo-500"
          >
            <Save className="h-4 w-4" />
            <span>Apply Context Changes</span>
          </button>
        </form>
      </div>

      {/* Security & Isolation Configuration */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
        <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
          <Lock className="h-4 w-4 text-emerald-400" />
          <h3 className="text-sm font-semibold text-slate-100">Security & Isolation Configuration</h3>
        </div>

        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="rounded-lg bg-slate-950 p-3 border border-slate-800">
            <span className="text-slate-500 text-[10px] uppercase">Secret Scrubber</span>
            <p className="mt-1 font-semibold text-emerald-300">FAIL_CLOSED (Active)</p>
            <p className="mt-1 text-[11px] text-slate-400 font-sans">
              Scrubs passwords, Bearer tokens, API keys, and nested secrets from logs, spans, and sandboxes.
            </p>
          </div>

          <div className="rounded-lg bg-slate-950 p-3 border border-slate-800">
            <span className="text-slate-500 text-[10px] uppercase">Telemetry Exporter</span>
            <p className="mt-1 font-semibold text-emerald-300">IN_MEMORY_ISOLATED</p>
            <p className="mt-1 text-[11px] text-slate-400 font-sans">
              Zero telemetry leaks over external network; spans are scrubbed and held in-process.
            </p>
          </div>

          <div className="rounded-lg bg-slate-950 p-3 border border-slate-800">
            <span className="text-slate-500 text-[10px] uppercase">Execution Sandbox</span>
            <p className="mt-1 font-semibold text-indigo-300">SUBPROCESS_WORKTREE</p>
            <p className="mt-1 text-[11px] text-slate-400 font-sans">
              Ephemeral git worktrees with strict environment variable scrubbing and timeout enforcement.
            </p>
          </div>

          <div className="rounded-lg bg-slate-950 p-3 border border-slate-800">
            <span className="text-slate-500 text-[10px] uppercase">Delivery Gate</span>
            <p className="mt-1 font-semibold text-amber-300">HMAC_SHA256_REQUIRED</p>
            <p className="mt-1 text-[11px] text-slate-400 font-sans">
              External writes and production actions strictly require cryptographic human signature validation.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
