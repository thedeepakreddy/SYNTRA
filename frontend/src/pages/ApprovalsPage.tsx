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
} from 'lucide-react';

export const ApprovalsPage: React.FC = () => {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'ALL' | 'PENDING' | 'APPROVED' | 'REJECTED'>('ALL');

  // Respond Modal State
  const [selectedApproval, setSelectedApproval] = useState<Approval | null>(null);
  const [gateArtifacts, setGateArtifacts] = useState<Artifact[]>([]);
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
    const digest = approval.signature_digest || approval.action_digest || '';
    const userCtx = apiClient.getUserContext();
    setRespondData({
      decision: 'APPROVED',
      digest,
      responder: userCtx.email || userCtx.userId,
      comment: '',
    });
    setRespondError(null);

    // Fetch deliverables for the mission
    if (approval.mission_id) {
      apiClient
        .getMissionArtifacts(approval.mission_id)
        .then((res) => setGateArtifacts(res.items || []))
        .catch(() => setGateArtifacts([]));
    }
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
      {/* Header & Description */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">
            Cryptographic Human Delivery Gate
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Governed under Tier-1 security controls: External writes, PR merges, and deployments require HMAC-signed human authorization.
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center space-x-1 rounded-lg border border-slate-800 bg-slate-900 p-1 text-xs">
          {(['ALL', 'PENDING', 'APPROVED', 'REJECTED'] as const).map((st) => (
            <button
              key={st}
              onClick={() => setFilter(st)}
              className={`rounded px-3 py-1 font-medium transition-colors ${
                filter === st ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {actionSuccess && (
        <div className="rounded-lg border border-emerald-800 bg-emerald-950/40 p-3 text-xs text-emerald-300 flex items-center justify-between">
          <span>{actionSuccess}</span>
          <button onClick={() => setActionSuccess(null)} className="text-emerald-400 hover:text-emerald-200">
            Dismiss
          </button>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-rose-800 bg-rose-950/40 p-4 text-xs text-rose-300">
          <p className="font-semibold">Error Loading Approvals</p>
          <p className="mt-1 font-mono">{error}</p>
        </div>
      )}

      {/* Approvals Table / Cards */}
      {loading ? (
        <div className="p-8 text-center text-xs text-slate-500">Loading approval requests...</div>
      ) : filteredApprovals.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-800 p-8 text-center">
          <CheckSquare className="mx-auto h-8 w-8 text-slate-600" />
          <p className="mt-2 text-sm font-medium text-slate-300">No approval requests found</p>
          <p className="text-xs text-slate-500 mt-1">
            {filter !== 'ALL'
              ? `No approvals matching filter '${filter}'.`
              : 'All sensitive multi-agent delivery actions require approval tickets.'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredApprovals.map((appr) => (
            <div
              key={appr.id}
              className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow hover:border-slate-700 transition-colors"
            >
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center space-x-2">
                    <StatusBadge status={appr.decision} />
                    <span className="font-mono text-xs font-semibold text-slate-200">
                      {appr.action_type}
                    </span>
                    <span className="font-mono text-[10px] text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded">
                      v{appr.mission_version}
                    </span>
                  </div>

                  <p className="font-mono text-xs text-slate-300">
                    <span className="text-slate-500">Resource: </span>
                    {appr.target_resource}
                  </p>

                  <div className="flex items-center space-x-1.5 text-[11px] font-mono text-slate-500 truncate max-w-xl">
                    <Key className="h-3 w-3 text-slate-400 flex-shrink-0" />
                    <span className="text-slate-400">HMAC Digest:</span>
                    <span className="truncate text-slate-400">{appr.signature_digest}</span>
                  </div>

                  {appr.comment && (
                    <p className="text-xs text-slate-400 italic">
                      &quot;{appr.comment}&quot; — <span className="font-mono">{appr.responder}</span>
                    </p>
                  )}
                </div>

                <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
                  <div className="text-[11px] text-slate-500 font-mono text-right">
                    <div>Expires: {new Date(appr.expires_at).toLocaleTimeString()}</div>
                    <div className="text-[10px] text-slate-600">ID: {appr.id.slice(0, 8)}</div>
                  </div>

                  {appr.decision === 'PENDING' && (
                    <button
                      onClick={() => openReviewModal(appr)}
                      className="inline-flex items-center space-x-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-medium text-white shadow hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                    >
                      <FileCheck2 className="h-4 w-4" />
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
        >
          <form onSubmit={handleRespondSubmit} className="space-y-4">
            {respondError && (
              <div className="flex items-start space-x-2 rounded-lg border border-rose-800 bg-rose-950/40 p-3 text-xs text-rose-300">
                <AlertCircle className="h-4 w-4 flex-shrink-0 text-rose-400 mt-0.5" />
                <span>{respondError}</span>
              </div>
            )}

            <div className="rounded-lg bg-slate-950 p-3 border border-slate-800 space-y-1.5 text-xs font-mono">
              <div className="text-slate-400">
                Action: <span className="text-slate-200">{selectedApproval.action_type}</span>
              </div>
              <div className="text-slate-400">
                Target: <span className="text-slate-200">{selectedApproval.target_resource}</span>
              </div>
              <div className="text-slate-400 truncate">
                Ticket ID: <span className="text-slate-300">{selectedApproval.id}</span>
              </div>
            </div>

            {/* Deliverables Staged for Verification */}
            {gateArtifacts.length > 0 && (
              <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-300">
                    Deliverables Awaiting Verification ({gateArtifacts.length})
                  </span>
                  <a
                    href="/calculator.html"
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
                      className="flex items-center justify-between rounded bg-slate-950 p-2 border border-slate-800/80"
                    >
                      <div className="truncate max-w-[260px]">
                        <span className="font-mono text-slate-200 text-[11px] block truncate">
                          {art.path}
                        </span>
                        <span className="text-[10px] text-indigo-400 font-mono">
                          {art.artifact_type}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setViewingGateArtifact(art)}
                        className="inline-flex items-center space-x-1 rounded bg-indigo-600/90 hover:bg-indigo-600 px-2 py-0.5 text-[11px] text-white font-medium shadow"
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
              <div className="flex items-start space-x-2 rounded-lg border border-amber-600/50 bg-amber-950/40 p-3 text-xs text-amber-200">
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
                className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
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
                className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300">Audit Justification / Comment</label>
              <textarea
                rows={2}
                placeholder="Reviewed regression test logs and security audit digest. Changes verified."
                value={respondData.comment || ''}
                onChange={(e) => setRespondData({ ...respondData, comment: e.target.value })}
                className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setSelectedApproval(null)}
                className="w-full sm:w-auto rounded-lg border border-slate-700 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800"
              >
                Cancel
              </button>
              <div className="flex items-center space-x-2 w-full sm:w-auto justify-end">
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => submitDecision('REJECTED')}
                  className="flex-1 sm:flex-initial inline-flex items-center justify-center space-x-1.5 rounded-lg border border-rose-800 bg-rose-950/80 px-4 py-2 text-xs font-medium text-rose-300 hover:bg-rose-900 disabled:opacity-50"
                >
                  <ShieldX className="h-4 w-4 text-rose-400" />
                  <span>Reject Ticket</span>
                </button>
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => submitDecision('APPROVED')}
                  className="flex-1 sm:flex-initial inline-flex items-center justify-center space-x-1.5 rounded-lg bg-emerald-600 px-5 py-2 text-xs font-semibold text-white shadow-lg hover:bg-emerald-500 disabled:opacity-50"
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
