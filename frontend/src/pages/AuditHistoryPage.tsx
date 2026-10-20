import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { AuditRecord } from '../types';
import { History, Search, ChevronDown, ChevronRight } from 'lucide-react';

export const AuditHistoryPage: React.FC = () => {
  const [records, setRecords] = useState<AuditRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [eventTypeFilter, setEventTypeFilter] = useState('ALL');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const loadAuditRecords = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getAuditRecords(100);
      setRecords(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load audit history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAuditRecords();
  }, []);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const filteredRecords = records.filter((r) => {
    const matchesSearch =
      r.event_type.toLowerCase().includes(search.toLowerCase()) ||
      r.event_id.toLowerCase().includes(search.toLowerCase()) ||
      (r.mission_id && r.mission_id.toLowerCase().includes(search.toLowerCase())) ||
      JSON.stringify(r.payload).toLowerCase().includes(search.toLowerCase());
    const matchesType = eventTypeFilter === 'ALL' || r.event_type === eventTypeFilter;
    return matchesSearch && matchesType;
  });

  const uniqueEventTypes = Array.from(new Set(records.map((r) => r.event_type)));

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow">
        <div className="flex items-center space-x-3">
          <div className="rounded-lg bg-indigo-600/20 p-2 text-indigo-400 border border-indigo-500/30">
            <History className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight text-white">
              Immutable & Tamper-Evident Audit Trail
            </h2>
            <p className="mt-1 text-xs text-slate-400 max-w-3xl">
              Append-only audit trail recording every state change, agent invocation, unified diff generation,
              and human delivery gate authorization.
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-800 bg-rose-950/40 p-4 text-xs text-rose-300">
          <p className="font-semibold">Error Loading Audit Records</p>
          <p className="mt-1 font-mono">{error}</p>
        </div>
      )}

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
        <div className="relative max-w-md w-full">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search audit trail by event type, ID, payload..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-slate-800 bg-slate-900 py-2 pl-9 pr-4 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
          />
        </div>

        <div className="flex items-center space-x-2">
          <select
            value={eventTypeFilter}
            onChange={(e) => setEventTypeFilter(e.target.value)}
            className="rounded-lg border border-slate-800 bg-slate-900 py-2 px-3 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
          >
            <option value="ALL">All Event Types ({records.length})</option>
            {uniqueEventTypes.map((et) => (
              <option key={et} value={et}>
                {et}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Records Feed */}
      <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 font-mono text-xs shadow-2xl">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-slate-400">
          <span className="text-[11px] font-semibold">Authoritative Event History</span>
          <span className="text-[10px] text-slate-500">{filteredRecords.length} records</span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-500">Loading audit records...</div>
        ) : filteredRecords.length === 0 ? (
          <div className="p-8 text-center text-slate-500">No audit records match your filters.</div>
        ) : (
          <div className="divide-y divide-slate-800/80">
            {filteredRecords.map((rec) => {
              const isExpanded = expandedId === rec.event_id;
              return (
                <div key={rec.event_id} className="py-2.5 hover:bg-slate-900/60 transition-colors">
                  <div
                    onClick={() => toggleExpand(rec.event_id)}
                    className="flex items-start justify-between cursor-pointer space-x-3"
                  >
                    <div className="flex items-center space-x-2">
                      {isExpanded ? (
                        <ChevronDown className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
                      ) : (
                        <ChevronRight className="h-3.5 w-3.5 text-slate-500 flex-shrink-0" />
                      )}
                      <span className="font-bold text-slate-200">{rec.event_type}</span>
                      {rec.agent_role && (
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-cyan-300">
                          {rec.agent_role}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center space-x-3 text-slate-500 text-[10px]">
                      {rec.mission_id && (
                        <span className="hidden sm:inline">M: {rec.mission_id.slice(0, 8)}</span>
                      )}
                      <span>{new Date(rec.timestamp).toLocaleTimeString()}</span>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="mt-2.5 pl-6 pr-2">
                      <div className="rounded border border-slate-800 bg-slate-900 p-3 text-[11px] text-slate-300">
                        <div className="mb-2 text-[10px] text-slate-500 flex items-center justify-between">
                          <span>Event ID: {rec.event_id}</span>
                          <span>Timestamp: {rec.timestamp}</span>
                        </div>
                        <pre className="overflow-x-auto text-[10px] text-emerald-300">
                          {JSON.stringify(rec.payload, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
