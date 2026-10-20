import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import {
  Artifact,
  AutonomyMode,
  CreateMissionPayload,
  Mission,
  MissionEvent,
  MissionUsageSummary,
  Project,
  Task,
} from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { Modal } from '../components/ConfirmModal';
import {
  Target,
  Plus,
  Search,
  Filter,
  Calendar,
  Layers,
  Coins,
  History,
  AlertCircle,
  Clock,
  Play,
  RotateCw,
  FileText,
  Loader2,
  CheckCircle2,
  Eye,
  ExternalLink,
  Code,
  Copy,
  Check,
  Sparkles,
} from 'lucide-react';
import { ArtifactViewerModal } from '../components/ArtifactViewerModal';

export const MissionsPage: React.FC = () => {
  const [missions, setMissions] = useState<Mission[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [stateFilter, setStateFilter] = useState<string>('ALL');

  // Mission Detail modal/drawer state
  const [selectedMission, setSelectedMission] = useState<Mission | null>(null);
  const [detailTab, setDetailTab] = useState<'tasks' | 'events' | 'artifacts' | 'usage' | 'app'>('tasks');
  const [tasks, setTasks] = useState<Task[]>([]);
  const [events, setEvents] = useState<MissionEvent[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [usage, setUsage] = useState<MissionUsageSummary | null>(null);
  const [appData, setAppData] = useState<{ mission_id: string; title: string; html: string; url: string } | null>(null);
  const [showSourceCode, setShowSourceCode] = useState(false);
  const [copiedSource, setCopiedSource] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [viewingArtifact, setViewingArtifact] = useState<Artifact | null>(null);

  // Create Mission Modal
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createData, setCreateData] = useState<CreateMissionPayload>({
    project_id: '',
    objective: '',
    title: '',
    autonomy_mode: 'semi_autonomous',
    budget_max_tokens: 250000,
    budget_max_cost_usd: '5.0000',
    max_duration_seconds: 3600,
  });
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Run Mission state
  const [runningId, setRunningId] = useState<string | null>(null);

  const handleRunMission = async (missionId: string) => {
    try {
      setRunningId(missionId);
      const updated = await apiClient.runMission(missionId);
      setMissions((prev) => prev.map((m) => (m.id === missionId ? updated : m)));
      if (selectedMission && selectedMission.id === missionId) {
        setSelectedMission(updated);
        await openMissionDetails(updated);
      }
    } catch (err: any) {
      alert(err.message || 'Failed to start mission execution.');
    } finally {
      setRunningId(null);
    }
  };

  const loadInitialData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [missionsData, projectsData] = await Promise.all([
        apiClient.getMissions(),
        apiClient.getProjects(),
      ]);
      setMissions(missionsData);
      setProjects(projectsData);
      if (projectsData.length > 0 && !createData.project_id) {
        setCreateData((prev) => ({ ...prev, project_id: projectsData[0].id }));
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load missions.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const openMissionDetails = async (mission: Mission, silent = false) => {
    setSelectedMission(mission);
    try {
      if (!silent) setDetailLoading(true);
      const [tasksRes, eventsRes, artifactsRes, usageRes, appRes] = await Promise.allSettled([
        apiClient.getMissionTasks(mission.id),
        apiClient.getMissionEvents(mission.id),
        apiClient.getMissionArtifacts(mission.id),
        apiClient.getMissionUsage(mission.id),
        apiClient.getMissionApp(mission.id),
      ]);
      if (tasksRes.status === 'fulfilled') setTasks(tasksRes.value.items || []);
      if (eventsRes.status === 'fulfilled') setEvents(eventsRes.value.items || []);
      if (artifactsRes.status === 'fulfilled') setArtifacts(artifactsRes.value.items || []);
      if (usageRes.status === 'fulfilled') setUsage(usageRes.value);
      if (appRes.status === 'fulfilled') setAppData(appRes.value);
      else setAppData(null);
    } catch {
      // handled gracefully
    } finally {
      if (!silent) setDetailLoading(false);
    }
  };

  const handleCopySource = () => {
    if (!appData?.html) return;
    navigator.clipboard.writeText(appData.html);
    setCopiedSource(true);
    setTimeout(() => setCopiedSource(false), 2000);
  };

  // Live polling: automatically refresh mission details every 2.5s while drawer is open
  useEffect(() => {
    if (!selectedMission) return;
    const interval = setInterval(async () => {
      try {
        const fresh = await apiClient.getMission(selectedMission.id);
        setSelectedMission(fresh);
        setMissions((prev) => prev.map((m) => (m.id === fresh.id ? fresh : m)));
        await openMissionDetails(fresh, true);
      } catch {
        // silent poll
      }
    }, 2500);
    return () => clearInterval(interval);
  }, [selectedMission?.id]);

  // Live polling: refresh missions list if any mission is running
  useEffect(() => {
    const hasRunning = missions.some((m) => m.state === 'RUNNING' || m.state === 'PENDING');
    if (!hasRunning) return;
    const interval = setInterval(async () => {
      try {
        const freshList = await apiClient.getMissions();
        setMissions(freshList);
      } catch {
        // silent
      }
    }, 4000);
    return () => clearInterval(interval);
  }, [missions]);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createData.project_id) {
      setCreateError('Please select a target project.');
      return;
    }
    if (!createData.objective.trim()) {
      setCreateError('Mission objective is required.');
      return;
    }

    try {
      setCreateSubmitting(true);
      setCreateError(null);
      const resolvedTitle = createData.title?.trim() || createData.objective.trim().slice(0, 60);
      await apiClient.createMission({ ...createData, title: resolvedTitle });
      setIsCreateOpen(false);
      setCreateData({
        project_id: projects[0]?.id || '',
        objective: '',
        title: '',
        autonomy_mode: 'semi_autonomous',
        budget_max_tokens: 250000,
        budget_max_cost_usd: '5.0000',
        max_duration_seconds: 3600,
      });
      await loadInitialData();
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create mission.');
    } finally {
      setCreateSubmitting(false);
    }
  };

  const filteredMissions = missions.filter((m) => {
    const matchesSearch =
      m.objective.toLowerCase().includes(search.toLowerCase()) ||
      (m.title && m.title.toLowerCase().includes(search.toLowerCase())) ||
      m.id.toLowerCase().includes(search.toLowerCase());
    const matchesState = stateFilter === 'ALL' || m.state === stateFilter;
    return matchesSearch && matchesState;
  });

  return (
    <div className="space-y-6">
      {/* Header & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Autonomous Missions & Task DAGs</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Orchestrated engineering missions decomposed into atomic, cycle-free task graphs.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setIsCreateOpen(true)}
            className="inline-flex items-center space-x-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-medium text-white shadow hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            <Plus className="h-4 w-4" />
            <span>Launch Mission</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-800 bg-rose-950/40 p-4 text-xs text-rose-300">
          <p className="font-semibold">Error Loading Missions</p>
          <p className="mt-1 font-mono">{error}</p>
        </div>
      )}

      {/* Filters: Search & State Tabs */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
        <div className="relative max-w-md w-full">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search missions by objective or ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-slate-800 bg-slate-900 py-2 pl-9 pr-4 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
          />
        </div>

        <div className="flex items-center space-x-1 overflow-x-auto rounded-lg border border-slate-800 bg-slate-900 p-1 text-xs">
          <Filter className="h-3.5 w-3.5 text-slate-500 mx-1.5" />
          {['ALL', 'PENDING', 'PLANNING', 'EXECUTING', 'AWAITING_APPROVAL', 'COMPLETED', 'FAILED'].map(
            (st) => (
              <button
                key={st}
                onClick={() => setStateFilter(st)}
                className={`rounded px-2.5 py-1 font-medium transition-colors ${
                  stateFilter === st
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {st}
              </button>
            )
          )}
        </div>
      </div>

      {/* Missions List */}
      {loading ? (
        <div className="p-8 text-center text-xs text-slate-500">Loading missions...</div>
      ) : filteredMissions.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-800 p-8 text-center">
          <Target className="mx-auto h-8 w-8 text-slate-600" />
          <p className="mt-2 text-sm font-medium text-slate-300">No missions found</p>
          <p className="text-xs text-slate-500 mt-1">
            {search || stateFilter !== 'ALL'
              ? 'Try modifying your search or state filter.'
              : 'Launch a new autonomous engineering mission to begin.'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredMissions.map((m) => {
            const project = projects.find((p) => p.id === m.project_id);
            return (
              <div
                key={m.id}
                onClick={() => openMissionDetails(m)}
                className="group cursor-pointer rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow hover:border-indigo-500/50 hover:bg-slate-900/90 transition-all"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center space-x-2">
                      <StatusBadge status={m.state} />
                      <span className="font-mono text-[11px] text-slate-500">
                        {project ? project.name : m.project_id.slice(0, 8)}
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                        {m.autonomy_mode}
                      </span>
                    </div>
                    <h3 className="font-semibold text-slate-100 text-sm group-hover:text-indigo-300 transition-colors">
                      {m.title || m.objective}
                    </h3>
                    <p className="text-xs text-slate-400 line-clamp-1">{m.objective}</p>
                  </div>

                  <div className="flex items-center space-x-3">
                    {(m.state === 'DRAFT' || m.state === 'PENDING') && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRunMission(m.id);
                        }}
                        disabled={runningId === m.id}
                        className="inline-flex items-center space-x-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white shadow hover:bg-emerald-500 disabled:opacity-50 transition-colors"
                      >
                        <Play className="h-3 w-3 fill-current" />
                        <span>{runningId === m.id ? 'Starting...' : 'Run Mission'}</span>
                      </button>
                    )}
                    {(m.state === 'RUNNING' || m.state === 'EXECUTING' || m.state === 'PLANNING') && (
                      <span className="inline-flex items-center space-x-1.5 rounded-full bg-indigo-950/80 px-2.5 py-1 text-[11px] font-medium text-indigo-300 border border-indigo-700/60">
                        <span className="relative flex h-2 w-2">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
                        </span>
                        <span>Running</span>
                      </span>
                    )}

                    <div className="flex items-center space-x-3 text-[11px] text-slate-500 font-mono">
                      <span className="inline-flex items-center space-x-1">
                        <Clock className="h-3 w-3 text-slate-400" />
                        <span>v{m.version}</span>
                      </span>
                      <span className="inline-flex items-center space-x-1">
                        <Calendar className="h-3 w-3 text-slate-400" />
                        <span>{new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Mission Detail Modal */}
      {selectedMission && (
        <Modal
          isOpen={!!selectedMission}
          onClose={() => setSelectedMission(null)}
          title={`Mission Details: ${selectedMission.id.slice(0, 8)}...`}
          maxWidth={detailTab === 'app' ? 'max-w-4xl' : 'max-w-xl'}
        >
          <div className="space-y-4">
            {/* Header info */}
            <div className="rounded-lg bg-slate-950 p-4 border border-slate-800">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <StatusBadge status={selectedMission.state} />
                  <span className="text-xs font-mono text-slate-400 px-2 py-0.5 rounded bg-slate-900 border border-slate-800">
                    {selectedMission.autonomy_mode}
                  </span>
                </div>

                {/* Header Action Controls */}
                <div className="flex items-center space-x-2">
                  {selectedMission.state === 'RUNNING' && (
                    <span className="inline-flex items-center space-x-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 text-xs font-semibold text-amber-400">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      <span>Pipeline Running...</span>
                    </span>
                  )}
                  {(selectedMission.state === 'DRAFT' || selectedMission.state === 'PENDING') && (
                    <button
                      onClick={() => handleRunMission(selectedMission.id)}
                      disabled={runningId === selectedMission.id}
                      className="inline-flex items-center space-x-1.5 rounded-lg bg-emerald-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow hover:bg-emerald-500 disabled:opacity-50 transition-colors"
                    >
                      <Play className="h-3.5 w-3.5 fill-current" />
                      <span>{runningId === selectedMission.id ? 'Starting Pipeline...' : 'Run Mission'}</span>
                    </button>
                  )}
                  <button
                    onClick={() => openMissionDetails(selectedMission)}
                    className="p-1.5 text-slate-400 hover:text-slate-200 rounded hover:bg-slate-800 transition-colors"
                    title="Refresh mission state & tasks"
                  >
                    <RotateCw className={`h-4 w-4 ${detailLoading ? 'animate-spin text-indigo-400' : ''}`} />
                  </button>
                </div>
              </div>
              <p className="mt-2.5 text-xs font-medium text-slate-200">{selectedMission.objective}</p>
            </div>

            {/* Sub-tabs & Live App Launch Button */}
            <div className="flex flex-wrap items-center justify-between border-b border-slate-800 text-xs gap-2">
              <div className="flex overflow-x-auto">
                <button
                  onClick={() => setDetailTab('tasks')}
                  className={`flex items-center space-x-1.5 py-2 px-3 border-b-2 font-medium ${
                    detailTab === 'tasks'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Layers className="h-3.5 w-3.5" />
                  <span>Task DAG ({tasks.length})</span>
                </button>
                <button
                  onClick={() => setDetailTab('events')}
                  className={`flex items-center space-x-1.5 py-2 px-3 border-b-2 font-medium ${
                    detailTab === 'events'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <History className="h-3.5 w-3.5" />
                  <span>Events ({events.length})</span>
                </button>
                <button
                  onClick={() => setDetailTab('artifacts')}
                  className={`flex items-center space-x-1.5 py-2 px-3 border-b-2 font-medium ${
                    detailTab === 'artifacts'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileText className="h-3.5 w-3.5" />
                  <span>Artifacts ({artifacts.length})</span>
                </button>
                <button
                  onClick={() => setDetailTab('app')}
                  className={`flex items-center space-x-1.5 py-2 px-3 border-b-2 font-medium ${
                    detailTab === 'app'
                      ? 'border-emerald-500 text-emerald-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
                  <span className="font-semibold text-emerald-300">Live App</span>
                  {appData && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />}
                </button>
                <button
                  onClick={() => setDetailTab('usage')}
                  className={`flex items-center space-x-1.5 py-2 px-3 border-b-2 font-medium ${
                    detailTab === 'usage'
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Coins className="h-3.5 w-3.5" />
                  <span>Ledger</span>
                </button>
              </div>

              <a
                href={appData?.url || `/generated_apps/${selectedMission.id}/index.html`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center space-x-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white px-2.5 py-1 text-xs font-semibold shadow transition-colors mb-1 mr-1"
                title="Open interactive application in new window"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                <span>Launch Live App</span>
              </a>
            </div>

            {/* Tab content */}
            {detailLoading ? (
              <div className="p-4 text-center text-xs text-slate-500">Loading mission data...</div>
            ) : detailTab === 'tasks' ? (
              <div className="max-h-80 overflow-y-auto space-y-2 pr-1">
                {tasks.length === 0 ? (
                  <p className="p-4 text-center text-xs text-slate-500">No tasks generated yet for this mission.</p>
                ) : (
                  tasks.map((t) => (
                    <div key={t.id} className="rounded border border-slate-800 bg-slate-950 p-2.5 text-xs">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          {t.state === 'IN_PROGRESS' && (
                            <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-400" />
                          )}
                          {t.state === 'COMPLETED' && (
                            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                          )}
                          <span className="font-semibold text-slate-200">{t.title}</span>
                        </div>
                        <StatusBadge status={t.state} />
                      </div>
                      <div className="mt-1 flex items-center space-x-2 text-[11px] text-slate-400">
                        <span className="font-mono text-indigo-400">{t.assigned_role}</span>
                        <span>•</span>
                        <span>Priority: {t.priority}</span>
                        {t.dependencies && t.dependencies.length > 0 && (
                          <>
                            <span>•</span>
                            <span>Deps: {t.dependencies.length}</span>
                          </>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            ) : detailTab === 'artifacts' ? (
              <div className="max-h-80 overflow-y-auto space-y-2 pr-1 text-xs">
                {artifacts.length === 0 ? (
                  <p className="p-4 text-center text-xs text-slate-500">No artifacts produced yet for this mission.</p>
                ) : (
                  artifacts.map((a) => (
                    <div key={a.id} className="rounded border border-slate-800 bg-slate-950 p-2.5 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <FileText className="h-4 w-4 text-indigo-400" />
                          <span className="font-semibold text-slate-200 truncate max-w-[280px]">{a.path}</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-950/60 text-indigo-300 border border-indigo-800/40">
                            {a.artifact_type}
                          </span>
                          <button
                            type="button"
                            onClick={() => setViewingArtifact(a)}
                            className="inline-flex items-center space-x-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white px-2 py-0.5 text-[11px] font-medium shadow transition-colors"
                            title="Inspect artifact contents"
                          >
                            <Eye className="h-3 w-3" />
                            <span>View</span>
                          </button>
                        </div>
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                        <span className="truncate max-w-[280px]" title={a.content_hash}>
                          SHA: {a.content_hash ? a.content_hash.slice(0, 16) + '...' : 'pending'}
                        </span>
                        <span>{new Date(a.created_at).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            ) : detailTab === 'events' ? (
              <div className="max-h-80 overflow-y-auto space-y-2 pr-1 font-mono text-xs">
                {events.length === 0 ? (
                  <p className="p-4 text-center text-xs text-slate-500">No execution events recorded.</p>
                ) : (
                  events.map((e) => (
                    <div key={e.id} className="rounded border border-slate-800 bg-slate-950 p-2 text-[11px]">
                      <div className="flex items-center justify-between text-indigo-300">
                        <span>{e.event_type}</span>
                        <span className="text-slate-500">{new Date(e.created_at).toLocaleTimeString()}</span>
                      </div>
                      <pre className="mt-1 overflow-x-auto text-[10px] text-slate-400">
                        {JSON.stringify(e.payload, null, 2)}
                      </pre>
                    </div>
                  ))
                )}
              </div>
            ) : detailTab === 'usage' ? (
              <div className="space-y-3 text-xs">
                <div className="grid grid-cols-2 gap-2">
                  <div className="rounded bg-slate-950 p-2 border border-slate-800">
                    <span className="text-slate-500 text-[11px]">Total Consumed Tokens</span>
                    <p className="font-mono text-sm font-bold text-slate-100">
                      {usage ? usage.total_tokens.toLocaleString() : 0}
                    </p>
                  </div>
                  <div className="rounded bg-slate-950 p-2 border border-slate-800">
                    <span className="text-slate-500 text-[11px]">Total Cost (USD)</span>
                    <p className="font-mono text-sm font-bold text-emerald-400">
                      ${usage ? Number(usage.total_cost_usd).toFixed(4) : '0.0000'}
                    </p>
                  </div>
                </div>
                {usage?.records && usage.records.length > 0 && (
                  <div className="max-h-48 overflow-y-auto border border-slate-800 rounded">
                    <table className="w-full text-left font-mono text-[10px]">
                      <thead className="bg-slate-950 text-slate-400">
                        <tr>
                          <th className="p-1.5">Model</th>
                          <th className="p-1.5">Tokens</th>
                          <th className="p-1.5">Cost ($)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800">
                        {usage.records.map((r) => (
                          <tr key={r.id}>
                            <td className="p-1.5 text-slate-300">{r.model_name}</td>
                            <td className="p-1.5 text-slate-400">{r.total_tokens}</td>
                            <td className="p-1.5 text-emerald-400">${Number(r.cost_usd).toFixed(4)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ) : (
              /* detailTab === 'app' */
              <div className="space-y-3">
                <div className="flex flex-wrap items-center justify-between bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs gap-2">
                  <div className="flex items-center space-x-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="font-medium text-slate-200 truncate max-w-[280px]">
                      {appData?.title || 'Synthesized Application Deliverable'}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      type="button"
                      onClick={() => setShowSourceCode(!showSourceCode)}
                      className="inline-flex items-center space-x-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 text-[11px] font-medium transition-colors"
                    >
                      <Code className="h-3 w-3" />
                      <span>{showSourceCode ? 'Interactive Frame' : 'Source Code'}</span>
                    </button>
                    {showSourceCode && appData?.html && (
                      <button
                        type="button"
                        onClick={handleCopySource}
                        className="inline-flex items-center space-x-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white px-2.5 py-1 text-[11px] font-medium transition-colors"
                      >
                        {copiedSource ? <Check className="h-3 w-3 text-emerald-300" /> : <Copy className="h-3 w-3" />}
                        <span>{copiedSource ? 'Copied!' : 'Copy HTML'}</span>
                      </button>
                    )}
                    <a
                      href={appData?.url || `/generated_apps/${selectedMission.id}/index.html`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center space-x-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white px-2.5 py-1 text-[11px] font-semibold transition-colors shadow"
                    >
                      <ExternalLink className="h-3 w-3" />
                      <span>Fullscreen</span>
                    </a>
                  </div>
                </div>

                {showSourceCode ? (
                  <div className="relative rounded-lg border border-slate-800 bg-slate-950 p-3 max-h-[460px] overflow-auto">
                    <pre className="font-mono text-[11px] text-emerald-300 leading-relaxed whitespace-pre-wrap select-all">
                      {appData?.html || '// Application source code is assembling...'}
                    </pre>
                  </div>
                ) : (
                  <div className="relative rounded-xl border border-slate-800 bg-slate-950 overflow-hidden shadow-inner h-[500px]">
                    <iframe
                      src={appData?.url || `/generated_apps/${selectedMission.id}/index.html`}
                      title="Generated Application Preview"
                      className="w-full h-full border-0"
                      sandbox="allow-scripts allow-forms allow-same-origin allow-popups"
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        </Modal>
      )}

      {/* Create Mission Modal */}
      <Modal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} title="Launch Autonomous Mission">
        <form onSubmit={handleCreateSubmit} className="space-y-4">
          {createError && (
            <div className="flex items-start space-x-2 rounded-lg border border-rose-800 bg-rose-950/40 p-3 text-xs text-rose-300">
              <AlertCircle className="h-4 w-4 flex-shrink-0 text-rose-400 mt-0.5" />
              <span>{createError}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300">Target Project *</label>
            <select
              value={createData.project_id}
              onChange={(e) => setCreateData({ ...createData, project_id: e.target.value })}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.slug})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300">Mission Title (Optional)</label>
            <input
              type="text"
              placeholder="e.g. Build Industrial Device Prototype (defaults to objective summary)"
              value={createData.title}
              onChange={(e) => setCreateData({ ...createData, title: e.target.value })}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300">Objective / Problem Statement *</label>
            <textarea
              rows={3}
              required
              placeholder="e.g. Implement atomic inventory deduction with overdraft prevention and unit tests..."
              value={createData.objective}
              onChange={(e) => setCreateData({ ...createData, objective: e.target.value })}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300">Autonomy Mode</label>
              <select
                value={createData.autonomy_mode}
                onChange={(e) =>
                  setCreateData({ ...createData, autonomy_mode: e.target.value as AutonomyMode })
                }
                className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-2 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
              >
                <option value="supervised">Supervised (Pause at gates)</option>
                <option value="semi_autonomous">Semi-Autonomous (Approve writes)</option>
                <option value="autonomous">Fully Autonomous</option>
                <option value="strict_approval">Strict Approval (Human approves all)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300">Token Limit</label>
              <input
                type="number"
                value={createData.budget_max_tokens}
                onChange={(e) =>
                  setCreateData({ ...createData, budget_max_tokens: Number(e.target.value) })
                }
                className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-2 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="mt-6 flex justify-end space-x-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setIsCreateOpen(false)}
              className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createSubmitting}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {createSubmitting ? 'Launching...' : 'Initialize Mission'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Artifact Document Inspector Modal */}
      <ArtifactViewerModal
        artifact={viewingArtifact}
        onClose={() => setViewingArtifact(null)}
      />
    </div>
  );
};
