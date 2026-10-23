/**
 * SYNTRA Control Center - Typed API Client
 * Connects directly to FastAPI v1 endpoints with tenant & RBAC context.
 */

import {
  AgentPersona,
  Approval,
  ApprovalRespondPayload,
  Artifact,
  AuditRecord,
  BenchmarkRunDetail,
  BenchmarkRunSummary,
  CreateMissionPayload,
  CreateProjectPayload,
  Mission,
  MissionEvent,
  MissionUsageSummary,
  ModelRoutingPolicy,
  ModelSpec,
  PlanResponse,
  Project,
  RoutingSimulationRequest,
  RoutingSimulationResponse,
  SystemOverview,
  Task,
  UserContext,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/v1';

// Default active user context for local dev / testing
export const DEFAULT_USER_CONTEXT: UserContext = {
  userId: '00000000-0000-0000-0000-000000000001',
  orgId: '00000000-0000-0000-0000-000000000002',
  role: 'developer',
  email: 'operator@syntra.local',
};

function safeGetStorage(key: string): string | null {
  try {
    if (typeof window !== 'undefined' && window.localStorage && typeof window.localStorage.getItem === 'function') {
      return window.localStorage.getItem(key);
    }
  } catch {
    // ignore
  }
  return null;
}

function safeSetStorage(key: string, value: string): void {
  try {
    if (typeof window !== 'undefined' && window.localStorage && typeof window.localStorage.setItem === 'function') {
      window.localStorage.setItem(key, value);
    }
  } catch {
    // ignore
  }
}

function safeRemoveStorage(key: string): void {
  try {
    if (typeof window !== 'undefined' && window.localStorage && typeof window.localStorage.removeItem === 'function') {
      window.localStorage.removeItem(key);
    }
  } catch {
    // ignore
  }
}

class SyntraApiClient {
  private userContext: UserContext = { ...DEFAULT_USER_CONTEXT };
  private bearerToken: string | null = null;

  constructor() {
    // Attempt to hydrate from localStorage in browser environment
    const saved = safeGetStorage('syntra_user_context');
    if (saved) {
      try {
        this.userContext = JSON.parse(saved);
      } catch {
        // ignore parsing error
      }
    }
    const token = safeGetStorage('syntra_bearer_token');
    if (token) {
      this.bearerToken = token;
    }
  }

  public setUserContext(ctx: Partial<UserContext>): void {
    this.userContext = { ...this.userContext, ...ctx };
    safeSetStorage('syntra_user_context', JSON.stringify(this.userContext));
  }

  public getUserContext(): UserContext {
    return { ...this.userContext };
  }

  public setBearerToken(token: string | null): void {
    this.bearerToken = token;
    if (token) {
      safeSetStorage('syntra_bearer_token', token);
    } else {
      safeRemoveStorage('syntra_bearer_token');
    }
  }

  private getHeaders(customHeaders: Record<string, string> = {}): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...customHeaders,
    };

    if (this.bearerToken) {
      headers['Authorization'] = `Bearer ${this.bearerToken}`;
    } else {
      // Send dev auth headers
      headers['X-Dev-User-Id'] = this.userContext.userId;
      headers['X-Dev-Org-Id'] = this.userContext.orgId;
      headers['X-Dev-Role'] = this.userContext.role;
      headers['X-Dev-Email'] = this.userContext.email;
    }

    return headers;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
    const headers = this.getHeaders((options.headers as Record<string, string>) || {});

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;
      try {
        const errorBody = await response.json();
        if (errorBody && errorBody.detail) {
          errorMessage = typeof errorBody.detail === 'string' ? errorBody.detail : JSON.stringify(errorBody.detail);
        }
        if (errorBody && errorBody.invalid_params && Array.isArray(errorBody.invalid_params)) {
          const paramErrors = errorBody.invalid_params
            .map((p: any) => `${p.loc?.slice(1)?.join('.') || 'param'}: ${p.msg}`)
            .join('; ');
          errorMessage = `${errorMessage} (${paramErrors})`;
        }
      } catch {
        // use fallback message
      }
      throw new Error(errorMessage);
    }

    return response.json() as Promise<T>;
  }

  // System & Health
  public async getSystemOverview(): Promise<SystemOverview> {
    return this.request<SystemOverview>('/system/overview');
  }

  // Projects
  public async getProjects(limit = 50): Promise<Project[]> {
    return this.request<Project[]>(`/projects?limit=${limit}`);
  }

  public async getProject(projectId: string): Promise<Project> {
    return this.request<Project>(`/projects/${projectId}`);
  }

  public async createProject(payload: CreateProjectPayload): Promise<Project> {
    return this.request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  // Missions
  public async getMissions(projectId?: string, state?: string, limit = 100): Promise<Mission[]> {
    const params = new URLSearchParams();
    if (projectId) params.append('project_id', projectId);
    if (state) params.append('state', state);
    params.append('limit', limit.toString());
    return this.request<Mission[]>(`/missions?${params.toString()}`);
  }

  public async getMission(missionId: string): Promise<Mission> {
    return this.request<Mission>(`/missions/${missionId}`);
  }

  public async createMission(payload: CreateMissionPayload): Promise<Mission> {
    return this.request<Mission>('/missions', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  public async runMission(missionId: string): Promise<Mission> {
    return this.request<Mission>(`/missions/${missionId}/run`, {
      method: 'POST',
    });
  }

  public async rebuildMission(missionId: string): Promise<Mission> {
    return this.request<Mission>(`/missions/${missionId}/rebuild`, {
      method: 'POST',
    });
  }

  public async getMissionPlan(missionId: string): Promise<PlanResponse> {
    return this.request<PlanResponse>(`/missions/${missionId}/plan`);
  }

  public async getMissionTasks(missionId: string, limit = 50): Promise<{ items: Task[]; has_more: boolean }> {
    return this.request<{ items: Task[]; has_more: boolean }>(`/missions/${missionId}/tasks?limit=${limit}`);
  }

  public async getMissionEvents(missionId: string, limit = 50): Promise<{ items: MissionEvent[]; has_more: boolean }> {
    return this.request<{ items: MissionEvent[]; has_more: boolean }>(`/missions/${missionId}/events?limit=${limit}`);
  }

  public async getMissionArtifacts(missionId: string, limit = 50): Promise<{ items: Artifact[]; has_more: boolean }> {
    return this.request<{ items: Artifact[]; has_more: boolean }>(`/missions/${missionId}/artifacts?limit=${limit}`);
  }

  public async getMissionApp(missionId: string): Promise<{ mission_id: string; title: string; html: string; url: string; backend_files?: Record<string, string> }> {
    return this.request<{ mission_id: string; title: string; html: string; url: string; backend_files?: Record<string, string> }>(`/missions/${missionId}/app`);
  }

  public async getMissionBackend(missionId: string): Promise<{ mission_id: string; title: string; framework: string; files: Record<string, string> }> {
    return this.request<{ mission_id: string; title: string; framework: string; files: Record<string, string> }>(`/missions/${missionId}/backend`);
  }

  public async getMissionUsage(missionId: string): Promise<MissionUsageSummary> {
    return this.request<MissionUsageSummary>(`/missions/${missionId}/usage`);
  }

  // Approvals
  public async getApprovals(status?: string, limit = 100): Promise<Approval[]> {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    params.append('limit', limit.toString());
    const data = await this.request<any[]>(`/approvals?${params.toString()}`);
    return data.map((a) => ({
      ...a,
      signature_digest: a.signature_digest || a.action_digest,
      comment: a.comment || a.reason,
      responder: a.responder || (a.resolved_by ? String(a.resolved_by) : null),
      decided_at: a.decided_at || a.resolved_at,
    }));
  }

  public async getApproval(approvalId: string): Promise<Approval> {
    const a = await this.request<any>(`/approvals/${approvalId}`);
    return {
      ...a,
      signature_digest: a.signature_digest || a.action_digest,
      comment: a.comment || a.reason,
      responder: a.responder || (a.resolved_by ? String(a.resolved_by) : null),
      decided_at: a.decided_at || a.resolved_at,
    };
  }

  public async respondApproval(approvalId: string, payload: ApprovalRespondPayload): Promise<Approval> {
    const bodyPayload = {
      decision: payload.decision,
      action_digest: payload.digest,
      digest: payload.digest,
      reason: payload.comment || 'Approved by operator',
      comment: payload.comment || 'Approved by operator',
      responder: payload.responder,
    };
    return this.request<Approval>(`/approvals/${approvalId}/respond`, {
      method: 'POST',
      body: JSON.stringify(bodyPayload),
    });
  }

  // Agents
  public async getAgents(): Promise<AgentPersona[]> {
    return this.request<AgentPersona[]>('/agents');
  }

  // Models & Routing
  public async getModels(): Promise<ModelSpec[]> {
    return this.request<ModelSpec[]>('/models');
  }

  public async getModelRoutingPolicy(): Promise<ModelRoutingPolicy> {
    return this.request<ModelRoutingPolicy>('/models/routing');
  }

  public async simulateModelRouting(req: RoutingSimulationRequest): Promise<RoutingSimulationResponse> {
    return this.request<RoutingSimulationResponse>('/models/routing/simulate', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  }

  // Benchmarks
  public async getBenchmarks(limit = 50): Promise<BenchmarkRunSummary[]> {
    return this.request<BenchmarkRunSummary[]>(`/benchmarks?limit=${limit}`);
  }

  public async getBenchmarkRun(runId: string): Promise<BenchmarkRunDetail> {
    return this.request<BenchmarkRunDetail>(`/benchmarks/${runId}`);
  }

  // Audit
  public async getAuditRecords(limit = 100, eventType?: string, missionId?: string): Promise<AuditRecord[]> {
    const params = new URLSearchParams();
    params.append('limit', limit.toString());
    if (eventType) params.append('event_type', eventType);
    if (missionId) params.append('mission_id', missionId);
    return this.request<AuditRecord[]>(`/audit?${params.toString()}`);
  }
}

export const apiClient = new SyntraApiClient();
