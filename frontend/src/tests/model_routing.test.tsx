import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ModelRoutingPage } from '../pages/ModelRoutingPage';
import { apiClient } from '../api/client';
import { ModelRoutingPolicy, ModelSpec, RoutingSimulationResponse } from '../types';

const MOCK_MODELS: ModelSpec[] = [
  {
    model_id: 'gemini-2.5-pro',
    family: 'gemini',
    tier: 'reasoning',
    input_token_cost_per_million: 1.25,
    output_token_cost_per_million: 5.0,
    max_context_window: 1000000,
    is_default: true,
  },
  {
    model_id: 'gemini-2.5-flash',
    family: 'gemini',
    tier: 'fast',
    input_token_cost_per_million: 0.075,
    output_token_cost_per_million: 0.3,
    max_context_window: 1000000,
    is_default: false,
  },
];

const MOCK_POLICY: ModelRoutingPolicy = {
  role_defaults: {
    product_manager: 'reasoning',
    backend_engineer: 'balanced',
    code_reviewer: 'reasoning',
  },
  tier_definitions: {
    reasoning: ['gemini-2.5-pro'],
    fast: ['gemini-2.5-flash'],
  },
  cost_threshold_usd: 10.0,
  enforce_strict_tiering: true,
};

const MOCK_SIM_RESULT: RoutingSimulationResponse = {
  assigned_tier: 'reasoning',
  resolved_model: 'gemini-2.5-pro',
  estimated_cost_tier: 'HIGH',
  rationale: 'Role product_manager requires deep reasoning capabilities.',
};

describe('ModelRoutingPage Component - Simulator & Catalog', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders model catalog and executes routing simulation', async () => {
    vi.spyOn(apiClient, 'getModels').mockResolvedValue(MOCK_MODELS);
    vi.spyOn(apiClient, 'getModelRoutingPolicy').mockResolvedValue(MOCK_POLICY);
    const simSpy = vi.spyOn(apiClient, 'simulateModelRouting').mockResolvedValue(MOCK_SIM_RESULT);

    render(<ModelRoutingPage />);

    // Wait for catalog to load
    await waitFor(() => {
      expect(screen.getByText('gemini-2.5-pro')).toBeInTheDocument();
      expect(screen.getByText('gemini-2.5-flash')).toBeInTheDocument();
    });

    // Verify Role-to-Tier policy section
    expect(screen.getByText('Role-Based Tiering Policies')).toBeInTheDocument();
    expect(screen.getAllByText(/product manager/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/backend engineer/i).length).toBeGreaterThan(0);

    // Trigger simulation
    const simulateButton = screen.getByText('Simulate Routing Decision');
    fireEvent.click(simulateButton);

    await waitFor(() => {
      expect(simSpy).toHaveBeenCalledWith({
        agent_role: 'product_manager',
        task_type: 'architecture_spec',
        requested_model: undefined,
      });
      expect(screen.getByText('Routing Decision Resolved')).toBeInTheDocument();
      expect(screen.getByText('Role product_manager requires deep reasoning capabilities.')).toBeInTheDocument();
    });
  });
});
