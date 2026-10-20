import React, { useEffect, useState } from 'react';
import { apiClient } from './api/client';
import { MembershipRole, SystemOverview, UserContext } from './types';
import { Navigation } from './components/Navigation';
import { TopBar } from './components/TopBar';

// 13 Destination Pages
import { OverviewPage } from './pages/OverviewPage';
import { ProjectsPage } from './pages/ProjectsPage';
import { MissionsPage } from './pages/MissionsPage';
import { AgentsPage } from './pages/AgentsPage';
import { ApprovalsPage } from './pages/ApprovalsPage';
import { ModelRoutingPage } from './pages/ModelRoutingPage';
import { UsageBudgetsPage } from './pages/UsageBudgetsPage';
import { RunsLogsPage } from './pages/RunsLogsPage';
import { ArtifactsPage } from './pages/ArtifactsPage';
import { BenchmarksPage } from './pages/BenchmarksPage';
import { AuditHistoryPage } from './pages/AuditHistoryPage';
import { SystemHealthPage } from './pages/SystemHealthPage';
import { SettingsPage } from './pages/SettingsPage';

export const App: React.FC = () => {
  const [activeRoute, setActiveRoute] = useState<string>(() => {
    if (typeof window !== 'undefined' && window.location.hash) {
      const h = window.location.hash.replace(/^#\/?/, '');
      if (h) return h;
    }
    return 'overview';
  });
  const [isNavCollapsed, setIsNavCollapsed] = useState(false);
  const [overview, setOverview] = useState<SystemOverview | null>(null);
  const [userContext, setUserContext] = useState<UserContext>(apiClient.getUserContext());
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Sync route on browser back/forward history navigation
  useEffect(() => {
    const handlePopState = () => {
      if (typeof window !== 'undefined' && window.location.hash) {
        const h = window.location.hash.replace(/^#\/?/, '');
        if (h) setActiveRoute(h);
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const handleRouteChange = (route: string) => {
    setActiveRoute(route);
    try {
      if (typeof window !== 'undefined' && window.location && window.history) {
        window.history.pushState(null, '', `#/${route}`);
      }
    } catch {
      // ignore
    }
  };

  const refreshSystemData = async () => {
    try {
      setIsRefreshing(true);
      const ov = await apiClient.getSystemOverview();
      setOverview(ov);
    } catch {
      // ignore
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    refreshSystemData();
  }, [userContext]);

  const handleRoleChange = (newRole: MembershipRole) => {
    const updated = { ...userContext, role: newRole };
    apiClient.setUserContext(updated);
    setUserContext(updated);
  };

  const getRouteTitle = (route: string): string => {
    switch (route) {
      case 'overview':
        return 'Control Center Overview';
      case 'projects':
        return 'Target Software Repositories';
      case 'missions':
        return 'Missions & Task Orchestrator';
      case 'agents':
        return 'Engineering Personas & Teams';
      case 'approvals':
        return 'Human Delivery Gate';
      case 'model-routing':
        return 'Model Routing & Tiering';
      case 'usage-budgets':
        return 'Financial Ledgers & Budgets';
      case 'runs-logs':
        return 'Execution Telemetry & Logs';
      case 'artifacts':
        return 'Artifact Handoffs & Diffs';
      case 'benchmarks':
        return 'Quality Benchmarks & Evaluation';
      case 'audit-history':
        return 'Tamper-Evident Audit History';
      case 'system-health':
        return 'System Diagnostic Health';
      case 'settings':
        return 'Tenant Settings & Configuration';
      default:
        return 'SYNTRA Control Center';
    }
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-slate-950 text-slate-100 font-sans">
      {/* 13-destination Persistent Navigation */}
      <Navigation
        activeRoute={activeRoute}
        onRouteChange={handleRouteChange}
        isCollapsed={isNavCollapsed}
        onToggleCollapse={() => setIsNavCollapsed(!isNavCollapsed)}
        pendingApprovalsCount={overview?.pending_approvals_count ?? 0}
      />

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* TopBar with Role Switcher & System Indicators */}
        <TopBar
          currentRouteTitle={getRouteTitle(activeRoute)}
          overview={overview}
          userContext={userContext}
          onRoleChange={handleRoleChange}
          onRefresh={refreshSystemData}
          isRefreshing={isRefreshing}
        />

        {/* Dynamic Page Container */}
        <main
          className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-slate-800"
          id="main-content"
          role="main"
        >
          {activeRoute === 'overview' && <OverviewPage onNavigate={handleRouteChange} />}
          {activeRoute === 'projects' && <ProjectsPage />}
          {activeRoute === 'missions' && <MissionsPage />}
          {activeRoute === 'agents' && <AgentsPage />}
          {activeRoute === 'approvals' && <ApprovalsPage />}
          {activeRoute === 'model-routing' && <ModelRoutingPage />}
          {activeRoute === 'usage-budgets' && <UsageBudgetsPage />}
          {activeRoute === 'runs-logs' && <RunsLogsPage />}
          {activeRoute === 'artifacts' && <ArtifactsPage />}
          {activeRoute === 'benchmarks' && <BenchmarksPage />}
          {activeRoute === 'audit-history' && <AuditHistoryPage />}
          {activeRoute === 'system-health' && <SystemHealthPage />}
          {activeRoute === 'settings' && (
            <SettingsPage
              userContext={userContext}
              onUserContextChange={(ctx) => setUserContext(ctx)}
            />
          )}
        </main>
      </div>
    </div>
  );
};
export default App;
