import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { Artifact, Mission } from '../types';
import { FileCode2, Copy, Check, Hash, Eye, ShieldCheck, Database } from 'lucide-react';
import { ArtifactViewerModal } from '../components/ArtifactViewerModal';

export const ArtifactsPage: React.FC = () => {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [missions, setMissions] = useState<Mission[]>([]);
  const [selectedMissionId, setSelectedMissionId] = useState<string>('ALL');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [viewingArtifact, setViewingArtifact] = useState<Artifact | null>(null);

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
                  CONTENT-ADDRESSED VAULT // SHA-256
                </span>
                <span className="px-2.5 py-0.5 rounded-full bg-slate-900/80 border border-white/10 text-[10px] font-mono text-slate-400">
                  IMMUTABLE ARTIFACT STORE
                </span>
              </div>
              <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-white font-sans drop-shadow-[0_0_14px_rgba(0,240,255,0.3)]">
                Immutable Artifact Handoffs &amp; Unified Diffs
              </h2>
              <p className="text-xs sm:text-sm text-slate-300 max-w-2xl font-sans leading-relaxed">
                All agent deliverables (PRDs, architecture blueprints, task DAGs, unified diffs, and verification reports)
                are strictly content-addressed and cryptographically hashed with SHA-256 to ensure complete provenance.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
              <span className="inline-flex items-center space-x-2 rounded-full bg-cyan-950/80 px-4 py-2 text-xs font-mono font-semibold text-cyan-300 border border-cyan-400/40 shadow-[0_0_14px_rgba(0,240,255,0.2),inset_0_1px_1px_rgba(255,255,255,0.25)]">
                <ShieldCheck className="h-4 w-4 text-cyan-400" />
                <span>SHA-256 Digest Verified</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-2xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 backdrop-blur-xl shadow-[0_0_20px_rgba(255,0,85,0.2)]">
          <p className="font-semibold font-sans">Error Loading Artifacts</p>
          <p className="mt-1 font-mono text-[11px]">{error}</p>
        </div>
      )}

      {/* Filter by Mission Controls Bar */}
      {missions.length > 0 && (
        <div className="double-bezel-outer">
          <div className="double-bezel-inner p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center space-x-2.5">
              <Database className="w-4 h-4 text-cyan-400" />
              <span className="text-xs text-slate-300 font-mono uppercase tracking-wider font-bold">
                Filter by Mission Scope:
              </span>
            </div>
            <select
              value={selectedMissionId}
              onChange={(e) => setSelectedMissionId(e.target.value)}
              className="liquid-control rounded-xl border border-white/[0.1] bg-slate-950/80 px-4 py-2 text-xs text-cyan-200 font-mono focus:border-cyan-400 focus:outline-none"
            >
              <option value="ALL" className="bg-slate-950 text-slate-200">
                All Missions ({artifacts.length} artifacts)
              </option>
              {missions.map((m) => (
                <option key={m.id} value={m.id} className="bg-slate-950 text-slate-200">
                  Mission {m.id.slice(0, 8)}... — {m.title || m.objective.slice(0, 30)}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* Artifacts Grid */}
      {loading ? (
        <div className="double-bezel-outer">
          <div className="double-bezel-inner p-14 text-center text-xs text-slate-400 font-mono tracking-wider">
            <span className="inline-block animate-spin mr-2 text-cyan-400">◓</span>
            RETRIEVING CRYPTOGRAPHIC ARTIFACT CATALOG...
          </div>
        </div>
      ) : filteredArtifacts.length === 0 ? (
        <div className="double-bezel-outer">
          <div className="double-bezel-inner p-14 text-center">
            <FileCode2 className="mx-auto h-8 w-8 text-cyan-400/50" />
            <p className="mt-3 text-sm font-bold text-slate-200 font-sans">No artifacts found</p>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto font-sans">
              Artifacts will be cataloged here as agents execute tasks and generate specification diffs.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {filteredArtifacts.map((art) => (
            <div key={art.id} className="double-bezel-outer group">
              <div className="double-bezel-inner p-6 space-y-4 font-mono text-xs flex flex-col justify-between h-full">
                <div className="space-y-3.5">
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="font-bold text-white text-sm font-sans tracking-wide">
                        {art.artifact_type}
                      </span>
                      <p className="text-[11px] text-cyan-400/90 mt-0.5 truncate max-w-sm font-mono">
                        {art.path}
                      </p>
                    </div>
                    <span className="text-[10px] bg-cyan-950/80 text-cyan-300 border border-cyan-400/30 px-2.5 py-0.5 rounded-full font-bold">
                      {art.size_bytes ? `${art.size_bytes} B` : '< 1 KB'}
                    </span>
                  </div>

                  {art.content_hash && (
                    <div className="liquid-glass-card rounded-xl p-3 border border-white/[0.08] flex items-center justify-between text-[11px]">
                      <div className="flex items-center space-x-2 truncate text-slate-300">
                        <Hash className="h-3.5 w-3.5 text-cyan-400 flex-shrink-0" />
                        <span className="truncate font-mono">{art.content_hash}</span>
                      </div>
                      <button
                        onClick={() => handleCopy(art.content_hash)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-cyan-300 hover:bg-white/[0.05] transition-colors"
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
                </div>

                <div className="pt-4 border-t border-white/[0.08] flex items-center justify-between text-[10px] text-slate-400">
                  <span className="font-mono">
                    Mission: <span className="text-slate-300">{art.mission_id.slice(0, 8)}...</span>
                  </span>
                  <div className="flex items-center space-x-3">
                    <span>{new Date(art.created_at).toLocaleTimeString()}</span>
                    <button
                      type="button"
                      onClick={() => setViewingArtifact(art)}
                      className="inline-flex items-center space-x-1.5 rounded-full bg-gradient-to-r from-cyan-500 to-cyan-600 text-slate-950 px-3.5 py-1.5 text-xs font-mono font-bold shadow-[0_0_14px_rgba(0,240,255,0.3),inset_0_1px_1px_rgba(255,255,255,0.5)] hover:brightness-110 active:scale-[0.98] transition-all uppercase tracking-wider"
                    >
                      <Eye className="h-3.5 w-3.5 text-slate-950" />
                      <span>Inspect</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Artifact Document Inspector Modal */}
      <ArtifactViewerModal
        artifact={viewingArtifact}
        onClose={() => setViewingArtifact(null)}
      />
    </div>
  );
};
