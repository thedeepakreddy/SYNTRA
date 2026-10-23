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
      {/* Top Banner - Double-Bezel Hardware Enclosure with HUD Brackets */}
      <div className="double-bezel-outer hud-corner relative overflow-hidden">
        {/* Prismatic Cyan / Emerald Atmosphere Ambient Refraction */}
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-80 h-80 rounded-full bg-cyan-500/15 blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-1/3 -mb-20 w-64 h-64 rounded-full bg-emerald-500/10 blur-3xl pointer-events-none" />
        <div className="absolute top-0 left-1/4 right-1/4 h-[1px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-80" />

        <div className="double-bezel-inner p-6 sm:p-7 backdrop-blur-2xl">
          <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-5">
            <div className="flex items-center space-x-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400/20 via-slate-900 to-cyan-500/10 text-cyan-300 border border-cyan-400/40 shadow-[0_0_20px_rgba(0,240,255,0.3),inset_0_1px_1px_rgba(255,255,255,0.4)]">
                <Users className="h-6 w-6" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="eyebrow-pill">
                    <Shield className="h-3 w-3 text-cyan-400" />
                    <span>PERSONAS DIRECTORY // 0xORGANIZATION</span>
                  </span>
                </div>
                <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-sans drop-shadow-[0_0_14px_rgba(0,240,255,0.3)] mt-1.5">
                  The 10 Specialized Engineering Personas
                </h2>
                <p className="mt-1 text-xs text-slate-300 max-w-2xl font-sans leading-relaxed">
                  SYNTRA enforces rigid role specialization and strict separation of powers according to AGENTS.md.
                  Agents are strictly typed, bounded by capability policies, and cryptographically barred from self-review.
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <span className="inline-flex items-center space-x-2 rounded-full bg-cyan-950/80 px-3.5 py-1.5 text-xs font-mono font-semibold text-cyan-300 border border-cyan-400/40 shadow-[0_0_14px_rgba(0,240,255,0.2),inset_0_1px_1px_rgba(255,255,255,0.25)]">
                <Shield className="h-3.5 w-3.5 text-cyan-400" />
                <span>AGENTS.md Enforced</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Governance & Separation of Powers Principles - Liquid Warning Glass */}
      <div className="liquid-glass-card rounded-2xl p-5 border border-amber-500/30 bg-gradient-to-br from-amber-500/[0.08] via-slate-950/80 to-[#020408]/90 shadow-[0_0_30px_rgba(255,184,0,0.1),inset_0_1.5px_1.5px_rgba(255,255,255,0.25)]">
        <div className="flex items-start space-x-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/15 border border-amber-400/40 text-amber-300 flex-shrink-0 mt-0.5 shadow-[0_0_15px_rgba(255,184,0,0.3)]">
            <ShieldAlert className="h-5 w-5" />
          </div>
          <div className="text-xs text-slate-300 space-y-3 flex-1">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="h-2 w-2 rounded-full bg-amber-400 shadow-[0_0_8px_#FFB800] animate-pulse" />
                <span className="font-semibold text-amber-300 font-sans tracking-wide uppercase text-xs">
                  Constitutional Anti-Collusion Rules
                </span>
              </div>
              <span className="font-mono text-[10px] text-amber-300 bg-amber-950/80 px-2.5 py-0.5 rounded-full border border-amber-500/40 font-bold uppercase tracking-wider">
                Zero Trust Boundary
              </span>
            </div>
            <ul className="grid grid-cols-1 md:grid-cols-3 gap-3.5 text-slate-300 pt-1 font-sans">
              <li className="liquid-control rounded-xl p-3.5 border border-white/[0.08] bg-slate-950/60 shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]">
                <strong className="text-amber-300 block text-xs mb-1 font-mono uppercase tracking-wider">1. Self-Review Invariant</strong>
                <span className="text-slate-300 text-[11px] leading-relaxed">The authoring agent is cryptographically barred from reviewing, auditing, or approving its own patch.</span>
              </li>
              <li className="liquid-control rounded-xl p-3.5 border border-white/[0.08] bg-slate-950/60 shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]">
                <strong className="text-amber-300 block text-xs mb-1 font-mono uppercase tracking-wider">2. Independent QA Invariant</strong>
                <span className="text-slate-300 text-[11px] leading-relaxed">QA acceptance tests must be formulated independently from PRD criteria, never copied from developer tests.</span>
              </li>
              <li className="liquid-control rounded-xl p-3.5 border border-white/[0.08] bg-slate-950/60 shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]">
                <strong className="text-amber-300 block text-xs mb-1 font-mono uppercase tracking-wider">3. Approval Boundary Invariant</strong>
                <span className="text-slate-300 text-[11px] leading-relaxed">No AI agent possesses authority to deploy or write external repos without human cryptographic authorization.</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 backdrop-blur-xl shadow-[0_0_20px_rgba(255,0,85,0.2)]">
          <p className="font-semibold font-sans">Error Loading Personas</p>
          <p className="mt-1 font-mono text-[11px]">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="liquid-glass-slab rounded-2xl p-12 text-center text-xs text-slate-400 font-mono tracking-wider">
          <span className="inline-block animate-spin mr-2 text-cyan-400">◓</span>
          RETRIEVING AGENT PERSONAS DOSSIER FROM KERNEL...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {agents.map((agent) => (
            <div
              key={agent.role}
              className="liquid-glass-card group rounded-2xl p-5 flex flex-col justify-between transition-all duration-200 hover:border-cyan-400/50 hover:shadow-[0_0_25px_rgba(0,240,255,0.15),inset_0_1.5px_1.5px_rgba(255,255,255,0.4)]"
            >
              <div>
                {/* Persona Header */}
                <div className="flex items-center justify-between pb-3.5 border-b border-white/[0.08]">
                  <div className="flex items-center space-x-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-400/30 text-cyan-300 shadow-[0_0_12px_rgba(0,240,255,0.2)]">
                      <Shield className="h-4 w-4" />
                    </div>
                    <div>
                      <h3 className="font-bold text-white text-sm font-sans group-hover:text-cyan-300 transition-colors">
                        {agent.display_name || agent.role.replace(/_/g, ' ')}
                      </h3>
                      <p className="font-mono text-[10px] text-cyan-400/70 font-semibold tracking-wider">
                        {agent.role}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    {agent.default_tier && (
                      <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-400/40 shadow-[0_0_8px_rgba(0,240,255,0.2)]">
                        {agent.default_tier}
                      </span>
                    )}
                  </div>
                </div>

                {/* Mandate */}
                <p className="mt-3.5 text-xs text-slate-200 font-medium font-sans leading-relaxed">
                  {agent.mandate}
                </p>

                {/* Core Responsibilities */}
                {agent.responsibilities && agent.responsibilities.length > 0 && (
                  <div className="mt-4">
                    <span className="text-[10px] font-mono font-bold text-slate-400 mb-2 block tracking-wider uppercase">
                      Core Responsibilities
                    </span>
                    <ul className="space-y-1.5 text-xs text-slate-300 font-sans">
                      {agent.responsibilities.map((r, idx) => (
                        <li key={idx} className="flex items-start space-x-2">
                          <span className="text-cyan-400 font-bold mt-0.5">▸</span>
                          <span className="leading-normal">{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Allowed Tools */}
                <div className="mt-4">
                  <span className="flex items-center space-x-1.5 text-[10px] font-mono font-bold text-emerald-400 mb-2 uppercase tracking-wider">
                    <Wrench className="h-3 w-3" />
                    <span>Allowed Capabilities</span>
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {(agent.allowed_tools || []).map((t) => (
                      <span
                        key={t}
                        className="rounded-lg bg-emerald-950/60 px-2 py-0.5 font-mono text-[10px] text-emerald-300 border border-emerald-400/30 shadow-[0_0_8px_rgba(0,255,157,0.15)]"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Forbidden Actions */}
                <div className="mt-4">
                  <span className="flex items-center space-x-1.5 text-[10px] font-mono font-bold text-rose-400 mb-1.5 uppercase tracking-wider">
                    <Ban className="h-3 w-3 text-rose-400" />
                    <span>Forbidden Actions</span>
                  </span>
                  <ul className="space-y-1.5 text-xs text-rose-300/90 font-sans">
                    {(agent.forbidden_actions || []).map((f, idx) => (
                      <li key={idx} className="flex items-start space-x-2">
                        <span className="text-rose-400 font-bold mt-0.5">✕</span>
                        <span className="leading-normal">{f}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Primary Inputs & Authoritative Outputs */}
              <div className="mt-5 pt-3.5 border-t border-white/[0.08] grid grid-cols-2 gap-3 text-[10px] font-mono">
                <div className="liquid-control rounded-xl p-2.5 border border-white/[0.06] bg-slate-950/60">
                  <span className="flex items-center space-x-1 text-slate-400 font-semibold mb-1">
                    <ArrowDownRight className="h-3 w-3 text-cyan-400" />
                    <span>Primary Inputs:</span>
                  </span>
                  <p className="text-slate-300 truncate" title={agent.primary_inputs?.join(', ')}>
                    {agent.primary_inputs && agent.primary_inputs.length > 0
                      ? agent.primary_inputs.join(', ')
                      : 'None specified'}
                  </p>
                </div>
                <div className="liquid-control rounded-xl p-2.5 border border-white/[0.06] bg-slate-950/60">
                  <span className="flex items-center space-x-1 text-slate-400 font-semibold mb-1">
                    <ArrowUpRight className="h-3 w-3 text-emerald-400" />
                    <span>Authoritative Outputs:</span>
                  </span>
                  <p className="text-slate-300 truncate" title={agent.authoritative_outputs?.join(', ')}>
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
