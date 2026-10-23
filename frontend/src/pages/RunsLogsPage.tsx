import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { AuditRecord, Mission } from '../types';
import { Search, ChevronDown, ChevronRight } from 'lucide-react';

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
                  OBSERVABILITY // TELEMETRY STREAM
                </span>
                <span className="px-2.5 py-0.5 rounded-full bg-slate-900/80 border border-white/10 text-[10px] font-mono text-slate-400">
                  W3C TRACE CONTEXT
                </span>
              </div>
              <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-white font-sans drop-shadow-[0_0_14px_rgba(0,240,255,0.3)]">
                Execution Runs &amp; Structured Telemetry Logs
              </h2>
              <p className="text-xs sm:text-sm text-slate-300 max-w-2xl font-sans leading-relaxed">
                Chronological real-time event pipeline with automated secret scrubbing, distributed OpenTelemetry trace propagation,
                and immutable audit logs from sandboxed worker processes.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
              <span className="inline-flex items-center space-x-2 rounded-full bg-cyan-950/80 px-4 py-2 text-xs font-mono font-semibold text-cyan-300 border border-cyan-400/40 shadow-[0_0_14px_rgba(0,240,255,0.2),inset_0_1px_1px_rgba(255,255,255,0.25)]">
                <span className="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#00F0FF] animate-pulse" />
                <span>OTel Secret Scrubbing Active</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-2xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 backdrop-blur-xl shadow-[0_0_20px_rgba(255,0,85,0.2)]">
          <p className="font-semibold font-sans">Error Loading Telemetry</p>
          <p className="mt-1 font-mono text-[11px]">{error}</p>
        </div>
      )}

      {/* Filter Controls Bar */}
      <div className="double-bezel-outer">
        <div className="double-bezel-inner p-4 sm:p-5">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
            <div className="relative">
              <Search className="absolute left-3.5 top-3.5 h-4 w-4 text-cyan-400/70" />
              <input
                type="text"
                placeholder="Search logs by keyword, agent role, ID..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="liquid-control w-full rounded-xl border border-white/[0.1] bg-slate-950/80 py-2.5 pl-10 pr-4 text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400 transition-all font-mono"
              />
            </div>

            <div>
              <select
                value={eventTypeFilter}
                onChange={(e) => setEventTypeFilter(e.target.value)}
                className="liquid-control w-full rounded-xl border border-white/[0.1] bg-slate-950/80 py-2.5 px-3.5 text-xs text-slate-200 focus:border-cyan-400 focus:outline-none font-mono"
              >
                <option value="ALL" className="bg-slate-950 text-slate-200">All Event Types</option>
                {uniqueEventTypes.map((et) => (
                  <option key={et} value={et} className="bg-slate-950 text-slate-200">
                    {et}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <select
                value={selectedMissionId}
                onChange={(e) => setSelectedMissionId(e.target.value)}
                className="liquid-control w-full rounded-xl border border-white/[0.1] bg-slate-950/80 py-2.5 px-3.5 text-xs text-slate-200 focus:border-cyan-400 focus:outline-none font-mono"
              >
                <option value="ALL" className="bg-slate-950 text-slate-200">All Missions</option>
                {missions.map((m) => (
                  <option key={m.id} value={m.id} className="bg-slate-950 text-slate-200">
                    Mission {m.id.slice(0, 8)}...
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Log Feed - Liquid Glass Terminal Console */}
      <div className="double-bezel-outer">
        <div className="double-bezel-inner p-6 font-mono text-xs space-y-4">
          <div className="flex items-center justify-between pb-4 border-b border-white/[0.08] text-slate-400">
            <div className="flex items-center space-x-2.5">
              <span className="h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#00F0FF] animate-pulse" />
              <span className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                Structured Telemetry Stream
              </span>
            </div>
            <span className="text-[10px] text-cyan-400 font-mono font-bold bg-cyan-950/80 px-3 py-1 rounded-full border border-cyan-400/30">
              {filteredLogs.length} events logged
            </span>
          </div>

          {loading ? (
            <div className="p-14 text-center text-slate-400 font-mono tracking-wider">
              <span className="inline-block animate-spin mr-2 text-cyan-400">◓</span>
              STREAMING STRUCTURED TELEMETRY...
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="p-14 text-center text-slate-400 font-mono tracking-wider">
              NO LOGS FOUND MATCHING ACTIVE FILTERS.
            </div>
          ) : (
            <div className="divide-y divide-white/[0.04]">
              {filteredLogs.map((log) => {
                const isExpanded = expandedLogId === log.event_id;
                return (
                  <div key={log.event_id} className="py-3.5 hover:bg-cyan-500/[0.03] transition-colors rounded-xl px-3">
                    <div
                      onClick={() => toggleExpand(log.event_id)}
                      className="flex items-start justify-between cursor-pointer space-x-3"
                    >
                      <div className="flex items-center space-x-2.5">
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4 text-cyan-400 flex-shrink-0" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-slate-500 flex-shrink-0" />
                        )}
                        <span className="font-bold text-cyan-300 drop-shadow-[0_0_8px_rgba(0,240,255,0.4)]">
                          {log.event_type}
                        </span>
                        {log.agent_role && (
                          <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-cyan-950/80 text-cyan-300 border border-cyan-400/30">
                            {log.agent_role}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center space-x-3 text-slate-400 text-[10px]">
                        {log.mission_id && (
                          <span className="hidden sm:inline font-mono text-slate-400">
                            M: <span className="text-slate-300">{log.mission_id.slice(0, 8)}</span>
                          </span>
                        )}
                        <span className="text-slate-400 font-mono">{new Date(log.timestamp).toLocaleTimeString()}</span>
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="mt-3.5 pl-6 pr-2">
                        <div className="liquid-glass-card rounded-xl border border-white/[0.08] p-4 text-[11px] text-slate-300">
                          <div className="mb-2 text-[10px] text-slate-400 flex items-center justify-between font-mono">
                            <span>Event ID: <span className="text-cyan-300">{log.event_id}</span></span>
                            <span>Timestamp: <span className="text-slate-300">{log.timestamp}</span></span>
                          </div>
                          <pre className="overflow-x-auto text-[11px] text-emerald-300 bg-slate-950/90 p-3.5 rounded-lg border border-white/[0.06] font-mono leading-relaxed">
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
    </div>
  );
};
