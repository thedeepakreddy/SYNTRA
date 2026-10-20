import React from 'react';

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = '' }) => {
  const norm = (status || '').toUpperCase();

  let colorClasses = 'bg-slate-800 text-slate-300 border-slate-700';

  if (['HEALTHY', 'APPROVED', 'COMPLETED', 'PASSED', 'SUCCESS'].includes(norm)) {
    colorClasses = 'bg-emerald-950/80 text-emerald-300 border-emerald-700/60';
  } else if (['PENDING', 'PLANNING', 'PLANNED', 'EXECUTING', 'RUNNING', 'AWAITING_APPROVAL'].includes(norm)) {
    colorClasses = 'bg-amber-950/80 text-amber-300 border-amber-700/60';
  } else if (['FAILED', 'REJECTED', 'UNHEALTHY', 'ERROR', 'CANCELLED'].includes(norm)) {
    colorClasses = 'bg-rose-950/80 text-rose-300 border-rose-700/60';
  } else if (['DEGRADED', 'EXPIRED', 'BLOCKED_BY_POLICY'].includes(norm)) {
    colorClasses = 'bg-purple-950/80 text-purple-300 border-purple-700/60';
  } else if (['FAST', 'BALANCED', 'REASONING'].includes(norm)) {
    colorClasses = 'bg-cyan-950/80 text-cyan-300 border-cyan-700/60';
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono font-medium border ${colorClasses} ${className}`}
      data-testid="status-badge"
    >
      <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current opacity-70" />
      {norm}
    </span>
  );
};
