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
      {/* Top Banner */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow">
        <div className="flex items-center space-x-3">
          <div className="rounded-lg bg-indigo-600/20 p-2 text-indigo-400 border border-indigo-500/30">
            <Cpu className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight text-white">
              Model Routing, Tiering & Decision Traceability
            </h2>
            <p className="mt-1 text-xs text-slate-400 max-w-3xl">
              SYNTRA routes each task to the optimal LLM tier (Reasoning, Balanced, Fast) based on
              persona mandate, complexity heuristics, and budget constraints without manual intervention.
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-800 bg-rose-950/40 p-4 text-xs text-rose-300">
          <p className="font-semibold">Error Loading Model Metadata</p>
          <p className="mt-1 font-mono">{error}</p>
        </div>
      )}

      {/* Model Routing Simulator (Interactive Tool) */}
      <div className="rounded-xl border border-indigo-900/60 bg-gradient-to-br from-indigo-950/30 via-slate-900 to-slate-900 p-6 shadow-xl">
        <div className="flex items-center space-x-2 pb-3 border-b border-indigo-900/40">
          <Sparkles className="h-4 w-4 text-indigo-400" />
          <h3 className="text-sm font-semibold text-slate-100">Live Model Routing Simulator</h3>
        </div>
        <p className="text-xs text-slate-400 mt-2">
          Test real-time routing policy evaluation across agent roles, task classifications, and model overrides.
        </p>

        <form onSubmit={handleSimulate} className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300">Agent Persona</label>
            <select
              value={simRequest.agent_role}
              onChange={(e) => setSimRequest({ ...simRequest, agent_role: e.target.value })}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300">Task Classification</label>
            <input
              type="text"
              placeholder="e.g. architecture_spec, code_generation, unit_test"
              value={simRequest.task_type}
              onChange={(e) => setSimRequest({ ...simRequest, task_type: e.target.value })}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300">
              Requested Model Override (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. gemini-2.5-pro, custom-eval"
              value={simRequest.requested_model}
              onChange={(e) => setSimRequest({ ...simRequest, requested_model: e.target.value })}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div className="md:col-span-3 flex justify-end">
            <button
              type="submit"
              disabled={simLoading}
              className="inline-flex items-center space-x-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-medium text-white shadow hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:opacity-50"
            >
              <Play className="h-3.5 w-3.5 fill-current" />
              <span>{simLoading ? 'Evaluating Decision...' : 'Simulate Routing Decision'}</span>
            </button>
          </div>
        </form>

        {simError && (
          <div className="mt-4 flex items-start space-x-2 rounded-lg border border-rose-800 bg-rose-950/40 p-3 text-xs text-rose-300">
            <AlertCircle className="h-4 w-4 flex-shrink-0 text-rose-400 mt-0.5" />
            <span>{simError}</span>
          </div>
        )}

        {simResult && (
          <div className="mt-4 rounded-lg border border-emerald-800/80 bg-emerald-950/30 p-4 text-xs">
            <div className="flex items-center space-x-2 text-emerald-400 font-semibold mb-2">
              <CheckCircle2 className="h-4 w-4" />
              <span>Routing Decision Resolved</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono">
              <div className="rounded bg-slate-950 p-2.5 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">ASSIGNED TIER</span>
                <span className="text-emerald-300 font-bold">{simResult.assigned_tier}</span>
              </div>
              <div className="rounded bg-slate-950 p-2.5 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">RESOLVED MODEL</span>
                <span className="text-slate-100 font-bold">{simResult.resolved_model}</span>
              </div>
              <div className="rounded bg-slate-950 p-2.5 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">COST TIER</span>
                <span className="text-amber-300 font-bold">{simResult.estimated_cost_tier}</span>
              </div>
            </div>
            <p className="mt-3 text-slate-300 font-mono text-[11px] bg-slate-950/80 p-2.5 rounded border border-slate-800">
              <strong className="text-slate-400">Rationale: </strong>
              {simResult.rationale}
            </p>
          </div>
        )}
      </div>

      {/* Model Catalog & Pricing */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <Layers className="h-4 w-4 text-indigo-400" />
            <h3 className="text-sm font-semibold text-slate-100">Registered Model Catalog</h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">{models.length} Models Active</span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500">Loading model catalog...</div>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Model ID</th>
                <th className="py-2.5 px-3">Family</th>
                <th className="py-2.5 px-3">Routing Tier</th>
                <th className="py-2.5 px-3">Context Window</th>
                <th className="py-2.5 px-3">Input / 1M Tokens</th>
                <th className="py-2.5 px-3">Output / 1M Tokens</th>
                <th className="py-2.5 px-3">Default</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {models.map((m) => (
                <tr key={m.model_id} className="hover:bg-slate-850">
                  <td className="py-2 px-3 text-slate-200 font-semibold">{m.model_id}</td>
                  <td className="py-2 px-3 text-slate-400">{m.family}</td>
                  <td className="py-2 px-3">
                    <StatusBadge status={m.tier} />
                  </td>
                  <td className="py-2 px-3 text-slate-400">
                    {m.max_context_window ? `${(m.max_context_window / 1000).toFixed(0)}k` : '—'}
                  </td>
                  <td className="py-2 px-3 text-slate-300">
                    ${m.input_token_cost_per_million ? m.input_token_cost_per_million.toFixed(2) : '0.00'}
                  </td>
                  <td className="py-2 px-3 text-slate-300">
                    ${m.output_token_cost_per_million ? m.output_token_cost_per_million.toFixed(2) : '0.00'}
                  </td>
                  <td className="py-2 px-3">
                    {m.is_default && (
                      <span className="text-[10px] bg-indigo-950 text-indigo-400 border border-indigo-800 px-1.5 py-0.5 rounded">
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
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
            <Sliders className="h-4 w-4 text-indigo-400" />
            <h3 className="text-sm font-semibold text-slate-100">Role-Based Tiering Policies</h3>
          </div>
          <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 font-mono text-xs">
            {Object.entries(policy.role_defaults).map(([role, tier]) => (
              <div
                key={role}
                className="flex items-center justify-between p-3 rounded-lg bg-slate-950 border border-slate-800"
              >
                <span className="text-slate-300 capitalize">{role.replace(/_/g, ' ')}</span>
                <StatusBadge status={tier} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
