import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { CreateProjectPayload, Project } from '../types';
import { Modal } from '../components/ConfirmModal';
import { FolderGit2, Plus, Search, GitBranch, Calendar, AlertCircle } from 'lucide-react';

export const ProjectsPage: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  // Create Project modal state
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
      await apiClient.createProject({
        name: formData.name.trim(),
        slug: formData.slug?.trim() || undefined,
        description: formData.description?.trim() || undefined,
        default_branch: formData.default_branch?.trim() || 'main',
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
      {/* Header & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Managed Projects</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Target software repositories governed by SYNTRA multi-agent engineering workflows.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center space-x-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-medium text-white shadow hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            <Plus className="h-4 w-4" />
            <span>New Project</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-800 bg-rose-950/40 p-4 text-xs text-rose-300">
          <p className="font-semibold">Error Loading Projects</p>
          <p className="mt-1 font-mono">{error}</p>
        </div>
      )}

      {/* Filter / Search Bar */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
        <input
          type="text"
          placeholder="Filter projects by name or slug..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-lg border border-slate-800 bg-slate-900 py-2 pl-9 pr-4 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
      </div>

      {/* Project Cards / Table */}
      {loading ? (
        <div className="p-8 text-center text-xs text-slate-500">Loading projects...</div>
      ) : filteredProjects.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-800 p-8 text-center">
          <FolderGit2 className="mx-auto h-8 w-8 text-slate-600" />
          <p className="mt-2 text-sm font-medium text-slate-300">No projects found</p>
          <p className="text-xs text-slate-500 mt-1">
            {search ? 'Try clearing your search query.' : 'Register a target software repository to begin.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredProjects.map((p) => (
            <div
              key={p.id}
              className="flex flex-col justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow hover:border-slate-700 transition-colors"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold text-slate-100 text-sm">{p.name}</h3>
                  <span className="font-mono text-[10px] text-slate-500 bg-slate-800/80 px-1.5 py-0.5 rounded">
                    {p.slug}
                  </span>
                </div>
                <p className="mt-2 text-xs text-slate-400 line-clamp-2">
                  {p.description || 'No description provided.'}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500">
                <span className="inline-flex items-center space-x-1 font-mono">
                  <GitBranch className="h-3 w-3 text-slate-400" />
                  <span>{p.default_branch || 'main'}</span>
                </span>
                <span className="inline-flex items-center space-x-1">
                  <Calendar className="h-3 w-3 text-slate-400" />
                  <span>{new Date(p.created_at).toLocaleDateString()}</span>
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Register Target Software Project">
        <form onSubmit={handleCreateSubmit} className="space-y-4">
          {createError && (
            <div className="flex items-start space-x-2 rounded-lg border border-rose-800 bg-rose-950/40 p-3 text-xs text-rose-300">
              <AlertCircle className="h-4 w-4 flex-shrink-0 text-rose-400 mt-0.5" />
              <span>{createError}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300">Project Name *</label>
            <input
              type="text"
              required
              placeholder="e.g. Acme Inventory Service"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300">Slug (Optional)</label>
            <input
              type="text"
              placeholder="acme-inventory-service"
              value={formData.slug}
              onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300">Description</label>
            <textarea
              rows={3}
              placeholder="Primary microservice for warehouse inventory management..."
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300">Default Branch</label>
            <input
              type="text"
              placeholder="main"
              value={formData.default_branch}
              onChange={(e) => setFormData({ ...formData, default_branch: e.target.value })}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div className="mt-6 flex justify-end space-x-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createSubmitting}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {createSubmitting ? 'Registering...' : 'Register Project'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
