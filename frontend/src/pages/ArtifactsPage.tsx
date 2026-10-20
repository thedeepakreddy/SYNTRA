import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { Artifact, Mission } from '../types';
import { FileCode2, Copy, Check, Hash } from 'lucide-react';

export const ArtifactsPage: React.FC = () => {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [missions, setMissions] = useState<Mission[]>([]);
  const [selectedMissionId, setSelectedMissionId] = useState<string>('ALL');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const mis = await apiClient.getMissions();
      setMissions(mis);

      // Collect artifacts from all missions
      const allArtifacts: Artifact[] = [];
      for (const m of mis.slice(0, 10)) {
        try {
          const res = await apiClient.getMissionArtifacts(m.id);
          if (res.items) {
            allArtifacts.push(...res.items);
          }
        } catch {
          // ignore individual fetch errors
        }
      }
      setArtifacts(allArtifacts);
    } catch (err: any) {
      setError(err.message || 'Failed to load artifacts.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCopy = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const filteredArtifacts = artifacts.filter((a) => {
    if (selectedMissionId === 'ALL') return true;
    return a.mission_id === selectedMissionId;
  });

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow">
        <div className="flex items-center space-x-3">
          <div className="rounded-lg bg-indigo-600/20 p-2 text-indigo-400 border border-indigo-500/30">
            <FileCode2 className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight text-white">
              Immutable Artifact Handoffs & Unified Diffs
            </h2>
            <p className="mt-1 text-xs text-slate-400 max-w-3xl">
              All agent deliverables (PRDs, architecture specifications, task DAGs, unified diffs, and verification reports)
              are content-addressed and cryptographically hashed with SHA-256.
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-800 bg-rose-950/40 p-4 text-xs text-rose-300">
          <p className="font-semibold">Error Loading Artifacts</p>
          <p className="mt-1 font-mono">{error}</p>
        </div>
      )}

      {/* Filter by Mission */}
      {missions.length > 0 && (
        <div className="flex items-center space-x-3">
          <span className="text-xs text-slate-400 font-medium">Filter by Mission:</span>
          <select
            value={selectedMissionId}
            onChange={(e) => setSelectedMissionId(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
          >
            <option value="ALL">All Missions ({artifacts.length} artifacts)</option>
            {missions.map((m) => (
              <option key={m.id} value={m.id}>
                Mission {m.id.slice(0, 8)}...
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Artifacts List */}
      {loading ? (
        <div className="p-8 text-center text-xs text-slate-500">Loading artifacts...</div>
      ) : filteredArtifacts.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-800 p-8 text-center">
          <FileCode2 className="mx-auto h-8 w-8 text-slate-600" />
          <p className="mt-2 text-sm font-medium text-slate-300">No artifacts found</p>
          <p className="text-xs text-slate-500 mt-1">
            Artifacts will be cataloged as agents execute tasks and generate specification diffs.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredArtifacts.map((art) => (
            <div
              key={art.id}
              className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow space-y-3 font-mono text-xs"
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="font-semibold text-slate-200 text-sm">{art.artifact_type}</span>
                  <p className="text-[11px] text-slate-400 mt-0.5 truncate max-w-sm">{art.path}</p>
                </div>
                <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded">
                  {art.size_bytes ? `${art.size_bytes} B` : '< 1 KB'}
                </span>
              </div>

              {art.content_hash && (
                <div className="rounded bg-slate-950 p-2.5 border border-slate-800 flex items-center justify-between text-[11px]">
                  <div className="flex items-center space-x-1.5 truncate text-slate-400">
                    <Hash className="h-3.5 w-3.5 text-indigo-400 flex-shrink-0" />
                    <span className="truncate">{art.content_hash}</span>
                  </div>
                  <button
                    onClick={() => handleCopy(art.content_hash)}
                    className="p-1 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800"
                    title="Copy SHA-256 Digest"
                  >
                    {copiedHash === art.content_hash ? (
                      <Check className="h-3.5 w-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )}
                  </button>
                </div>
              )}

              <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[10px] text-slate-500">
                <span>Mission: {art.mission_id.slice(0, 8)}...</span>
                <span>{new Date(art.created_at).toLocaleTimeString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
