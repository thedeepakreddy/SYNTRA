import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { CreateProjectPayload, Project } from '../types';
import { Modal } from '../components/ConfirmModal';
import { FolderGit2, Plus, Search, GitBranch, Calendar, AlertCircle, Zap, RotateCw, CheckCircle2 } from 'lucide-react';

export const ProjectsPage: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [rebuildingId, setRebuildingId] = useState<string | null>(null);
  const [rebuildFeedback, setRebuildFeedback] = useState<string | null>(null);

  const handleRebuildProject = async (projectId: string, projectName: string) => {
    try {
      setRebuildingId(projectId);
      setRebuildFeedback(null);
      await apiClient.rebuildProject(projectId);
      setRebuildFeedback(`Rebuild initiated successfully for "${projectName}". Multi-agent execution pipeline dispatched.`);
      setTimeout(() => setRebuildFeedback(null), 5000);
    } catch (err: any) {
      alert(err.message || `Failed to rebuild project ${projectName}.`);
    } finally {
      setRebuildingId(null);
    }
  };

  // Create Project Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState<CreateProjectPayload>({
    name: '',
    slug: '',
    description: '',
    default_branch: 'main',
  });
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const loadProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getProjects();
      setProjects(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load projects.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setCreateError('Project name is required.');
      return;
    }

    try {
      setCreateSubmitting(true);
      setCreateError(null);
      const autoSlug =
        formData.slug?.trim() ||
        formData.name
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, '-')
          .replace(/(^-|-$)+/g, '');

      await apiClient.createProject({
        ...formData,
        slug: autoSlug,
      });

      setIsModalOpen(false);
      setFormData({ name: '', slug: '', description: '', default_branch: 'main' });
      await loadProjects();
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create project.');
    } finally {
      setCreateSubmitting(false);
    }
  };

  const filteredProjects = projects.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.slug.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header & Actions - Double-Bezel Hardware Enclosure with HUD Brackets */}
      <div className="double-bezel-outer hud-corner relative overflow-hidden">
        <div className="absolute top-0 right-10 -mt-16 w-96 h-96 rounded-full bg-cyan-500/15 blur-3xl pointer-events-none" />
        <div className="absolute top-0 left-1/4 right-1/4 h-[1px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-80" />

        <div className="double-bezel-inner p-6 md:p-8 backdrop-blur-2xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <span className="eyebrow-pill">
                  <Zap className="h-3 w-3 text-cyan-400" />
                  <span>TARGET CODEBASES</span>
                </span>
              </div>
              <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white font-sans drop-shadow-[0_2px_14px_rgba(0,240,255,0.25)]">
                Managed Projects
              </h2>
              <p className="text-xs text-slate-300 max-w-xl font-sans">
                Target software repositories governed by SYNTRA multi-agent engineering workflows.
              </p>
            </div>

            {/* CTA Button-in-Button */}
            <div className="flex items-center space-x-3 flex-shrink-0">
              <button
                onClick={() => setIsModalOpen(true)}
                className="btn-island-primary group"
              >
                <span>New Project</span>
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
          <p className="font-semibold font-sans">Error Loading Projects</p>
          <p className="mt-1 font-mono text-[11px] text-rose-400/80">{error}</p>
        </div>
      )}

      {rebuildFeedback && (
        <div className="rounded-2xl border border-emerald-500/40 bg-emerald-950/40 p-4 text-xs text-emerald-300 backdrop-blur-md shadow-layered-sm flex items-center space-x-2.5 animate-fadeIn">
          <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0" />
          <span className="font-mono">{rebuildFeedback}</span>
        </div>
      )}

      {/* Filter / Search Bar with Liquid Glass Styling */}
      <div className="relative max-w-md">
        <Search className="absolute left-3.5 top-3 h-4 w-4 text-cyan-400/70" />
        <input
          type="text"
          placeholder="Filter projects by name or slug..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-2xl border border-white/[0.12] bg-slate-950/70 py-2.5 pl-10 pr-4 text-xs text-slate-200 placeholder-slate-500 shadow-[inset_0_1px_1.5px_rgba(255,255,255,0.15)] focus:border-cyan-400 focus:bg-slate-900/90 focus:outline-none focus:ring-1 focus:ring-cyan-400/50 transition-all font-mono"
        />
      </div>

      {/* Project Cards Grid */}
      {loading ? (
        <div className="p-12 text-center text-xs font-mono text-slate-500">Loading target projects...</div>
      ) : filteredProjects.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-white/[0.1] p-12 text-center bg-slate-950/40 backdrop-blur-md">
          <FolderGit2 className="mx-auto h-10 w-10 text-slate-600" />
          <p className="mt-3 text-sm font-semibold text-slate-300 font-sans">No projects found</p>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto font-sans">
            {search ? 'Try adjusting your search criteria.' : 'Register a target software repository to begin autonomous development.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredProjects.map((p) => (
            <div
              key={p.id}
              className="liquid-glass-card rounded-2xl p-5 flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-bold text-white text-sm group-hover:text-cyan-300 transition-colors font-sans drop-shadow-[0_0_8px_rgba(255,255,255,0.1)]">
                    {p.name}
                  </h3>
                  <span className="font-mono text-[10px] text-cyan-300 bg-cyan-950/60 border border-cyan-500/30 px-2.5 py-0.5 rounded-full shadow-[0_0_8px_rgba(0,240,255,0.15)]">
                    {p.slug}
                  </span>
                </div>
                <p className="mt-2.5 text-xs text-slate-300 line-clamp-2 leading-relaxed font-sans">
                  {p.description || 'No description provided.'}
                </p>
              </div>

              <div className="mt-5 pt-3.5 border-t border-white/[0.08] flex items-center justify-between gap-2 text-[11px] text-slate-500 flex-wrap">
                <div className="flex items-center space-x-2">
                  <span className="inline-flex items-center space-x-1.5 font-mono text-cyan-200 bg-cyan-950/40 px-2.5 py-1 rounded-lg border border-cyan-500/25 shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]">
                    <GitBranch className="h-3 w-3 text-cyan-400" />
                    <span>{p.default_branch || 'main'}</span>
                  </span>
                  <span className="inline-flex items-center space-x-1 font-mono text-[10px] text-slate-400">
                    <Calendar className="h-3 w-3 text-slate-500" />
                    <span>{new Date(p.created_at).toLocaleDateString()}</span>
                  </span>
                </div>

                <button
                  onClick={() => handleRebuildProject(p.id, p.name)}
                  disabled={rebuildingId === p.id}
                  className="inline-flex items-center space-x-1.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 px-3 py-1.5 text-xs font-mono font-bold transition-all shadow-[0_0_12px_rgba(245,158,11,0.15)] active:scale-[0.97] disabled:opacity-50"
                  title={`Rebuild project deliverables for ${p.name}`}
                >
                  <RotateCw className={`h-3 w-3 ${rebuildingId === p.id ? 'animate-spin' : ''}`} />
                  <span>{rebuildingId === p.id ? 'Rebuilding...' : 'Rebuild Project'}</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Register Target Software Project">
        <form onSubmit={handleCreateSubmit} className="space-y-4">
          {createError && (
            <div className="flex items-start space-x-2 rounded-xl border border-rose-500/30 bg-rose-950/40 p-3 text-xs text-rose-300">
              <AlertCircle className="h-4 w-4 flex-shrink-0 text-rose-400 mt-0.5" />
              <span>{createError}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-300 font-sans">Project Name *</label>
            <input
              type="text"
              required
              placeholder="e.g. Acme Inventory Service"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="mt-1.5 w-full rounded-xl border border-white/[0.12] bg-slate-900/80 px-3.5 py-2.5 text-xs text-white placeholder-slate-500 shadow-[inset_0_1px_1.5px_rgba(255,255,255,0.15)] focus:border-cyan-400 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 font-sans">Slug (Optional)</label>
            <input
              type="text"
              placeholder="acme-inventory-service"
              value={formData.slug}
              onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
              className="mt-1.5 w-full rounded-xl border border-white/[0.12] bg-slate-900/80 px-3.5 py-2.5 text-xs font-mono text-white placeholder-slate-500 shadow-[inset_0_1px_1.5px_rgba(255,255,255,0.15)] focus:border-cyan-400 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 font-sans">Description</label>
            <textarea
              rows={3}
              placeholder="Primary microservice for warehouse inventory management..."
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="mt-1.5 w-full rounded-xl border border-white/[0.12] bg-slate-900/80 px-3.5 py-2.5 text-xs text-white placeholder-slate-500 shadow-[inset_0_1px_1.5px_rgba(255,255,255,0.15)] focus:border-cyan-400 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 font-sans">Default Branch</label>
            <input
              type="text"
              placeholder="main"
              value={formData.default_branch}
              onChange={(e) => setFormData({ ...formData, default_branch: e.target.value })}
              className="mt-1.5 w-full rounded-xl border border-white/[0.12] bg-slate-900/80 px-3.5 py-2.5 text-xs font-mono text-white placeholder-slate-500 shadow-[inset_0_1px_1.5px_rgba(255,255,255,0.15)] focus:border-cyan-400 focus:outline-none"
            />
          </div>

          <div className="mt-6 flex justify-end space-x-3 pt-4 border-t border-white/[0.08]">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="rounded-full border border-white/[0.1] px-4 py-2 text-xs font-medium text-slate-300 hover:bg-white/[0.06] transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createSubmitting}
              className="rounded-full bg-cyan-500 hover:bg-cyan-400 px-5 py-2 text-xs font-bold text-slate-950 shadow-[0_0_20px_rgba(0,240,255,0.4)] transition-all active:scale-[0.97] disabled:opacity-50"
            >
              {createSubmitting ? 'Registering...' : 'Register Project'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
