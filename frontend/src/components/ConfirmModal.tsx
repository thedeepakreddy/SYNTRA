import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  maxWidth?: string;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, maxWidth = 'max-w-lg' }) => {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md overscroll-contain animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      {/* Double-Bezel Architecture */}
      <div
        ref={modalRef}
        className={`w-full ${maxWidth} max-h-[94vh] flex flex-col rounded-3xl p-1 bg-gradient-to-b from-white/[0.16] via-white/[0.06] to-white/[0.02] shadow-[0_25px_70px_rgba(0,0,0,0.9),0_0_0_1px_rgba(0,240,255,0.12)] transition-all transform duration-200`}
      >
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden rounded-[calc(1.5rem-4px)] bg-[#070C18]/95 p-6 backdrop-blur-2xl text-slate-200 shadow-[inset_0_1.5px_2px_rgba(255,255,255,0.2),inset_0_-1px_1px_rgba(0,240,255,0.08)]">
          <div className="flex items-center justify-between pb-4 border-b border-white/[0.08] flex-shrink-0">
            <h2 id="modal-title" className="text-sm font-bold text-white tracking-tight font-sans drop-shadow-[0_0_8px_rgba(0,240,255,0.3)]">
              {title}
            </h2>
            <button
              onClick={onClose}
              className="rounded-full p-1.5 text-slate-400 hover:bg-white/[0.08] hover:text-white transition-colors duration-150 active:scale-[0.95] border border-transparent hover:border-white/[0.1]"
              aria-label="Close dialog"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="mt-4 flex-1 overflow-y-auto pr-1">{children}</div>
        </div>
      </div>
    </div>
  );
};
