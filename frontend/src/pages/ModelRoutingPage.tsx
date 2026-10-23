import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import {
  ModelRoutingPolicy,
  ModelSpec,
  RoutingSimulationRequest,
  RoutingSimulationResponse,
} from '../types';
import { StatusBadge } from '../components/StatusBadge';
import {
  Cpu,
  Play,
  CheckCircle2,
  Sliders,
  Layers,
  AlertCircle,
  Sparkles,
  Zap,
} from 'lucide-react';

const ROLES = [
  'product_manager',
  'software_architect',
  'engineering_manager',
  'backend_engineer',
  'frontend_engineer',
  'qa_engineer',
  'devops_engineer',
  'security_reviewer',
  'code_reviewer',
  'debugging_specialist',
];

export const ModelRoutingPage: React.FC = () => {
  const [models, setModels] = useState<ModelSpec[]>([]);
  const [policy, setPolicy] = useState<ModelRoutingPolicy | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Simulation Form State
  const [simRequest, setSimRequest] = useState<RoutingSimulationRequest>({
    agent_role: 'product_manager',
    task_type: 'architecture_spec',
    requested_model: '',
  });
  const [simResult, setSimResult] = useState<RoutingSimulationResponse | null>(null);
  const [simLoading, setSimLoading] = useState(false);
  const [simError, setSimError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [modelsData, policyData] = await Promise.all([
        apiClient.getModels(),
        apiClient.getModelRoutingPolicy(),
      ]);
      setModels(modelsData);
      setPolicy(policyData);
    } catch (err: any) {
      setError(err.message || 'Failed to load model catalog or routing policies.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSimulate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSimLoading(true);
      setSimError(null);
      setSimResult(null);
      const payload: RoutingSimulationRequest = {
        agent_role: simRequest.agent_role || undefined,
        task_type: simRequest.task_type || undefined,
        requested_model: simRequest.requested_model?.trim() || undefined,
      };
      const result = await apiClient.simulateModelRouting(payload);
      setSimResult(result);
    } catch (err: any) {
      setSimError(err.message || 'Failed to simulate model routing decision.');
    } finally {
      setSimLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner - Double-Bezel Hardware Enclosure with HUD Brackets */}
      <div className="double-bezel-outer hud-corner relative overflow-hidden">
        {/* Prismatic Cyan / Emerald Atmosphere Ambient Refraction */}
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-80 h-80 rounded-full bg-cyan-500/15 blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-1/3 -mb-20 w-64 h-64 rounded-full bg-emerald-500/10 blur-3xl pointer-events-none" />
        <div className="absolute top-0 left-1/4 right-1/4 h-[1px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-80" />

        <div className="double-bezel-inner p-6 backdrop-blur-2xl">
          <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center space-x-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400/20 via-slate-900 to-cyan-500/10 text-cyan-300 border border-cyan-400/40 shadow-[0_0_20px_rgba(0,240,255,0.3),inset_0_1px_1px_rgba(255,255,255,0.4)]">
                <Cpu className="h-6 w-6" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="eyebrow-pill">
                    <Cpu className="h-3 w-3 text-cyan-400" />
                    <span>NEURAL DISPATCH // ROUTING FABRIC</span>
                  </span>
                </div>
                <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-sans drop-shadow-[0_0_14px_rgba(0,240,255,0.3)] mt-1.5">
                  Model Routing, Tiering & Decision Traceability
                </h2>
                <p className="mt-0.5 text-xs text-slate-300 max-w-2xl font-sans">
                  SYNTRA routes each task to the optimal LLM tier (Reasoning, Balanced, Fast) based on
                  persona mandate, complexity heuristics, and budget constraints without manual intervention.
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <span className="inline-flex items-center space-x-2 rounded-full bg-emerald-950/80 px-3.5 py-1.5 text-xs font-mono font-semibold text-emerald-300 border border-emerald-400/40 shadow-[0_0_14px_rgba(0,255,157,0.2),inset_0_1px_1px_rgba(255,255,255,0.25)]">
                <Zap className="h-3.5 w-3.5 text-emerald-400 shadow-[0_0_8px_#00FF9D]" />
                <span>Zero-Cost Test Routing Active</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 backdrop-blur-xl shadow-[0_0_20px_rgba(255,0,85,0.2)]">
          <p className="font-semibold font-sans">Error Loading Model Metadata</p>
          <p className="mt-1 font-mono text-[11px]">{error}</p>
        </div>
      )}

      {/* Model Routing Simulator (Interactive Tool) */}
      <div className="liquid-glass-slab hud-corner rounded-2xl p-6 relative overflow-hidden">
        <div className="flex items-center space-x-2.5 pb-4 border-b border-white/[0.08]">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-500/10 border border-cyan-400/30 text-cyan-300 shadow-[0_0_12px_rgba(0,240,255,0.2)]">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white font-sans tracking-wide">Live Model Routing Simulator</h3>
            <p className="text-xs text-slate-400 font-sans">
              Test real-time routing policy evaluation across agent roles, task classifications, and model overrides.
            </p>
          </div>
        </div>

        <form onSubmit={handleSimulate} className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-mono font-bold uppercase tracking-wider text-slate-300 mb-1.5">
              Agent Persona
            </label>
            <select
              value={simRequest.agent_role}
              onChange={(e) => setSimRequest({ ...simRequest, agent_role: e.target.value })}
              className="liquid-control w-full rounded-xl border border-white/[0.1] bg-slate-950/80 px-3.5 py-2.5 text-xs text-slate-200 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400 transition-all font-sans"
            >
              {ROLES.map((r) => (
                <option key={r} value={r} className="bg-slate-950 text-slate-200">
                  {r.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-mono font-bold uppercase tracking-wider text-slate-300 mb-1.5">
              Task Classification
            </label>
            <input
              type="text"
              placeholder="e.g. architecture_spec, code_generation, unit_test"
              value={simRequest.task_type}
              onChange={(e) => setSimRequest({ ...simRequest, task_type: e.target.value })}
              className="liquid-control w-full rounded-xl border border-white/[0.1] bg-slate-950/80 px-3.5 py-2.5 text-xs text-slate-200 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400 transition-all font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-mono font-bold uppercase tracking-wider text-slate-300 mb-1.5">
              Requested Model Override (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. gemini-2.5-pro, custom-eval"
              value={simRequest.requested_model}
              onChange={(e) => setSimRequest({ ...simRequest, requested_model: e.target.value })}
              className="liquid-control w-full rounded-xl border border-white/[0.1] bg-slate-950/80 px-3.5 py-2.5 text-xs text-cyan-200 font-mono focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400 transition-all"
            />
          </div>

          <div className="md:col-span-3 flex justify-end pt-2">
            <button
              type="submit"
              disabled={simLoading}
              className="inline-flex items-center space-x-2 rounded-xl bg-gradient-to-r from-cyan-500 to-cyan-600 px-5 py-2.5 text-xs font-mono font-bold text-slate-950 shadow-[0_0_20px_rgba(0,240,255,0.4),inset_0_1px_1px_rgba(255,255,255,0.6)] hover:brightness-110 active:scale-[0.98] disabled:opacity-50 transition-all tracking-wider uppercase"
            >
              <Play className="h-3.5 w-3.5 fill-current" />
              <span>{simLoading ? 'Evaluating Decision...' : 'Simulate Routing Decision'}</span>
            </button>
          </div>
        </form>

        {simError && (
          <div className="mt-4 flex items-start space-x-2 rounded-xl border border-rose-500/40 bg-rose-950/40 p-3 text-xs text-rose-300 font-sans backdrop-blur-xl">
            <AlertCircle className="h-4 w-4 flex-shrink-0 text-rose-400 mt-0.5" />
            <span>{simError}</span>
          </div>
        )}

        {simResult && (
          <div className="mt-5 rounded-xl border border-emerald-400/30 bg-emerald-950/30 p-5 text-xs backdrop-blur-xl shadow-[0_0_25px_rgba(0,255,157,0.15)]">
            <div className="flex items-center space-x-2 text-emerald-400 font-bold mb-3.5">
              <CheckCircle2 className="h-4 w-4 shadow-[0_0_8px_#00FF9D]" />
              <span className="font-mono text-xs uppercase tracking-wider">Routing Decision Resolved</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 font-mono">
              <div className="liquid-control rounded-xl bg-slate-950/80 p-3.5 border border-white/[0.08]">
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-bold">ASSIGNED TIER</span>
                <span className="text-emerald-300 font-bold text-base">{simResult.assigned_tier}</span>
              </div>
              <div className="liquid-control rounded-xl bg-slate-950/80 p-3.5 border border-white/[0.08]">
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-bold">RESOLVED MODEL</span>
                <span className="text-cyan-300 font-bold text-base">{simResult.resolved_model}</span>
              </div>
              <div className="liquid-control rounded-xl bg-slate-950/80 p-3.5 border border-white/[0.08]">
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-bold">COST TIER</span>
                <span className="text-amber-300 font-bold text-base">{simResult.estimated_cost_tier}</span>
              </div>
            </div>
            <p className="mt-3.5 text-slate-300 font-mono text-xs bg-slate-950/90 p-3.5 rounded-xl border border-white/[0.08]">
              <strong className="text-cyan-400">Rationale: </strong>
              {simResult.rationale}
            </p>
          </div>
        )}
      </div>

      {/* Model Catalog & Pricing - Liquid Glass Table */}
      <div className="liquid-glass-card rounded-2xl p-6">
        <div className="flex items-center justify-between pb-4 border-b border-white/[0.08]">
          <div className="flex items-center space-x-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-500/10 border border-cyan-400/30 text-cyan-300">
              <Layers className="h-4 w-4" />
            </div>
            <h3 className="text-sm font-bold text-white font-sans tracking-wide">Registered Model Catalog</h3>
          </div>
          <span className="text-xs text-cyan-400 font-mono font-bold bg-cyan-950/80 px-2.5 py-0.5 rounded-full border border-cyan-400/30">
            {models.length} Models Active
          </span>
        </div>

        {loading ? (
          <div className="p-10 text-center text-xs text-slate-400 font-mono tracking-wider">
            <span className="inline-block animate-spin mr-2 text-cyan-400">◓</span>
            LOADING REGISTERED MODEL SPECS...
          </div>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-950/90 text-cyan-400/80 border-b border-white/[0.08] uppercase text-[10px] tracking-wider font-bold">
                <tr>
                  <th className="py-3 px-3">Model ID</th>
                  <th className="py-3 px-3">Family</th>
                  <th className="py-3 px-3">Routing Tier</th>
                  <th className="py-3 px-3">Context Window</th>
                  <th className="py-3 px-3">Input / 1M Tokens</th>
                  <th className="py-3 px-3">Output / 1M Tokens</th>
                  <th className="py-3 px-3">Default</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {models.map((m) => (
                  <tr key={m.model_id} className="hover:bg-cyan-500/[0.04] transition-colors">
                    <td className="py-3 px-3 text-white font-bold">{m.model_id}</td>
                    <td className="py-3 px-3 text-slate-300">{m.family}</td>
                    <td className="py-3 px-3">
                      <StatusBadge status={m.tier} />
                    </td>
                    <td className="py-3 px-3 text-slate-300">
                      {m.max_context_window ? `${(m.max_context_window / 1000).toFixed(0)}k` : '—'}
                    </td>
                    <td className="py-3 px-3 text-slate-200">
                      ${m.input_token_cost_per_million ? m.input_token_cost_per_million.toFixed(2) : '0.00'}
                    </td>
                    <td className="py-3 px-3 text-slate-200">
                      ${m.output_token_cost_per_million ? m.output_token_cost_per_million.toFixed(2) : '0.00'}
                    </td>
                    <td className="py-3 px-3">
                      {m.is_default && (
                        <span className="text-[10px] bg-cyan-950 text-cyan-300 border border-cyan-400/40 px-2 py-0.5 rounded-full font-bold shadow-[0_0_8px_rgba(0,240,255,0.2)]">
                          DEFAULT
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Role-to-Tier Policy Map */}
      {policy && (
        <div className="liquid-glass-card rounded-2xl p-6">
          <div className="flex items-center space-x-2.5 pb-4 border-b border-white/[0.08]">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-500/10 border border-cyan-400/30 text-cyan-300">
              <Sliders className="h-4 w-4" />
            </div>
            <h3 className="text-sm font-bold text-white font-sans tracking-wide">Role-Based Tiering Policies</h3>
          </div>
          <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5 font-mono text-xs">
            {Object.entries(policy.role_defaults).map(([role, tier]) => (
              <div
                key={role}
                className="liquid-control flex items-center justify-between p-3.5 rounded-xl border border-white/[0.08] bg-slate-950/70"
              >
                <span className="text-slate-200 capitalize font-sans font-medium text-xs">
                  {role.replace(/_/g, ' ')}
                </span>
                <StatusBadge status={tier} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
