import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { Approval, ApprovalRespondPayload, Artifact } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { Modal } from '../components/ConfirmModal';
import { ArtifactViewerModal } from '../components/ArtifactViewerModal';
import {
  CheckSquare,
  ShieldCheck,
  ShieldX,
  Key,
  AlertCircle,
  FileCheck2,
  Eye,
  ExternalLink,
  Sparkles,
  Copy,
  Check,
  Lock,
} from 'lucide-react';

export const ApprovalsPage: React.FC = () => {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'ALL' | 'PENDING' | 'APPROVED' | 'REJECTED'>('ALL');
  const [copiedDigest, setCopiedDigest] = useState<string | null>(null);

  // Respond Modal State
  const [selectedApproval, setSelectedApproval] = useState<Approval | null>(null);
  const [gateArtifacts, setGateArtifacts] = useState<Artifact[]>([]);
  const [missionApp, setMissionApp] = useState<{ mission_id: string; title: string; html: string; url: string } | null>(null);
  const [previewingApp, setPreviewingApp] = useState(false);
  const [viewingGateArtifact, setViewingGateArtifact] = useState<Artifact | null>(null);
  const [respondData, setRespondData] = useState<ApprovalRespondPayload>({
    decision: 'APPROVED',
    digest: '',
    responder: '',
    comment: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [respondError, setRespondError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const loadApprovals = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getApprovals();
      setApprovals(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load approval requests.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApprovals();
  }, []);

  const openReviewModal = (approval: Approval) => {
    setSelectedApproval(approval);
    setGateArtifacts([]);
    setMissionApp(null);
    setPreviewingApp(false);
    const digest = approval.signature_digest || approval.action_digest || '';
    const userCtx = apiClient.getUserContext();
    setRespondData({
      decision: 'APPROVED',
      digest,
      responder: userCtx.email || userCtx.userId,
      comment: '',
    });
    setRespondError(null);

    // Fetch deliverables and live app for the mission
    if (approval.mission_id) {
      apiClient
        .getMissionArtifacts(approval.mission_id)
        .then((res) => setGateArtifacts(res.items || []))
        .catch(() => setGateArtifacts([]));

      apiClient
        .getMissionApp(approval.mission_id)
        .then((res) => setMissionApp(res))
        .catch(() => setMissionApp(null));
    }
  };

  const handleCopyDigest = (digest: string) => {
    navigator.clipboard.writeText(digest);
    setCopiedDigest(digest);
    setTimeout(() => setCopiedDigest(null), 2000);
  };

  const submitDecision = async (decision: 'APPROVED' | 'REJECTED') => {
    if (!selectedApproval) return;

    try {
      setSubmitting(true);
      setRespondError(null);
      const payload: ApprovalRespondPayload = {
        ...respondData,
        decision,
      };
      await apiClient.respondApproval(selectedApproval.id, payload);
      setActionSuccess(
        `Approval ticket ${selectedApproval.id.slice(0, 8)} successfully ${decision}. Mission state updated to ${
          decision === 'APPROVED' ? 'COMPLETED' : 'REPLANNING'
        }.`
      );
      setSelectedApproval(null);
      await loadApprovals();
    } catch (err: any) {
      setRespondError(err.message || `Failed to submit ${decision.toLowerCase()} decision.`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRespondSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await submitDecision(respondData.decision);
  };

  const filteredApprovals = approvals.filter((a) => {
    if (filter === 'ALL') return true;
    return a.decision === filter;
  });

  return (
    <div className="space-y-6">
      {/* Top Banner - Double-Bezel Hardware Enclosure with HUD Brackets */}
      <div className="double-bezel-outer hud-corner relative overflow-hidden">
        {/* Prismatic Cyan Ambient Glow */}
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-80 h-80 rounded-full bg-cyan-500/15 blur-3xl pointer-events-none" />
        <div className="absolute top-0 left-1/4 right-1/4 h-[1px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-80" />

        <div className="double-bezel-inner p-6 backdrop-blur-2xl">
          <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center space-x-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400/20 via-slate-900 to-cyan-500/10 text-cyan-300 border border-cyan-400/40 shadow-[0_0_20px_rgba(0,240,255,0.3),inset_0_1px_1px_rgba(255,255,255,0.4)]">
                <Lock className="h-6 w-6" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="eyebrow-pill">
                    <Lock className="h-3 w-3 text-cyan-400" />
                    <span>SECURITY CLEARANCE // LEVEL-4 GATE</span>
                  </span>
                </div>
                <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-sans drop-shadow-[0_0_14px_rgba(0,240,255,0.3)] mt-1.5">
                  Cryptographic Human Delivery Gate
                </h2>
                <p className="mt-0.5 text-xs text-slate-300 max-w-2xl font-sans">
                  Governed under Tier-1 security controls: External writes, PR merges, and deployments require HMAC-signed human authorization.
                </p>
              </div>
            </div>

            {/* Filter Pills with Liquid Glass Styling */}
            <div className="flex items-center space-x-1.5 rounded-xl border border-white/[0.08] bg-slate-950/70 p-1 text-xs backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.06)]">
              {(['ALL', 'PENDING', 'APPROVED', 'REJECTED'] as const).map((st) => (
                <button
                  key={st}
                  onClick={() => setFilter(st)}
                  className={`rounded-lg px-3 py-1 font-mono text-[11px] font-bold tracking-wider transition-all duration-200 ${
                    filter === st
                      ? 'bg-gradient-to-r from-cyan-500/30 to-cyan-500/10 text-cyan-300 border border-cyan-400/40 shadow-[0_0_12px_rgba(0,240,255,0.25)]'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {actionSuccess && (
        <div className="liquid-glass-card rounded-xl p-4 text-xs text-emerald-300 flex items-center justify-between border-emerald-400/30 bg-emerald-950/40 shadow-[0_0_20px_rgba(0,255,157,0.15)]">
          <div className="flex items-center space-x-2.5">
            <ShieldCheck className="h-4 w-4 text-emerald-400 flex-shrink-0 shadow-[0_0_8px_#00FF9D]" />
            <span className="font-sans font-medium">{actionSuccess}</span>
          </div>
          <button
            onClick={() => setActionSuccess(null)}
            className="text-emerald-400 hover:text-emerald-200 text-[11px] font-mono font-bold uppercase underline px-2 py-0.5"
          >
            Dismiss
          </button>
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 backdrop-blur-xl shadow-[0_0_20px_rgba(255,0,85,0.2)]">
          <p className="font-semibold font-sans">Error Loading Approvals</p>
          <p className="mt-1 font-mono text-[11px]">{error}</p>
        </div>
      )}

      {/* Approvals Table / Cards */}
      {loading ? (
        <div className="liquid-glass-slab rounded-2xl p-12 text-center text-xs text-slate-400 font-mono tracking-wider">
          <span className="inline-block animate-spin mr-2 text-cyan-400">◓</span>
          RETRIEVING CRYPTOGRAPHIC APPROVAL TICKETS...
        </div>
      ) : filteredApprovals.length === 0 ? (
        <div className="liquid-glass-card rounded-2xl border-dashed border-white/[0.1] p-12 text-center">
          <CheckSquare className="mx-auto h-8 w-8 text-cyan-400/50" />
          <p className="mt-3 text-sm font-bold text-slate-200 font-sans">No approval requests found</p>
          <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto font-sans">
            {filter !== 'ALL'
              ? `No approvals matching filter '${filter}'.`
              : 'All sensitive multi-agent delivery actions require signed human approval tickets.'}
          </p>
        </div>
      ) : (
        <div className="space-y-3.5">
          {filteredApprovals.map((appr) => (
            <div
              key={appr.id}
              className="liquid-glass-card group rounded-2xl p-5 hover:border-cyan-400/40 transition-all duration-200 hover:shadow-[0_0_25px_rgba(0,240,255,0.12),inset_0_1.5px_1.5px_rgba(255,255,255,0.4)]"
            >
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div className="space-y-2.5 flex-1 min-w-0">
                  <div className="flex items-center space-x-2.5">
                    <StatusBadge status={appr.decision} />
                    <span className="font-mono text-xs font-bold text-white tracking-wider">
                      {appr.action_type}
                    </span>
                    <span className="font-mono text-[10px] text-cyan-300 bg-cyan-950/80 px-2 py-0.5 rounded-md border border-cyan-400/30">
                      v{appr.mission_version}
                    </span>
                  </div>

                  <p className="font-mono text-xs text-slate-300">
                    <span className="text-slate-500">Resource: </span>
                    <span className="text-white font-semibold">{appr.target_resource}</span>
                  </p>

                  <div className="flex items-center space-x-2 text-[11px] font-mono text-slate-300 bg-slate-950/70 p-2.5 rounded-xl border border-white/[0.08] max-w-2xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.04)]">
                    <Key className="h-3.5 w-3.5 text-cyan-400 flex-shrink-0" />
                    <span className="text-slate-400">HMAC Digest:</span>
                    <span className="truncate text-cyan-300 flex-1 font-mono">{appr.signature_digest}</span>
                    <button
                      type="button"
                      onClick={() => handleCopyDigest(appr.signature_digest)}
                      className="p-1.5 text-slate-400 hover:text-cyan-300 rounded-lg hover:bg-white/[0.05] transition-colors"
                      title="Copy HMAC Digest"
                    >
                      {copiedDigest === appr.signature_digest ? (
                        <Check className="h-3.5 w-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </div>

                  {appr.comment && (
                    <p className="text-xs text-slate-300 italic font-sans pt-1">
                      &quot;{appr.comment}&quot; — <span className="font-mono text-cyan-300 font-semibold">{appr.responder}</span>
                    </p>
                  )}
                </div>

                <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 flex-shrink-0">
                  <div className="text-[11px] text-slate-400 font-mono text-left sm:text-right space-y-0.5">
                    <div>Expires: <span className="text-slate-200">{new Date(appr.expires_at).toLocaleTimeString()}</span></div>
                    <div className="text-[10px] text-slate-500">ID: {appr.id.slice(0, 8)}</div>
                  </div>

                  {appr.decision === 'PENDING' && (
                    <button
                      onClick={() => openReviewModal(appr)}
                      className="inline-flex items-center space-x-2 rounded-xl bg-gradient-to-r from-cyan-500 to-cyan-600 px-4 py-2.5 text-xs font-mono font-bold text-slate-950 shadow-[0_0_20px_rgba(0,240,255,0.4),inset_0_1px_1px_rgba(255,255,255,0.6)] hover:brightness-110 active:scale-[0.98] transition-all tracking-wider uppercase"
                    >
                      <FileCheck2 className="h-4 w-4 text-slate-950" />
                      <span>Review Gate</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Review & Respond Modal */}
      {selectedApproval && (
        <Modal
          isOpen={!!selectedApproval}
          onClose={() => setSelectedApproval(null)}
          title={`Review Approval Ticket: ${selectedApproval.action_type}`}
          maxWidth={previewingApp ? 'max-w-4xl' : 'max-w-2xl'}
        >
          <form onSubmit={handleRespondSubmit} className="space-y-4">
            {respondError && (
              <div className="flex items-start space-x-2 rounded-xl border border-rose-500/30 bg-rose-950/40 p-3 text-xs text-rose-300">
                <AlertCircle className="h-4 w-4 flex-shrink-0 text-rose-400 mt-0.5" />
                <span>{respondError}</span>
              </div>
            )}

            <div className="rounded-xl bg-slate-950 p-3.5 border border-white/[0.08] space-y-1.5 text-xs font-mono shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
              <div className="text-slate-400">
                Action: <span className="text-slate-200 font-bold">{selectedApproval.action_type}</span>
              </div>
              <div className="text-slate-400">
                Target: <span className="text-slate-200">{selectedApproval.target_resource}</span>
              </div>
              <div className="text-slate-400 truncate">
                Ticket ID: <span className="text-slate-300">{selectedApproval.id}</span>
              </div>
            </div>

            {/* Live Application Deliverable Preview Card */}
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-3.5 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center space-x-2">
                  <Sparkles className="h-4 w-4 text-emerald-400" />
                  <span className="font-semibold text-emerald-300 font-sans">
                    Live Application Deliverable
                  </span>
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    type="button"
                    onClick={() => setPreviewingApp(!previewingApp)}
                    className="inline-flex items-center space-x-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 text-[11px] font-medium transition-colors border border-white/[0.06]"
                  >
                    <span>{previewingApp ? 'Collapse Live Frame' : 'Preview Live App'}</span>
                  </button>
                  <a
                    href={missionApp?.url || (selectedApproval.mission_id ? `/generated_apps/${selectedApproval.mission_id}/index.html` : '/calculator.html')}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center space-x-1 text-[11px] text-emerald-400 hover:text-emerald-300 font-semibold underline"
                    title="Open live built application in new window"
                  >
                    <ExternalLink className="h-3 w-3" />
                    <span>Launch in New Tab</span>
                  </a>
                </div>
              </div>

              {previewingApp && (
                <div className="relative rounded-xl border border-white/[0.08] bg-slate-950 overflow-hidden shadow-inner h-[380px] mt-2">
                  <iframe
                    src={missionApp?.url || (selectedApproval.mission_id ? `/generated_apps/${selectedApproval.mission_id}/index.html` : '/calculator.html')}
                    title="Live Deliverable Preview"
                    className="w-full h-full border-0"
                    sandbox="allow-scripts allow-forms allow-same-origin allow-popups"
                  />
                </div>
              )}
            </div>

            {/* Deliverables Staged for Verification */}
            {gateArtifacts.length > 0 && (
              <div className="rounded-xl border border-white/[0.08] bg-slate-900/50 p-3.5 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-300 font-sans">
                    Deliverables Awaiting Verification ({gateArtifacts.length})
                  </span>
                  <a
                    href={missionApp?.url || (selectedApproval.mission_id ? `/generated_apps/${selectedApproval.mission_id}/index.html` : '/calculator.html')}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center space-x-1 text-[11px] text-emerald-400 hover:text-emerald-300 font-semibold underline"
                    title="Open live built application preview"
                  >
                    <ExternalLink className="h-3 w-3" />
                    <span>Launch Live App</span>
                  </a>
                </div>
                <div className="max-h-36 overflow-y-auto space-y-1.5 pr-1 text-xs">
                  {gateArtifacts.map((art) => (
                    <div
                      key={art.id}
                      className="flex items-center justify-between rounded-lg bg-slate-950 p-2.5 border border-white/[0.06]"
                    >
                      <div className="truncate max-w-[260px]">
                        <span className="font-mono text-slate-200 text-[11px] block truncate">
                          {art.path}
                        </span>
                        <span className="text-[10px] text-cyan-400 font-mono">
                          {art.artifact_type}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setViewingGateArtifact(art)}
                        className="inline-flex items-center space-x-1 rounded-lg bg-cyan-600 hover:bg-cyan-500 px-2.5 py-1 text-[11px] text-white font-medium shadow transition-colors"
                      >
                        <Eye className="h-3 w-3" />
                        <span>Inspect</span>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Role Notice */}
            {apiClient.getUserContext().role !== 'admin' && (
              <div className="flex items-start space-x-2 rounded-xl border border-amber-500/30 bg-amber-950/40 p-3 text-xs text-amber-200 font-sans">
                <AlertCircle className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <span>
                  <strong>Role Warning:</strong> You are operating as{' '}
                  <code className="bg-amber-900/60 px-1 py-0.5 rounded font-mono">
                    {apiClient.getUserContext().role}
                  </code>
                  . Only <code className="bg-amber-900/60 px-1 py-0.5 rounded font-mono">admin</code>{' '}
                  can authorize delivery gates. Switch role to Admin in the top-right header if submission fails.
                </span>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-300">Cryptographic Digest *</label>
              <input
                type="text"
                required
                value={respondData.digest}
                onChange={(e) => setRespondData({ ...respondData, digest: e.target.value })}
                className="mt-1 w-full rounded-xl border border-white/[0.08] bg-slate-900/80 px-3 py-2 font-mono text-xs text-cyan-200 focus:border-cyan-400 focus:outline-none"
              />
              <span className="text-[10px] text-slate-500 mt-1 block">
                Pre-filled HMAC-SHA256 signature binding this ticket to unmodified mission version.
              </span>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300">Authorizing Officer / Responder *</label>
              <input
                type="text"
                required
                value={respondData.responder}
                onChange={(e) => setRespondData({ ...respondData, responder: e.target.value })}
                className="mt-1 w-full rounded-xl border border-white/[0.08] bg-slate-900/80 px-3 py-2 text-xs text-slate-200 focus:border-cyan-400 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300">Audit Justification / Comment</label>
              <textarea
                rows={2}
                placeholder="Reviewed regression test logs and security audit digest. Changes verified."
                value={respondData.comment || ''}
                onChange={(e) => setRespondData({ ...respondData, comment: e.target.value })}
                className="mt-1 w-full rounded-xl border border-white/[0.08] bg-slate-900/80 px-3 py-2 text-xs text-slate-200 focus:border-cyan-400 focus:outline-none"
              />
            </div>

            <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-white/[0.08]">
              <button
                type="button"
                onClick={() => setSelectedApproval(null)}
                className="w-full sm:w-auto rounded-xl border border-white/[0.08] px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800 transition-colors"
              >
                Cancel
              </button>
              <div className="flex items-center space-x-2.5 w-full sm:w-auto justify-end">
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => submitDecision('REJECTED')}
                  className="flex-1 sm:flex-initial inline-flex items-center justify-center space-x-1.5 rounded-xl border border-rose-500/30 bg-rose-950/80 px-4 py-2 text-xs font-medium text-rose-300 hover:bg-rose-900 disabled:opacity-50 transition-colors"
                >
                  <ShieldX className="h-4 w-4 text-rose-400" />
                  <span>Reject Ticket</span>
                </button>
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => submitDecision('APPROVED')}
                  className="flex-1 sm:flex-initial inline-flex items-center justify-center space-x-1.5 rounded-xl bg-emerald-600 px-5 py-2 text-xs font-semibold text-white shadow-layered-sm shadow-emerald-600/25 hover:bg-emerald-500 disabled:opacity-50 transition-colors"
                >
                  <ShieldCheck className="h-4 w-4 text-white" />
                  <span>{submitting ? 'Authorizing...' : 'Authorize & Approve'}</span>
                </button>
              </div>
            </div>
          </form>
        </Modal>
      )}

      {/* Artifact Deliverable Inspector Modal */}
      <ArtifactViewerModal
        artifact={viewingGateArtifact}
        onClose={() => setViewingGateArtifact(null)}
      />
    </div>
  );
};
