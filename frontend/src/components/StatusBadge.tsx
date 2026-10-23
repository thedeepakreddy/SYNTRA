import React from 'react';

interface StatusBadgeProps {
  status: string;
  className?: string;
  pulse?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = '', pulse }) => {
  const norm = (status || '').toUpperCase();

  let colorClasses = 'bg-slate-900/80 text-slate-300 border-white/10 shadow-[inset_0_1px_1px_rgba(255,255,255,0.2)]';
  let dotColor = 'bg-slate-400';
  let shouldPulse = pulse ?? false;

  if (['HEALTHY', 'APPROVED', 'COMPLETED', 'PASSED', 'SUCCESS'].includes(norm)) {
    colorClasses = 'bg-emerald-950/50 text-emerald-300 border-emerald-400/40 shadow-[inset_0_1px_1px_rgba(255,255,255,0.3),0_0_12px_rgba(0,255,157,0.2)]';
    dotColor = 'bg-emerald-400 shadow-[0_0_8px_#00FF9D]';
  } else if (['PENDING', 'PLANNING', 'PLANNED', 'EXECUTING', 'RUNNING', 'AWAITING_APPROVAL'].includes(norm)) {
    colorClasses = 'bg-amber-950/50 text-amber-300 border-amber-400/40 shadow-[inset_0_1px_1px_rgba(255,255,255,0.3),0_0_12px_rgba(255,184,0,0.2)]';
    dotColor = 'bg-amber-400 shadow-[0_0_8px_#FFB800]';
    shouldPulse = pulse !== false; // pulse by default for in-progress states
  } else if (['FAILED', 'REJECTED', 'UNHEALTHY', 'ERROR', 'CANCELLED'].includes(norm)) {
    colorClasses = 'bg-rose-950/50 text-rose-300 border-rose-500/40 shadow-[inset_0_1px_1px_rgba(255,255,255,0.3),0_0_12px_rgba(255,0,85,0.25)]';
    dotColor = 'bg-rose-400 shadow-[0_0_8px_#FF0055]';
  } else if (['DEGRADED', 'EXPIRED', 'BLOCKED_BY_POLICY'].includes(norm)) {
    colorClasses = 'bg-orange-950/50 text-orange-300 border-orange-500/40 shadow-[inset_0_1px_1px_rgba(255,255,255,0.3),0_0_12px_rgba(249,115,22,0.2)]';
    dotColor = 'bg-orange-400 shadow-[0_0_8px_#F97316]';
  } else if (['FAST', 'BALANCED', 'REASONING'].includes(norm)) {
    // Cyberpunk Model Routing Tiers
    if (norm === 'FAST') {
      colorClasses = 'bg-cyan-950/50 text-cyan-300 border-cyan-400/40 shadow-[inset_0_1px_1px_rgba(255,255,255,0.3),0_0_12px_rgba(0,240,255,0.25)]';
      dotColor = 'bg-cyan-400 shadow-[0_0_8px_#00F0FF]';
    } else if (norm === 'BALANCED') {
      colorClasses = 'bg-teal-950/50 text-teal-300 border-teal-400/40 shadow-[inset_0_1px_1px_rgba(255,255,255,0.3),0_0_12px_rgba(20,184,166,0.25)]';
      dotColor = 'bg-teal-400 shadow-[0_0_8px_#14B8A6]';
    } else {
      colorClasses = 'bg-sky-950/50 text-sky-300 border-sky-400/40 shadow-[inset_0_1px_1px_rgba(255,255,255,0.3),0_0_12px_rgba(56,189,248,0.25)]';
      dotColor = 'bg-sky-400 shadow-[0_0_8px_#38BDF8]';
    }
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-mono tracking-wider font-semibold border backdrop-blur-md transition-all duration-200 ${colorClasses} ${className}`}
      data-testid="status-badge"
    >
      <span className="relative flex h-1.5 w-1.5 mr-1.5">
        {shouldPulse && (
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${dotColor}`} />
        )}
        <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${dotColor}`} />
      </span>
      {norm}
    </span>
  );
};
