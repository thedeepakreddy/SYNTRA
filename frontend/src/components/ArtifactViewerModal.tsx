import React, { useState } from 'react';
import { Artifact } from '../types';
import { Modal } from './ConfirmModal';
import { Copy, Check, Download, Hash } from 'lucide-react';

interface ArtifactViewerModalProps {
  artifact: Artifact | null;
  onClose: () => void;
}

export const ArtifactViewerModal: React.FC<ArtifactViewerModalProps> = ({ artifact, onClose }) => {
  const [copied, setCopied] = useState(false);
  const [copiedHash, setCopiedHash] = useState(false);

  if (!artifact) return null;

  // Resolve content: either already decoded in artifact.content, or base64 decode if path starts with inline:
  let content = artifact.content || '';
  if (!content && artifact.path && artifact.path.startsWith('inline:')) {
    try {
      const b64 = artifact.path.replace('inline:', '');
      content = decodeURIComponent(escape(atob(b64)));
    } catch {
      try {
        content = atob(artifact.path.replace('inline:', ''));
      } catch (err) {
        content = `[Unable to decode inline content: ${err}]`;
      }
    }
  }

  const handleCopyContent = () => {
    if (!content) return;
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCopyHash = () => {
    if (!artifact.content_hash) return;
    navigator.clipboard.writeText(artifact.content_hash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  const handleDownload = () => {
    if (!content) return;
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = artifact.path || `${artifact.artifact_type}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <Modal
      isOpen={!!artifact}
      onClose={onClose}
      title={`Artifact Inspector: ${artifact.path || artifact.artifact_type}`}
    >
      <div className="space-y-4">
        {/* Metadata Banner */}
        <div className="rounded-lg bg-slate-950 p-3.5 border border-slate-800 space-y-2 text-xs font-mono">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.5 rounded text-[10px] bg-indigo-950/80 text-indigo-300 border border-indigo-700/50">
                {artifact.artifact_type}
              </span>
              <span className="text-slate-400">
                {artifact.size_bytes ? `${artifact.size_bytes} bytes` : `${content.length} bytes`}
              </span>
            </div>
            <span className="text-slate-500">
              {new Date(artifact.created_at).toLocaleString()}
            </span>
          </div>

          {artifact.content_hash && (
            <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-800/80">
              <div className="flex items-center space-x-1.5 truncate max-w-md">
                <Hash className="h-3.5 w-3.5 text-indigo-400 flex-shrink-0" />
                <span className="truncate">{artifact.content_hash}</span>
              </div>
              <button
                type="button"
                onClick={handleCopyHash}
                className="p-1 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800"
                title="Copy SHA-256 Digest"
              >
                {copiedHash ? (
                  <Check className="h-3.5 w-3.5 text-emerald-400" />
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )}
              </button>
            </div>
          )}
        </div>

        {/* Content Viewer */}
        <div className="relative rounded-lg border border-slate-800 bg-slate-950/90 p-4">
          <div className="absolute top-2.5 right-2.5 flex items-center space-x-1.5 z-10">
            <button
              type="button"
              onClick={handleCopyContent}
              className="inline-flex items-center space-x-1 rounded bg-slate-800/90 hover:bg-slate-700 px-2.5 py-1 text-[11px] font-medium text-slate-200 border border-slate-700 shadow"
            >
              {copied ? (
                <>
                  <Check className="h-3.5 w-3.5 text-emerald-400" />
                  <span className="text-emerald-400">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5 text-slate-400" />
                  <span>Copy Document</span>
                </>
              )}
            </button>
            <button
              type="button"
              onClick={handleDownload}
              className="inline-flex items-center space-x-1 rounded bg-slate-800/90 hover:bg-slate-700 px-2.5 py-1 text-[11px] font-medium text-slate-200 border border-slate-700 shadow"
              title="Download file"
            >
              <Download className="h-3.5 w-3.5 text-slate-400" />
              <span>Download</span>
            </button>
          </div>

          <div className="max-h-[500px] overflow-y-auto pr-2 mt-6">
            {content ? (
              <pre className="font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed select-text">
                {content}
              </pre>
            ) : (
              <div className="p-8 text-center text-xs text-slate-500 font-mono">
                [No textual content stored for this artifact]
              </div>
            )}
          </div>
        </div>

        {/* Modal Actions */}
        <div className="flex justify-end pt-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800"
          >
            Close Viewer
          </button>
        </div>
      </div>
    </Modal>
  );
};
