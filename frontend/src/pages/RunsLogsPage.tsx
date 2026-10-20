import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { AuditRecord, Mission } from '../types';
import { Terminal, Search, ChevronDown, ChevronRight } from 'lucide-react';

export const RunsLogsPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditRecord[]>([]);
  const [missions, setMissions] = useState<Mission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [eventTypeFilter, setEventTypeFilter] = useState('ALL');
  const [selectedMissionId, setSelectedMissionId] = useState('ALL');
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [auditRecords, missionsList] = await Promise.all([
        apiClient.getAuditRecords(100),
        apiClient.getMissions(),
      ]);
      setLogs(auditRecords);
      setMissions(missionsList);
    } catch (err: any) {
      setError(err.message || 'Failed to load execution runs & logs.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const toggleExpand = (id: string) => {
    setExpandedLogId(expandedLogId === id ? null : id);
  };

  const filteredLogs = logs.filter((log) => {
    const matchesSearch =
      log.event_type.toLowerCase().includes(search.toLowerCase()) ||
      (log.agent_role && log.agent_role.toLowerCase().includes(search.toLowerCase())) ||
      (log.mission_id && log.mission_id.toLowerCase().includes(search.toLowerCase())) ||
      JSON.stringify(log.payload).toLowerCase().includes(search.toLowerCase());

    const matchesType = eventTypeFilter === 'ALL' || log.event_type === eventTypeFilter;
    const matchesMission = selectedMissionId === 'ALL' || log.mission_id === selectedMissionId;

    return matchesSearch && matchesType && matchesMission;
  });

  const uniqueEventTypes = Array.from(new Set(logs.map((l) => l.event_type)));

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow">
        <div className="flex items-center space-x-3">
          <div className="rounded-lg bg-cyan-600/20 p-2 text-cyan-400 border border-cyan-500/30">
            <Terminal className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight text-white">
              Execution Runs & Structured Telemetry Logs
            </h2>
            <p className="mt-1 text-xs text-slate-400 max-w-3xl">
              Chronological telemetry stream with scrubbed credentials, W3C trace IDs, and immutable
              execution records from worker sandboxes.
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-800 bg-rose-950/40 p-4 text-xs text-rose-300">
          <p className="font-semibold">Error Loading Telemetry</p>
          <p className="mt-1 font-mono">{error}</p>
        </div>
      )}

      {/* Filter Controls */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search logs by keyword, role, ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-slate-800 bg-slate-900 py-2 pl-9 pr-4 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
          />
        </div>

        <div>
          <select
            value={eventTypeFilter}
            onChange={(e) => setEventTypeFilter(e.target.value)}
            className="w-full rounded-lg border border-slate-800 bg-slate-900 py-2 px-3 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
          >
            <option value="ALL">All Event Types</option>
            {uniqueEventTypes.map((et) => (
              <option key={et} value={et}>
                {et}
              </option>
            ))}
          </select>
        </div>

        <div>
          <select
            value={selectedMissionId}
            onChange={(e) => setSelectedMissionId(e.target.value)}
            className="w-full rounded-lg border border-slate-800 bg-slate-900 py-2 px-3 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
          >
            <option value="ALL">All Missions</option>
            {missions.map((m) => (
              <option key={m.id} value={m.id}>
                Mission {m.id.slice(0, 8)}...
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Log Feed */}
      <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 font-mono text-xs shadow-2xl">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-slate-400">
          <span className="text-[11px] font-semibold">Structured Event Feed</span>
          <span className="text-[10px] text-slate-500">{filteredLogs.length} events matching</span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-500">Loading telemetry stream...</div>
        ) : filteredLogs.length === 0 ? (
          <div className="p-8 text-center text-slate-500">No logs found matching your filters.</div>
        ) : (
          <div className="divide-y divide-slate-800/80">
            {filteredLogs.map((log) => {
              const isExpanded = expandedLogId === log.event_id;
              return (
                <div key={log.event_id} className="py-2.5 hover:bg-slate-900/60 transition-colors">
                  <div
                    onClick={() => toggleExpand(log.event_id)}
                    className="flex items-start justify-between cursor-pointer space-x-3"
                  >
                    <div className="flex items-center space-x-2">
                      {isExpanded ? (
                        <ChevronDown className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
                      ) : (
                        <ChevronRight className="h-3.5 w-3.5 text-slate-500 flex-shrink-0" />
                      )}
                      <span className="font-bold text-indigo-400">{log.event_type}</span>
                      {log.agent_role && (
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-cyan-300">
                          {log.agent_role}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center space-x-3 text-slate-500 text-[10px]">
                      {log.mission_id && (
                        <span className="hidden sm:inline">M: {log.mission_id.slice(0, 8)}</span>
                      )}
                      <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="mt-2.5 pl-6 pr-2">
                      <div className="rounded border border-slate-800 bg-slate-900 p-3 text-[11px] text-slate-300">
                        <div className="mb-2 text-[10px] text-slate-500 flex items-center justify-between">
                          <span>Event ID: {log.event_id}</span>
                          <span>Timestamp: {log.timestamp}</span>
                        </div>
                        <pre className="overflow-x-auto text-[10px] text-emerald-300">
                          {JSON.stringify(log.payload, null, 2)}
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
