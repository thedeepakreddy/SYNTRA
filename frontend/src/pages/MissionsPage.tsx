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
  ChevronRight,
  ShieldAlert,
  Zap,
  Monitor,
  Smartphone,
  Lock,
  RefreshCcw,
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

  // Live App Viewport & Frame state
  const [viewportMode, setViewportMode] = useState<'desktop' | 'mobile'>('desktop');
  const [iframeKey, setIframeKey] = useState<number>(0);
  const [copiedMissionId, setCopiedMissionId] = useState<boolean>(false);

  const handleCopyMissionId = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopiedMissionId(true);
    setTimeout(() => setCopiedMissionId(false), 2000);
  };

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
      {/* Top Banner - Double-Bezel Hardware Enclosure with HUD Brackets */}
      <div className="double-bezel-outer hud-corner relative overflow-hidden">
        <div className="absolute top-0 right-10 -mt-16 w-96 h-96 rounded-full bg-cyan-500/15 blur-3xl pointer-events-none" />
        <div className="absolute top-0 left-1/4 right-1/4 h-[1px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-80" />

        <div className="double-bezel-inner p-6 md:p-8 backdrop-blur-2xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <span className="eyebrow-pill">
                  <Zap className="h-3 w-3 text-cyan-400" />
                  <span>CYCLE-FREE TASK DAGS</span>
                </span>
              </div>
              <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white font-sans drop-shadow-[0_2px_14px_rgba(0,240,255,0.25)]">
                Autonomous Missions & Task DAGs
              </h2>
              <p className="text-xs text-slate-300 max-w-2xl font-sans">
                Orchestrated engineering missions decomposed into atomic, cycle-free task graphs governed by AGENTS.md separation of powers.
              </p>
            </div>

            <div className="flex items-center space-x-3 flex-shrink-0">
              <button
                onClick={() => setIsCreateOpen(true)}
                className="btn-island-primary group"
              >
                <span>Launch Mission</span>
                <span className="btn-island-icon">
                  <Plus className="h-4 w-4 stroke-[2.5]" />
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-2xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300 backdrop-blur-md shadow-layered-sm">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="h-4 w-4 text-rose-400" />
            <p className="font-semibold font-sans">Error Loading Missions</p>
          </div>
          <p className="mt-1 font-mono text-[11px] text-rose-400/80">{error}</p>
        </div>
      )}

      {/* Filters: Glass Search & State Tabs */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
        <div className="relative max-w-md w-full">
          <Search className="absolute left-3.5 top-3 h-4 w-4 text-cyan-400/70" />
          <input
            type="text"
            placeholder="Search missions by objective or ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-2xl border border-white/[0.12] bg-slate-950/70 py-2.5 pl-10 pr-4 text-xs text-slate-200 placeholder-slate-500 shadow-[inset_0_1px_1.5px_rgba(255,255,255,0.15)] focus:border-cyan-400 focus:bg-slate-900/90 focus:outline-none focus:ring-1 focus:ring-cyan-400/50 transition-all font-mono"
          />
        </div>

        <div className="flex items-center space-x-1 overflow-x-auto rounded-2xl border border-white/[0.12] bg-slate-950/80 p-1.5 text-xs backdrop-blur-2xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]">
          <Filter className="h-3.5 w-3.5 text-cyan-400 mx-2 flex-shrink-0" />
          {['ALL', 'PENDING', 'PLANNING', 'EXECUTING', 'AWAITING_APPROVAL', 'COMPLETED', 'FAILED'].map(
            (st) => (
              <button
                key={st}
                onClick={() => setStateFilter(st)}
                className={`rounded-xl px-3 py-1 text-[11px] font-mono tracking-wider transition-all whitespace-nowrap ${
                  stateFilter === st
                    ? 'bg-gradient-to-r from-cyan-500/30 to-teal-500/20 text-cyan-200 font-bold border border-cyan-400/50 shadow-[0_0_12px_rgba(0,240,255,0.3),inset_0_1px_1px_rgba(255,255,255,0.3)]'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.05]'
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
        <div className="rounded-3xl border border-white/[0.08] bg-slate-950/40 p-12 text-center text-xs text-slate-500 font-mono">
          <Loader2 className="mx-auto h-6 w-6 animate-spin text-cyan-400 mb-2" />
          ORCHESTRATING MISSION PIPELINES...
        </div>
      ) : filteredMissions.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-white/[0.1] bg-slate-950/40 p-12 text-center backdrop-blur-md">
          <Target className="mx-auto h-10 w-10 text-slate-600" />
          <p className="mt-3 text-sm font-semibold text-slate-300 font-sans">No missions found</p>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto font-sans">
            {search || stateFilter !== 'ALL'
              ? 'Try modifying your search query or state filter tab.'
              : 'Launch a new autonomous engineering mission to begin.'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredMissions.map((m) => {
            const project = projects.find((p) => p.id === m.project_id);
            const isRunning = m.state === 'RUNNING' || m.state === 'EXECUTING' || m.state === 'PLANNING';

            return (
              <div
                key={m.id}
                onClick={() => openMissionDetails(m)}
                className={`group cursor-pointer rounded-2xl liquid-glass-card p-5 ${
                  isRunning ? 'border-cyan-400/50 shadow-[0_0_24px_rgba(0,240,255,0.25)]' : ''
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-2 flex-1 min-w-0">
                    <div className="flex items-center space-x-2.5">
                      <StatusBadge status={m.state} />
                      <span className="font-mono text-[11px] font-bold text-cyan-300">
                        {project ? project.name : m.project_id.slice(0, 8)}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-cyan-950/60 text-cyan-300 border border-cyan-500/30">
                        {m.autonomy_mode}
                      </span>
                    </div>
                    <h3 className="font-bold text-white text-sm group-hover:text-cyan-300 transition-colors font-sans truncate drop-shadow-[0_0_8px_rgba(255,255,255,0.1)]">
                      {m.title || m.objective}
                    </h3>
                    <p className="text-xs text-slate-300 line-clamp-1 font-sans">{m.objective}</p>
                  </div>

                  <div className="flex items-center space-x-3.5 flex-shrink-0">
                    {(m.state === 'DRAFT' || m.state === 'PENDING') && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRunMission(m.id);
                        }}
                        disabled={runningId === m.id}
                        className="inline-flex items-center space-x-2 rounded-full bg-emerald-500 hover:bg-emerald-400 px-4 py-1.5 text-xs font-bold text-slate-950 shadow-[0_0_16px_rgba(0,255,157,0.4)] active:scale-[0.98] disabled:opacity-50 transition-all font-mono"
                      >
                        <Play className="h-3 w-3 fill-current" />
                        <span>{runningId === m.id ? 'Starting...' : 'Run Mission'}</span>
                      </button>
                    )}

                    {isRunning && (
                      <span className="inline-flex items-center space-x-2 rounded-full bg-cyan-950/90 px-3 py-1 text-[11px] font-mono font-bold text-cyan-300 border border-cyan-400/50 shadow-[0_0_16px_rgba(0,240,255,0.4)]">
                        <span className="relative flex h-2 w-2">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-400 shadow-[0_0_8px_#00F0FF]"></span>
                        </span>
                        <span>PIPELINE ACTIVE</span>
                      </span>
                    )}

                    <div className="flex items-center space-x-3 text-[11px] text-slate-400 font-mono">
                      <span className="inline-flex items-center space-x-1">
                        <Clock className="h-3 w-3 text-cyan-400" />
                        <span>v{m.version}</span>
                      </span>
                      <span className="inline-flex items-center space-x-1">
                        <Calendar className="h-3 w-3 text-slate-500" />
                        <span>{new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </span>
                      <ChevronRight className="h-4 w-4 text-slate-600 group-hover:text-cyan-300 group-hover:translate-x-0.5 transition-all" />
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
          maxWidth="max-w-5xl"
        >
          <div className="space-y-6">
            {/* Top Mission Profile Card: Hardware Double-Bezel Enclosure */}
            <div className="double-bezel-outer">
              <div className="double-bezel-inner p-5 sm:p-6 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  {/* Left: Badges & Mission ID */}
                  <div className="flex flex-wrap items-center gap-2.5">
                    <StatusBadge status={selectedMission.state} />
                    <span className="eyebrow-pill text-cyan-400 border-cyan-500/30">
                      {selectedMission.autonomy_mode}
                    </span>
                    <span className="px-2.5 py-1 rounded-full bg-slate-900/90 border border-white/10 text-[10px] font-mono text-slate-300">
                      v{selectedMission.version}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCopyMissionId(selectedMission.id)}
                      className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-slate-900/90 border border-cyan-500/25 hover:border-cyan-400 text-[10px] font-mono text-cyan-300 transition-colors active:scale-[0.97]"
                      title="Click to copy full Mission UUID"
                    >
                      <Copy className="h-3 w-3 text-cyan-400" />
                      <span>{selectedMission.id.slice(0, 8)}...</span>
                      {copiedMissionId && <span className="text-emerald-400 font-bold">✓ Copied</span>}
                    </button>
                  </div>

                  {/* Right Action Island */}
                  <div className="flex items-center space-x-3">
                    {selectedMission.state === 'RUNNING' && (
                      <span className="inline-flex items-center space-x-2 rounded-full bg-amber-500/15 border border-amber-500/40 px-3.5 py-1.5 text-xs font-mono font-semibold text-amber-300 shadow-[0_0_15px_rgba(245,158,11,0.3)] animate-pulse">
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        <span>Pipeline Active</span>
                      </span>
                    )}

                    {(selectedMission.state === 'DRAFT' || selectedMission.state === 'PENDING') && (
                      <button
                        onClick={() => handleRunMission(selectedMission.id)}
                        disabled={runningId === selectedMission.id}
                        className="btn-island-emerald group"
                      >
                        <span>{runningId === selectedMission.id ? 'Starting Pipeline...' : 'Run Mission'}</span>
                        <span className="btn-island-icon">
                          <Play className="h-3.5 w-3.5 fill-current text-slate-950" />
                        </span>
                      </button>
                    )}

                    {appData && (
                      <a
                        href={appData.url || `/generated_apps/${selectedMission.id}/index.html`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-island-primary group"
                        title="Open synthesized application in new tab"
                      >
                        <span>Launch App</span>
                        <span className="btn-island-icon">
                          <ExternalLink className="h-3.5 w-3.5 text-slate-950" />
                        </span>
                      </a>
                    )}

                    <button
                      onClick={() => openMissionDetails(selectedMission)}
                      className="p-2 text-slate-400 hover:text-cyan-300 rounded-full bg-slate-900/80 border border-white/10 hover:border-cyan-400/40 transition-colors active:scale-[0.95]"
                      title="Refresh mission state & tasks"
                    >
                      <RotateCw className={`h-4 w-4 ${detailLoading ? 'animate-spin text-cyan-400' : ''}`} />
                    </button>
                  </div>
                </div>

                {/* Mission Objective Statement */}
                <div className="rounded-xl bg-slate-950/80 border border-white/[0.08] p-3.5 shadow-[inset_0_1px_1px_rgba(255,255,255,0.06)] flex items-start space-x-3">
                  <div className="w-1 h-5 rounded-full bg-cyan-400 shadow-[0_0_10px_#00F0FF] flex-shrink-0 mt-0.5" />
                  <p className="text-xs sm:text-sm text-slate-200 font-sans leading-relaxed">
                    {selectedMission.objective}
                  </p>
                </div>
              </div>
            </div>

            {/* Apple Liquid Glass Floating Segmented Tab Switcher */}
            <div className="rounded-2xl p-1.5 bg-black/60 border border-white/[0.08] backdrop-blur-xl flex flex-wrap items-center gap-1.5 shadow-[inset_0_1px_1px_rgba(255,255,255,0.06)]">
              <button
                type="button"
                onClick={() => setDetailTab('tasks')}
                className={`flex items-center space-x-2 py-2 px-4 rounded-xl font-mono text-xs transition-all active:scale-[0.97] ${
                  detailTab === 'tasks'
                    ? 'tab-pill-active font-bold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.05]'
                }`}
              >
                <Layers className="h-3.5 w-3.5" />
                <span>Task DAG</span>
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-white/[0.08] text-slate-300">
                  {tasks.length}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setDetailTab('events')}
                className={`flex items-center space-x-2 py-2 px-4 rounded-xl font-mono text-xs transition-all active:scale-[0.97] ${
                  detailTab === 'events'
                    ? 'tab-pill-active font-bold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.05]'
                }`}
              >
                <History className="h-3.5 w-3.5" />
                <span>Events</span>
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-white/[0.08] text-slate-300">
                  {events.length}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setDetailTab('artifacts')}
                className={`flex items-center space-x-2 py-2 px-4 rounded-xl font-mono text-xs transition-all active:scale-[0.97] ${
                  detailTab === 'artifacts'
                    ? 'tab-pill-active font-bold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.05]'
                }`}
              >
                <FileText className="h-3.5 w-3.5" />
                <span>Artifacts</span>
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-white/[0.08] text-slate-300">
                  {artifacts.length}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setDetailTab('app')}
                className={`flex items-center space-x-2 py-2 px-4 rounded-xl font-mono text-xs transition-all active:scale-[0.97] ${
                  detailTab === 'app'
                    ? 'tab-pill-emerald-active font-bold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.05]'
                }`}
              >
                <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
                <span>Live App View</span>
                {appData && (
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_#00FF9D]" />
                )}
              </button>

              <button
                type="button"
                onClick={() => setDetailTab('usage')}
                className={`flex items-center space-x-2 py-2 px-4 rounded-xl font-mono text-xs transition-all active:scale-[0.97] ${
                  detailTab === 'usage'
                    ? 'tab-pill-active font-bold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.05]'
                }`}
              >
                <Coins className="h-3.5 w-3.5" />
                <span>Financial Ledger</span>
              </button>
            </div>

            {/* Tab Contents */}
            {detailLoading ? (
              <div className="double-bezel-outer">
                <div className="double-bezel-inner p-12 text-center text-xs text-slate-400 font-mono tracking-wider">
                  <Loader2 className="mx-auto h-6 w-6 animate-spin text-cyan-400 mb-3" />
                  SYNCHRONIZING MISSION TELEMETRY...
                </div>
              </div>
            ) : detailTab === 'tasks' ? (
              <div className="space-y-3">
                {tasks.length === 0 ? (
                  <div className="double-bezel-outer">
                    <div className="double-bezel-inner p-10 text-center space-y-3">
                      <div className="w-12 h-12 rounded-full bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center mx-auto text-cyan-400">
                        <Layers className="w-6 h-6" />
                      </div>
                      <p className="text-sm font-bold text-white font-sans">No tasks generated yet for this mission</p>
                      <p className="text-xs text-slate-400 max-w-md mx-auto font-sans leading-relaxed">
                        Trigger the autonomous multi-agent pipeline using the "Run Mission" button above to invoke Product Manager,
                        Software Architect, and Engineering Manager decomposition.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                    {tasks.map((t, idx) => (
                      <div key={t.id} className="double-bezel-outer group">
                        <div className="double-bezel-inner p-4 space-y-2.5">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-3">
                              <span className="px-2 py-0.5 rounded-md bg-cyan-950/80 text-cyan-300 border border-cyan-500/30 font-mono text-[10px] font-bold">
                                #{String(idx + 1).padStart(2, '0')}
                              </span>
                              {t.state === 'IN_PROGRESS' && (
                                <Loader2 className="h-4 w-4 animate-spin text-amber-400" />
                              )}
                              {t.state === 'COMPLETED' && (
                                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                              )}
                              <span className="font-bold text-white text-xs font-sans">{t.title}</span>
                            </div>
                            <StatusBadge status={t.state} />
                          </div>
                          <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-400 font-mono pt-1 border-t border-white/[0.04]">
                            <span className="text-cyan-400 font-bold bg-slate-900/80 px-2 py-0.5 rounded border border-white/[0.08]">
                              {t.assigned_role}
                            </span>
                            <span>Priority: <span className="text-slate-300 font-bold">{t.priority}</span></span>
                            {t.dependencies && t.dependencies.length > 0 && (
                              <span>Deps: <span className="text-amber-400 font-bold">{t.dependencies.length}</span></span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : detailTab === 'events' ? (
              <div className="double-bezel-outer">
                <div className="double-bezel-inner p-5 space-y-3 font-mono text-xs">
                  {events.length === 0 ? (
                    <p className="p-8 text-center text-slate-500 font-mono">NO EXECUTION EVENTS RECORDED YET.</p>
                  ) : (
                    <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                      {events.map((e) => (
                        <div key={e.id} className="rounded-xl border border-white/[0.08] bg-slate-950/90 p-3.5 space-y-2">
                          <div className="flex items-center justify-between text-cyan-300">
                            <span className="font-bold">{e.event_type}</span>
                            <span className="text-slate-500 text-[10px]">{new Date(e.created_at).toLocaleTimeString()}</span>
                          </div>
                          <pre className="overflow-x-auto text-[11px] text-emerald-300 bg-black/60 p-3 rounded-lg border border-white/[0.06] leading-relaxed">
                            {JSON.stringify(e.payload, null, 2)}
                          </pre>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : detailTab === 'artifacts' ? (
              <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                {artifacts.length === 0 ? (
                  <div className="double-bezel-outer">
                    <div className="double-bezel-inner p-10 text-center text-slate-500 font-sans text-xs">
                      No artifacts produced yet for this mission.
                    </div>
                  </div>
                ) : (
                  artifacts.map((a) => (
                    <div key={a.id} className="double-bezel-outer group">
                      <div className="double-bezel-inner p-4 space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2.5">
                            <FileText className="h-4 w-4 text-cyan-400" />
                            <span className="font-bold text-white truncate max-w-sm font-mono text-xs">{a.path}</span>
                          </div>
                          <div className="flex items-center space-x-2">
                            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono bg-cyan-950/80 text-cyan-300 border border-cyan-400/30 font-bold">
                              {a.artifact_type}
                            </span>
                            <button
                              type="button"
                              onClick={() => setViewingArtifact(a)}
                              className="inline-flex items-center space-x-1.5 rounded-full bg-cyan-500 hover:bg-cyan-400 text-slate-950 px-3 py-1 text-xs font-bold font-mono transition-all active:scale-[0.97]"
                              title="Inspect artifact contents"
                            >
                              <Eye className="h-3 w-3" />
                              <span>Inspect</span>
                            </button>
                          </div>
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono pt-2 border-t border-white/[0.04]">
                          <span className="truncate max-w-sm">
                            SHA: {a.content_hash ? a.content_hash.slice(0, 24) + '...' : 'pending'}
                          </span>
                          <span>{new Date(a.created_at).toLocaleTimeString()}</span>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            ) : detailTab === 'usage' ? (
              <div className="double-bezel-outer">
                <div className="double-bezel-inner p-5 space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="liquid-glass-card rounded-xl p-4 border border-white/[0.08]">
                      <span className="text-[10px] text-slate-400 uppercase tracking-widest font-mono font-bold block">
                        Mission Tokens
                      </span>
                      <p className="font-mono text-2xl font-bold text-white mt-1.5">
                        {usage ? usage.total_tokens.toLocaleString() : 0}
                      </p>
                    </div>
                    <div className="liquid-glass-card rounded-xl p-4 border border-white/[0.08]">
                      <span className="text-[10px] text-slate-400 uppercase tracking-widest font-mono font-bold block">
                        Mission Cost (USD)
                      </span>
                      <p className="font-mono text-2xl font-bold text-emerald-300 mt-1.5 drop-shadow-[0_0_8px_rgba(0,255,157,0.3)]">
                        ${usage ? Number(usage.total_cost_usd).toFixed(4) : '0.0000'}
                      </p>
                    </div>
                  </div>

                  {usage?.records && usage.records.length > 0 && (
                    <div className="overflow-x-auto rounded-xl border border-white/[0.08]">
                      <table className="w-full text-left font-mono text-xs">
                        <thead className="bg-slate-950/90 text-cyan-400/90 border-b border-white/[0.08] uppercase text-[10px] tracking-wider font-bold">
                          <tr>
                            <th className="py-2.5 px-3">Model</th>
                            <th className="py-2.5 px-3">Tokens</th>
                            <th className="py-2.5 px-3">Cost ($)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/[0.04]">
                          {usage.records.map((r) => (
                            <tr key={r.id}>
                              <td className="py-2 px-3 text-slate-200">{r.model_name}</td>
                              <td className="py-2 px-3 text-slate-400">{r.total_tokens}</td>
                              <td className="py-2 px-3 text-emerald-400 font-bold">${Number(r.cost_usd).toFixed(4)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              /* detailTab === 'app' - Apple Liquid Glass Interactive Browser Deck */
              <div className="double-bezel-outer">
                <div className="double-bezel-inner p-4 sm:p-5 space-y-4">
                  {/* Browser Chrome Header */}
                  <div className="rounded-2xl bg-slate-950/95 border border-white/[0.12] p-3 flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-[0_10px_30px_rgba(0,0,0,0.6)]">
                    {/* Traffic Lights & Address Bar */}
                    <div className="flex items-center space-x-3 flex-1 min-w-0">
                      <div className="flex items-center space-x-1.5">
                        <span className="w-3 h-3 rounded-full bg-[#FF5F56] shadow-[0_0_6px_#FF5F56]" />
                        <span className="w-3 h-3 rounded-full bg-[#FFBD2E] shadow-[0_0_6px_#FFBD2E]" />
                        <span className="w-3 h-3 rounded-full bg-[#27C93F] shadow-[0_0_6px_#27C93F]" />
                      </div>

                      <div className="flex-1 flex items-center space-x-2 rounded-full bg-slate-900/90 border border-white/[0.08] px-3.5 py-1.5 text-xs font-mono text-slate-300 shadow-[inset_0_1px_1px_rgba(255,255,255,0.06)] truncate">
                        <Lock className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                        <span className="text-cyan-400/90 truncate">
                          https://syntra.local/apps/{selectedMission.id.slice(0, 8)}/
                        </span>
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_6px_#00FF9D] flex-shrink-0" />
                      </div>
                    </div>

                    {/* Viewport & Action Controls */}
                    <div className="flex items-center space-x-2 flex-wrap">
                      {/* Device Mode Switcher */}
                      <div className="flex items-center rounded-xl bg-slate-900/90 border border-white/[0.08] p-1">
                        <button
                          type="button"
                          onClick={() => setViewportMode('desktop')}
                          className={`p-1.5 rounded-lg transition-colors ${
                            viewportMode === 'desktop'
                              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/40 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
                              : 'text-slate-400 hover:text-white'
                          }`}
                          title="Desktop Viewport (100%)"
                        >
                          <Monitor className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => setViewportMode('mobile')}
                          className={`p-1.5 rounded-lg transition-colors ${
                            viewportMode === 'mobile'
                              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/40 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
                              : 'text-slate-400 hover:text-white'
                          }`}
                          title="Mobile Viewport (iPhone 390px)"
                        >
                          <Smartphone className="h-4 w-4" />
                        </button>
                      </div>

                      {/* Source Code Toggle */}
                      <button
                        type="button"
                        onClick={() => setShowSourceCode(!showSourceCode)}
                        className={`inline-flex items-center space-x-1.5 rounded-xl px-3 py-1.5 text-xs font-mono font-medium transition-colors border ${
                          showSourceCode
                            ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400/40 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
                            : 'bg-slate-900/90 text-slate-300 border-white/[0.08] hover:bg-slate-800'
                        }`}
                      >
                        <Code className="h-3.5 w-3.5" />
                        <span>{showSourceCode ? 'Live Frame' : 'Source'}</span>
                      </button>

                      {/* Refresh Frame */}
                      <button
                        type="button"
                        onClick={() => setIframeKey((k) => k + 1)}
                        className="p-1.5 rounded-xl bg-slate-900/90 hover:bg-slate-800 text-slate-300 border border-white/[0.08] transition-colors active:scale-[0.95]"
                        title="Reload App Sandbox Frame"
                      >
                        <RefreshCcw className="h-4 w-4 text-cyan-400" />
                      </button>

                      {/* Open Fullscreen Tab */}
                      <a
                        href={appData?.url || `/generated_apps/${selectedMission.id}/index.html`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center space-x-1.5 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 text-slate-950 px-3.5 py-1.5 text-xs font-mono font-bold shadow-[0_0_14px_rgba(0,255,157,0.3)] hover:brightness-110 active:scale-[0.97] transition-all"
                      >
                        <ExternalLink className="h-3.5 w-3.5 stroke-[2.5]" />
                        <span>Popout ↗</span>
                      </a>
                    </div>
                  </div>

                  {/* Surface Display Area */}
                  {showSourceCode ? (
                    <div className="relative rounded-2xl border border-white/[0.1] bg-slate-950 p-4 max-h-[540px] overflow-auto">
                      <div className="flex items-center justify-between pb-3 border-b border-white/[0.08] mb-3">
                        <span className="text-xs font-mono text-cyan-400 font-bold uppercase tracking-wider">
                          Deliverable Source Code (HTML5 / JS)
                        </span>
                        {appData?.html && (
                          <button
                            type="button"
                            onClick={handleCopySource}
                            className="inline-flex items-center space-x-1.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 px-3 py-1 text-xs font-bold font-mono transition-colors shadow"
                          >
                            {copiedSource ? <Check className="h-3.5 w-3.5 text-slate-950" /> : <Copy className="h-3.5 w-3.5" />}
                            <span>{copiedSource ? 'Copied!' : 'Copy HTML'}</span>
                          </button>
                        )}
                      </div>
                      <pre className="font-mono text-[11px] text-emerald-300 leading-relaxed whitespace-pre-wrap select-all">
                        {appData?.html || '// Application source code is assembling...'}
                      </pre>
                    </div>
                  ) : viewportMode === 'mobile' ? (
                    <div className="py-4 flex justify-center bg-black/40 rounded-2xl border border-white/[0.06]">
                      <div className="iphone-device-bezel">
                        {/* Speaker Notch */}
                        <div className="flex justify-center mb-2">
                          <span className="w-16 h-3 rounded-full bg-slate-900 border border-white/10" />
                        </div>
                        <div className="iphone-device-screen">
                          <iframe
                            key={`mobile-${iframeKey}`}
                            src={appData?.url || `/generated_apps/${selectedMission.id}/index.html`}
                            title="Generated Mobile Application Preview"
                            className="w-full h-full border-0"
                            sandbox="allow-scripts allow-forms allow-same-origin allow-popups"
                          />
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="relative rounded-2xl border border-white/[0.1] bg-black/95 overflow-hidden shadow-2xl h-[560px]">
                      <iframe
                        key={`desktop-${iframeKey}`}
                        src={appData?.url || `/generated_apps/${selectedMission.id}/index.html`}
                        title="Generated Application Preview"
                        className="w-full h-full border-0"
                        sandbox="allow-scripts allow-forms allow-same-origin allow-popups"
                      />
                    </div>
                  )}

                  {/* Footer status banner */}
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 px-2 pt-1 border-t border-white/[0.04]">
                    <span className="flex items-center space-x-2">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                      <span>{appData?.title || 'Synthesized Application Deliverable'}</span>
                    </span>
                    <span className="text-cyan-400/80">Interactive Hermetic Sandbox</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </Modal>
      )}

      {/* Create Mission Modal */}
      <Modal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} title="Launch Autonomous Mission">
        <form onSubmit={handleCreateSubmit} className="space-y-4">
          {createError && (
            <div className="flex items-start space-x-2 rounded-xl border border-rose-500/30 bg-rose-950/40 p-3 text-xs text-rose-300">
              <AlertCircle className="h-4 w-4 flex-shrink-0 text-rose-400 mt-0.5" />
              <span>{createError}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-300 font-sans">Target Project *</label>
            <select
              value={createData.project_id}
              onChange={(e) => setCreateData({ ...createData, project_id: e.target.value })}
              className="mt-1.5 w-full rounded-xl border border-white/[0.12] bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-cyan-400 focus:outline-none"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.slug})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 font-sans">Mission Title (Optional)</label>
            <input
              type="text"
              placeholder="e.g. Build Industrial Device Prototype (defaults to objective summary)"
              value={createData.title}
              onChange={(e) => setCreateData({ ...createData, title: e.target.value })}
              className="mt-1.5 w-full rounded-xl border border-white/[0.12] bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-cyan-400 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 font-sans">Objective / Problem Statement *</label>
            <textarea
              rows={3}
              required
              placeholder="e.g. Implement atomic inventory deduction with overdraft prevention and unit tests..."
              value={createData.objective}
              onChange={(e) => setCreateData({ ...createData, objective: e.target.value })}
              className="mt-1.5 w-full rounded-xl border border-white/[0.12] bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-cyan-400 focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 font-sans">Autonomy Mode</label>
              <select
                value={createData.autonomy_mode}
                onChange={(e) =>
                  setCreateData({ ...createData, autonomy_mode: e.target.value as AutonomyMode })
                }
                className="mt-1.5 w-full rounded-xl border border-white/[0.12] bg-slate-900 px-2.5 py-2 text-xs text-slate-200 focus:border-cyan-400 focus:outline-none"
              >
                <option value="supervised">Supervised (Pause at gates)</option>
                <option value="semi_autonomous">Semi-Autonomous (Approve writes)</option>
                <option value="autonomous">Fully Autonomous</option>
                <option value="strict_approval">Strict Approval (Human approves all)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 font-sans">Token Limit</label>
              <input
                type="number"
                value={createData.budget_max_tokens}
                onChange={(e) =>
                  setCreateData({ ...createData, budget_max_tokens: Number(e.target.value) })
                }
                className="mt-1.5 w-full rounded-xl border border-white/[0.12] bg-slate-900 px-2.5 py-2 text-xs text-slate-200 font-mono focus:border-cyan-400 focus:outline-none"
              />
            </div>
          </div>

          <div className="mt-6 flex justify-end space-x-3 pt-4 border-t border-white/[0.08]">
            <button
              type="button"
              onClick={() => setIsCreateOpen(false)}
              className="rounded-full border border-white/[0.1] px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createSubmitting}
              className="rounded-full bg-cyan-500 hover:bg-cyan-400 px-5 py-2 text-xs font-bold text-slate-950 shadow-[0_0_20px_rgba(0,240,255,0.4)] disabled:opacity-50 transition-colors"
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
