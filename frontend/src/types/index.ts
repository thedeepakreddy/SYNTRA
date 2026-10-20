/**
 * SYNTRA Control Center - Frontend Type Definitions
 * Strictly aligned with backend Pydantic v2 schemas and domain entities.
 */

export type MembershipRole = 'admin' | 'developer' | 'viewer';

export interface UserContext {
  userId: string;
  orgId: string;
  role: MembershipRole;
  email: string;
}

export interface SystemOverview {
  projects_count: number;
  missions_count: number;
  pending_approvals_count: number;
  active_agents_count: number;
  total_tokens_consumed: number;
  total_cost_usd: string | number;
  system_health: 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY';
  environment: string;
  active_tenant_id: string;
}

export interface Project {
  id: string;
  org_id: string;
  name: string;
  slug: string;
  description: string | null;
  default_branch: string;
  created_at: string;
  updated_at: string;
}

export interface CreateProjectPayload {
  name: string;
  slug?: string;
  description?: string;
  default_branch?: string;
}

export type MissionState =
  | 'DRAFT'
  | 'PENDING'
  | 'PLANNING'
  | 'PLANNED'
  | 'READY'
  | 'RUNNING'
  | 'EXECUTING'
  | 'PAUSED'
  | 'REPLANNING'
  | 'VERIFYING'
  | 'AWAITING_APPROVAL'
  | 'AWAITING_DELIVERY_APPROVAL'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export type AutonomyMode = 'supervised' | 'semi_autonomous' | 'autonomous' | 'strict_approval';

export interface Mission {
  id: string;
  org_id: string;
  project_id: string;
  title: string | null;
  objective: string;
  state: MissionState;
  autonomy_mode: AutonomyMode;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface CreateMissionPayload {
  project_id: string;
  objective: string;
  title?: string;
  autonomy_mode?: AutonomyMode;
  budget_max_tokens?: number;
  budget_max_cost_usd?: string;
  max_concurrency?: number;
  max_task_attempts?: number;
  max_duration_seconds?: number;
}

export interface Task {
  id: string;
  plan_id: string;
  title: string;
  description: string | null;
  assigned_role: string;
  priority: number;
  state: string;
  dependencies: string[];
  version: number;
  created_at: string;
  updated_at: string;
}

export interface PlanResponse {
  id: string;
  mission_id: string;
  status: string;
  version: number;
  tasks: Task[];
  created_at: string;
}

export type ApprovalActionType =
  | 'INITIAL_PLAN'
  | 'SCOPE_CHANGE'
  | 'EXTERNAL_REPOSITORY_WRITE'
  | 'PULL_REQUEST_CREATION'
  | 'PROTECTED_BRANCH_MERGE'
  | 'DEPLOYMENT'
  | 'BUDGET_INCREASE'
  | 'SECURITY_POLICY_CHANGE';

export type ApprovalDecision = 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';

export interface Approval {
  id: string;
  org_id: string;
  mission_id: string;
  action_type: ApprovalActionType;
  target_resource: string;
  mission_version: number;
  decision: ApprovalDecision;
  signature_digest: string;
  comment: string | null;
  responder: string | null;
  expires_at: string;
  decided_at: string | null;
  created_at: string;
}

export interface ApprovalRespondPayload {
  decision: 'APPROVED' | 'REJECTED';
  digest: string;
  responder: string;
  comment?: string;
}

export interface AgentPersona {
  role: string;
  display_name?: string;
  mandate: string;
  responsibilities?: string[];
  allowed_tools: string[];
  forbidden_actions: string[];
  primary_inputs?: string[];
  authoritative_outputs?: string[];
  default_tier?: string;
  status?: string;
}

export interface ModelSpec {
  model_id: string;
  family: string;
  tier: 'fast' | 'balanced' | 'reasoning' | string;
  input_token_cost_per_million: number;
  output_token_cost_per_million: number;
  max_context_window: number;
  is_default: boolean;
}

export interface ModelRoutingPolicy {
  role_defaults: Record<string, string>;
  tier_definitions: Record<string, string[]>;
  cost_threshold_usd: number;
  enforce_strict_tiering: boolean;
}

export interface RoutingSimulationRequest {
  agent_role?: string;
  task_type?: string;
  requested_model?: string;
}

export interface RoutingSimulationResponse {
  assigned_tier: string;
  resolved_model: string;
  estimated_cost_tier: string;
  rationale: string;
}

export interface BenchmarkRunSummary {
  run_id: string;
  mode: string;
  status: 'PASSED' | 'FAILED' | 'ERROR';
  duration_ms: number;
  metrics: Record<string, { value: number; threshold?: number; passed?: boolean } | number>;
  completed_at?: string;
}

export interface BenchmarkRunDetail extends BenchmarkRunSummary {
  manifest?: Record<string, any>;
  verification?: Record<string, any>;
  audit_count?: number;
}

export interface AuditRecord {
  event_id: string;
  event_type: string;
  mission_id: string | null;
  task_id: string | null;
  agent_role: string | null;
  payload: Record<string, any>;
  timestamp: string;
}

export interface MissionEvent {
  id: string;
  mission_id: string;
  event_type: string;
  payload: Record<string, any>;
  created_at: string;
}

export interface Artifact {
  id: string;
  mission_id: string;
  artifact_type: string;
  path: string;
  content_hash: string;
  size_bytes: number;
  created_at: string;
}

export interface UsageRecord {
  id: string;
  mission_id: string;
  model_name: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: string | number;
  created_at: string;
}

export interface MissionUsageSummary {
  mission_id: string;
  total_tokens: number;
  total_cost_usd: string | number;
  records: UsageRecord[];
}
