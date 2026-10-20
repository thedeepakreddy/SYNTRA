import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { App } from '../App';
import { apiClient } from '../api/client';
import { SystemOverview } from '../types';

const MOCK_OVERVIEW: SystemOverview = {
  projects_count: 5,
  missions_count: 8,
  pending_approvals_count: 2,
  active_agents_count: 10,
  total_tokens_consumed: 142000,
  total_cost_usd: '0.4250',
  system_health: 'HEALTHY',
  environment: 'development',
  active_tenant_id: '00000000-0000-0000-0000-000000000002',
};

describe('App Integration - Full Control Center Route Switching', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.location.hash = '';
    vi.spyOn(apiClient, 'getSystemOverview').mockResolvedValue(MOCK_OVERVIEW);
    vi.spyOn(apiClient, 'getProjects').mockResolvedValue([]);
    vi.spyOn(apiClient, 'getMissions').mockResolvedValue([]);
    vi.spyOn(apiClient, 'getApprovals').mockResolvedValue([]);
    vi.spyOn(apiClient, 'getAgents').mockResolvedValue([]);
    vi.spyOn(apiClient, 'getModels').mockResolvedValue([]);
    vi.spyOn(apiClient, 'getModelRoutingPolicy').mockResolvedValue({
      role_defaults: {},
      tier_definitions: {},
      cost_threshold_usd: 10,
      enforce_strict_tiering: true,
    });
    vi.spyOn(apiClient, 'getBenchmarks').mockResolvedValue([]);
    vi.spyOn(apiClient, 'getAuditRecords').mockResolvedValue([]);
  });

  it('renders top bar with tenant, environment, and role switcher', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('SYNTRA')).toBeInTheDocument();
      expect(screen.getByText('DEVELOPMENT')).toBeInTheDocument();
      expect(screen.getByRole('combobox', { name: /switch user role/i })).toBeInTheDocument();
    });
  });

  it('switches between all 13 destinations seamlessly via navigation', async () => {
    render(<App />);

    // 1. Overview
    await waitFor(() => {
      expect(screen.getByText('SYNTRA Autonomous Engineering Organization')).toBeInTheDocument();
    });

    // 2. Projects
    fireEvent.click(screen.getByTestId('nav-projects'));
    await waitFor(() => {
      expect(screen.getByText('Managed Projects')).toBeInTheDocument();
    });

    // 3. Missions & Tasks
    fireEvent.click(screen.getByTestId('nav-missions'));
    await waitFor(() => {
      expect(screen.getByText('Autonomous Missions & Task DAGs')).toBeInTheDocument();
    });

    // 4. Agents & Teams
    fireEvent.click(screen.getByTestId('nav-agents'));
    await waitFor(() => {
      expect(screen.getByText('The 10 Specialized Engineering Personas')).toBeInTheDocument();
    });

    // 5. Approvals
    fireEvent.click(screen.getByTestId('nav-approvals'));
    await waitFor(() => {
      expect(screen.getByText('Cryptographic Human Delivery Gate')).toBeInTheDocument();
    });

    // 6. Model Routing
    fireEvent.click(screen.getByTestId('nav-model-routing'));
    await waitFor(() => {
      expect(screen.getByText('Model Routing, Tiering & Decision Traceability')).toBeInTheDocument();
    });

    // 7. Usage & Budgets
    fireEvent.click(screen.getByTestId('nav-usage-budgets'));
    await waitFor(() => {
      expect(screen.getByText('Financial Ledgers, Budgets & Token Governance')).toBeInTheDocument();
    });

    // 8. Runs & Logs
    fireEvent.click(screen.getByTestId('nav-runs-logs'));
    await waitFor(() => {
      expect(screen.getByText('Execution Runs & Structured Telemetry Logs')).toBeInTheDocument();
    });

    // 9. Artifacts & Results
    fireEvent.click(screen.getByTestId('nav-artifacts'));
    await waitFor(() => {
      expect(screen.getByText('Immutable Artifact Handoffs & Unified Diffs')).toBeInTheDocument();
    });

    // 10. Benchmarks & Quality
    fireEvent.click(screen.getByTestId('nav-benchmarks'));
    await waitFor(() => {
      expect(screen.getByText('Benchmarking & Quantitative Quality Evaluation')).toBeInTheDocument();
    });

    // 11. Audit History
    fireEvent.click(screen.getByTestId('nav-audit-history'));
    await waitFor(() => {
      expect(screen.getByText('Immutable & Tamper-Evident Audit Trail')).toBeInTheDocument();
    });

    // 12. System Health
    fireEvent.click(screen.getByTestId('nav-system-health'));
    await waitFor(() => {
      expect(screen.getByText('Platform Diagnostic & Infrastructure Health')).toBeInTheDocument();
    });

    // 13. Settings & Config
    fireEvent.click(screen.getByTestId('nav-settings'));
    await waitFor(() => {
      expect(screen.getByText('Tenant Settings & RBAC Context Configuration')).toBeInTheDocument();
    });
  });

  it('switches role in topbar and updates active context', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: /switch user role/i })).toBeInTheDocument();
    });

    const roleSelect = screen.getByRole('combobox', { name: /switch user role/i });
    fireEvent.change(roleSelect, { target: { value: 'admin' } });

    expect(apiClient.getUserContext().role).toBe('admin');
  });
});
