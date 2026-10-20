import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Navigation, NAV_ITEMS } from '../components/Navigation';

describe('Navigation Component - 13 Control Center Destinations', () => {
  it('renders all 13 canonical navigation links with icons and labels', () => {
    const handleRouteChange = vi.fn();
    const handleToggleCollapse = vi.fn();

    render(
      <Navigation
        activeRoute="overview"
        onRouteChange={handleRouteChange}
        isCollapsed={false}
        onToggleCollapse={handleToggleCollapse}
        pendingApprovalsCount={3}
      />
    );

    // Verify exactly 13 nav items
    expect(NAV_ITEMS).toHaveLength(13);

    // Verify all 13 labels are present in the DOM
    const expectedLabels = [
      'Overview',
      'Projects',
      'Missions & Tasks',
      'Agents & Teams',
      'Approvals',
      'Model Routing',
      'Usage & Budgets',
      'Runs & Logs',
      'Artifacts & Results',
      'Benchmarks & Quality',
      'Audit History',
      'System Health',
      'Settings & Config',
    ];

    for (const label of expectedLabels) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }

    // Verify pending approvals badge is displayed
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('triggers onRouteChange when a destination is clicked', () => {
    const handleRouteChange = vi.fn();
    const handleToggleCollapse = vi.fn();

    render(
      <Navigation
        activeRoute="overview"
        onRouteChange={handleRouteChange}
        isCollapsed={false}
        onToggleCollapse={handleToggleCollapse}
      />
    );

    const modelRoutingButton = screen.getByText('Model Routing');
    fireEvent.click(modelRoutingButton);
    expect(handleRouteChange).toHaveBeenCalledWith('model-routing');

    const approvalsButton = screen.getByText('Approvals');
    fireEvent.click(approvalsButton);
    expect(handleRouteChange).toHaveBeenCalledWith('approvals');
  });

  it('collapses and expands sidebar when toggle button is clicked', () => {
    const handleRouteChange = vi.fn();
    const handleToggleCollapse = vi.fn();

    const { rerender } = render(
      <Navigation
        activeRoute="overview"
        onRouteChange={handleRouteChange}
        isCollapsed={false}
        onToggleCollapse={handleToggleCollapse}
      />
    );

    const collapseButton = screen.getByLabelText('Collapse sidebar');
    fireEvent.click(collapseButton);
    expect(handleToggleCollapse).toHaveBeenCalledTimes(1);

    rerender(
      <Navigation
        activeRoute="overview"
        onRouteChange={handleRouteChange}
        isCollapsed={true}
        onToggleCollapse={handleToggleCollapse}
      />
    );

    expect(screen.getByLabelText('Expand sidebar')).toBeInTheDocument();
  });
});
