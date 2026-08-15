import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider, useAuth } from '@/lib/auth/auth-context';
import { config } from '@/lib/config';

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
  });
}

const apiBase = `${config.apiBaseUrl}${config.apiVersionPrefix}`;

const profile = {
  id: 'user-1',
  email: 'alice@example.com',
  name: 'Alice',
  created_at: '2026-01-01T00:00:00Z',
};

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

describe('AuthProvider', () => {
  it('starts with no user and stops loading when no tokens are stored', async () => {
    vi.stubGlobal('fetch', vi.fn());

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.user).toBeNull();
  });

  it('logs in, stores tokens, and exposes the user', async () => {
    const fetchMock = vi.fn((url: string) => {
      if (url === `${apiBase}/auth/login`) {
        return Promise.resolve(
          jsonResponse({
            success: true,
            data: { access_token: 'access-1', refresh_token: 'refresh-1', token_type: 'bearer' },
            error: null,
          }),
        );
      }
      if (url === `${apiBase}/auth/me`) {
        return Promise.resolve(jsonResponse({ success: true, data: profile, error: null }));
      }
      throw new Error(`unexpected fetch: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.login('alice@example.com', 'correct-horse');
    });

    expect(result.current.user).toEqual(profile);
    expect(window.localStorage.getItem('aegis.auth.access_token')).toBe('access-1');
    expect(window.localStorage.getItem('aegis.auth.refresh_token')).toBe('refresh-1');
  });

  it('restores a session from stored tokens on mount', async () => {
    window.localStorage.setItem('aegis.auth.access_token', 'access-1');
    window.localStorage.setItem('aegis.auth.refresh_token', 'refresh-1');
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(jsonResponse({ success: true, data: profile, error: null }))),
    );

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.user).toEqual(profile));
  });

  it('refreshes an expired access token during session restore', async () => {
    window.localStorage.setItem('aegis.auth.access_token', 'expired-access');
    window.localStorage.setItem('aegis.auth.refresh_token', 'refresh-1');

    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (url === `${apiBase}/auth/me`) {
        const authHeader = new Headers(init?.headers).get('Authorization');
        if (authHeader === 'Bearer expired-access') {
          return Promise.resolve(
            jsonResponse(
              { success: false, data: null, error: { code: 'UNAUTHENTICATED', message: 'x' } },
              { status: 401 },
            ),
          );
        }
        return Promise.resolve(jsonResponse({ success: true, data: profile, error: null }));
      }
      if (url === `${apiBase}/auth/refresh`) {
        return Promise.resolve(
          jsonResponse({
            success: true,
            data: { access_token: 'fresh-access', token_type: 'bearer' },
            error: null,
          }),
        );
      }
      throw new Error(`unexpected fetch: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.user).toEqual(profile));
    expect(window.localStorage.getItem('aegis.auth.access_token')).toBe('fresh-access');
  });

  it('clears stored tokens when the refresh token is also invalid', async () => {
    window.localStorage.setItem('aegis.auth.access_token', 'expired-access');
    window.localStorage.setItem('aegis.auth.refresh_token', 'expired-refresh');

    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          jsonResponse(
            { success: false, data: null, error: { code: 'UNAUTHENTICATED', message: 'x' } },
            { status: 401 },
          ),
        ),
      ),
    );

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.user).toBeNull();
    expect(window.localStorage.getItem('aegis.auth.access_token')).toBeNull();
  });

  it('logout clears the user and stored tokens', async () => {
    window.localStorage.setItem('aegis.auth.access_token', 'access-1');
    window.localStorage.setItem('aegis.auth.refresh_token', 'refresh-1');
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url === `${apiBase}/auth/logout`) {
          return Promise.resolve(jsonResponse({ success: true, data: null, error: null }));
        }
        return Promise.resolve(jsonResponse({ success: true, data: profile, error: null }));
      }),
    );

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });
    await waitFor(() => expect(result.current.user).toEqual(profile));

    await act(async () => {
      await result.current.logout();
    });

    expect(result.current.user).toBeNull();
    expect(window.localStorage.getItem('aegis.auth.access_token')).toBeNull();
  });

  it('useAuth throws when used outside an AuthProvider', () => {
    // React logs the thrown error to console.error even when the test catches
    // it; suppressed here so the expected failure does not pollute test output.
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => renderHook(() => useAuth())).toThrow(
      'useAuth must be used within an AuthProvider.',
    );

    consoleError.mockRestore();
  });
});
