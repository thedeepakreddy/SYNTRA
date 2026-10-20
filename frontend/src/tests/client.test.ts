import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient, DEFAULT_USER_CONTEXT } from '../api/client';

describe('SyntraApiClient - Dev Auth & Multi-Tenancy', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    apiClient.setUserContext(DEFAULT_USER_CONTEXT);
    apiClient.setBearerToken(null);
  });

  it('injects dev auth headers when no bearer token is present', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'HEALTHY' }),
    });
    globalThis.fetch = fetchMock;

    await apiClient.getSystemOverview();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/v1/system/overview');
    expect(options.headers['X-Dev-User-Id']).toBe(DEFAULT_USER_CONTEXT.userId);
    expect(options.headers['X-Dev-Org-Id']).toBe(DEFAULT_USER_CONTEXT.orgId);
    expect(options.headers['X-Dev-Role']).toBe(DEFAULT_USER_CONTEXT.role);
    expect(options.headers['X-Dev-Email']).toBe(DEFAULT_USER_CONTEXT.email);
  });

  it('updates role and propagates new role in request headers', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    });
    globalThis.fetch = fetchMock;

    apiClient.setUserContext({ role: 'admin' });
    expect(apiClient.getUserContext().role).toBe('admin');

    await apiClient.getProjects();

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers['X-Dev-Role']).toBe('admin');
  });

  it('injects Bearer token in Authorization header when set', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    });
    globalThis.fetch = fetchMock;

    apiClient.setBearerToken('test-jwt-token-12345');

    await apiClient.getAgents();

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers['Authorization']).toBe('Bearer test-jwt-token-12345');
    // Dev headers not sent when Bearer token is present
    expect(options.headers['X-Dev-Role']).toBeUndefined();
  });
});
