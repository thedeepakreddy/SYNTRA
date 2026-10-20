import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { AgentPersona } from '../types';
import { Users, Shield, Wrench, Ban, ArrowDownRight, ArrowUpRight, ShieldAlert } from 'lucide-react';

export const AgentsPage: React.FC = () => {
  const [agents, setAgents] = useState<AgentPersona[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAgents = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getAgents();
      setAgents(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load engineering personas.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAgents();
  }, []);

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow">
        <div className="flex items-center space-x-3">
          <div className="rounded-lg bg-indigo-600/20 p-2 text-indigo-400 border border-indigo-500/30">
            <Users className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight text-white">
              The 10 Specialized Engineering Personas
            </h2>
            <p className="mt-1 text-xs text-slate-400 max-w-3xl">
              SYNTRA enforces role specialization and separation of powers according to AGENTS.md.
              Agents are strictly typed, bounded by capability policies, and forbidden from self-review.
            </p>
          </div>
        </div>
      </div>

      {/* Governance & Separation of Powers Principles */}
      <div className="rounded-xl border border-amber-900/40 bg-amber-950/20 p-4">
        <div className="flex items-start space-x-3">
          <ShieldAlert className="h-5 w-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-slate-300 space-y-1">
            <span className="font-semibold text-amber-300">Constitutional Anti-Collusion Rules:</span>
            <ul className="list-disc list-inside space-y-0.5 text-slate-400">
              <li>
                <strong className="text-slate-300">Self-Review Invariant:</strong> The authoring agent is cryptographically barred from reviewing or approving its own patch.
              </li>
              <li>
                <strong className="text-slate-300">Independent QA Invariant:</strong> QA acceptance tests must be formulated independently from PRD requirements, never copied from developer tests.
              </li>
              <li>
                <strong className="text-slate-300">Approval Boundary Invariant:</strong> No AI agent possesses authority to deploy or write external repos without human cryptographic authorization.
              </li>
            </ul>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-800 bg-rose-950/40 p-4 text-xs text-rose-300">
          <p className="font-semibold">Error Loading Personas</p>
          <p className="mt-1 font-mono">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="p-8 text-center text-xs text-slate-500">Loading engineering personas...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {agents.map((agent) => (
            <div
              key={agent.role}
              className="flex flex-col justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow hover:border-slate-700 transition-colors"
            >
              <div>
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center space-x-2">
                    <Shield className="h-4 w-4 text-indigo-400" />
                    <h3 className="font-semibold text-slate-100 text-sm">
                      {agent.display_name || agent.role.replace(/_/g, ' ')}
                    </h3>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    {agent.default_tier && (
                      <span className="font-mono text-[9px] font-semibold px-1.5 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/60">
                        {agent.default_tier}
                      </span>
                    )}
                    <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                      {agent.role}
                    </span>
                  </div>
                </div>

                <p className="mt-3 text-xs text-slate-300 font-medium">{agent.mandate}</p>

                {/* Core Responsibilities */}
                {agent.responsibilities && agent.responsibilities.length > 0 && (
                  <div className="mt-3">
                    <span className="text-[11px] font-semibold text-slate-400 mb-1 block">
                      Core Responsibilities
                    </span>
                    <ul className="space-y-0.5 text-[11px] text-slate-300">
                      {agent.responsibilities.map((r, idx) => (
                        <li key={idx} className="flex items-start space-x-1.5">
                          <span className="text-indigo-400 font-bold">•</span>
                          <span>{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Allowed Tools */}
                <div className="mt-4">
                  <span className="flex items-center space-x-1 text-[11px] font-semibold text-slate-400 mb-1.5">
                    <Wrench className="h-3 w-3 text-emerald-400" />
                    <span>Allowed Tools</span>
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {(agent.allowed_tools || []).map((t) => (
                      <span
                        key={t}
                        className="rounded bg-slate-800/80 px-2 py-0.5 font-mono text-[10px] text-emerald-300 border border-emerald-900/40"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Forbidden Actions */}
                <div className="mt-3">
                  <span className="flex items-center space-x-1 text-[11px] font-semibold text-slate-400 mb-1.5">
                    <Ban className="h-3 w-3 text-rose-400" />
                    <span>Forbidden Actions</span>
                  </span>
                  <ul className="space-y-1 text-[11px] text-rose-300/90">
                    {(agent.forbidden_actions || []).map((f, idx) => (
                      <li key={idx} className="flex items-start space-x-1.5">
                        <span className="text-rose-500 font-bold">•</span>
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Inputs & Outputs */}
              <div className="mt-4 pt-3 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-[10px] text-slate-400 font-mono">
                <div>
                  <span className="flex items-center space-x-0.5 text-slate-500 font-semibold mb-1">
                    <ArrowDownRight className="h-3 w-3 text-cyan-400" />
                    <span>Primary Inputs:</span>
                  </span>
                  <p className="text-slate-300">
                    {agent.primary_inputs && agent.primary_inputs.length > 0
                      ? agent.primary_inputs.join(', ')
                      : 'None specified'}
                  </p>
                </div>
                <div>
                  <span className="flex items-center space-x-0.5 text-slate-500 font-semibold mb-1">
                    <ArrowUpRight className="h-3 w-3 text-indigo-400" />
                    <span>Authoritative Outputs:</span>
                  </span>
                  <p className="text-slate-300">
                    {agent.authoritative_outputs && agent.authoritative_outputs.length > 0
                      ? agent.authoritative_outputs.join(', ')
                      : 'None specified'}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
