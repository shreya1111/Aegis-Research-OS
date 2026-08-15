import { afterEach, describe, expect, it, vi } from 'vitest';

import { fetchCurrentUser, login, logout, refreshAccessToken, register } from '@/lib/api/auth';
import { config } from '@/lib/config';

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
  });
}

const apiBase = `${config.apiBaseUrl}${config.apiVersionPrefix}`;

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('auth API client', () => {
  it('register posts to /auth/register and returns the profile', async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(
        jsonResponse({
          success: true,
          data: { id: 'u1', email: 'alice@example.com', name: 'Alice', created_at: 'x' },
          error: null,
        }),
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    const profile = await register({
      email: 'alice@example.com',
      password: 'correct-horse',
      name: 'Alice',
    });

    expect(profile.email).toBe('alice@example.com');
    expect(fetchMock).toHaveBeenCalledWith(
      `${apiBase}/auth/register`,
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('login posts credentials and returns a token pair', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          jsonResponse({
            success: true,
            data: { access_token: 'a', refresh_token: 'r', token_type: 'bearer' },
            error: null,
          }),
        ),
      ),
    );

    const tokens = await login({ email: 'alice@example.com', password: 'correct-horse' });

    expect(tokens).toEqual({ access_token: 'a', refresh_token: 'r', token_type: 'bearer' });
  });

  it('refreshAccessToken posts the refresh token and returns a new access token', async () => {
    const fetchMock = vi.fn((_url: string, _init?: RequestInit) =>
      Promise.resolve(
        jsonResponse({
          success: true,
          data: { access_token: 'fresh', token_type: 'bearer' },
          error: null,
        }),
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    const result = await refreshAccessToken('refresh-token-value');

    expect(result.access_token).toBe('fresh');
    const body = JSON.parse((fetchMock.mock.calls[0]?.[1] as RequestInit).body as string);
    expect(body).toEqual({ refresh_token: 'refresh-token-value' });
  });

  it('fetchCurrentUser attaches the bearer token', async () => {
    const fetchMock = vi.fn((_url: string, _init?: RequestInit) =>
      Promise.resolve(
        jsonResponse({
          success: true,
          data: { id: 'u1', email: 'alice@example.com', name: 'Alice', created_at: 'x' },
          error: null,
        }),
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await fetchCurrentUser('access-token-value');

    const headers = fetchMock.mock.calls[0]?.[1]?.headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer access-token-value');
  });

  it('logout posts with the bearer token and discards the response', async () => {
    const fetchMock = vi.fn((_url: string, _init?: RequestInit) =>
      Promise.resolve(jsonResponse({ success: true, data: null, error: null })),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(logout('access-token-value')).resolves.toBeUndefined();
    const headers = fetchMock.mock.calls[0]?.[1]?.headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer access-token-value');
  });
});
