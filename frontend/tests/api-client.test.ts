import { afterEach, describe, expect, it, vi } from 'vitest';

import { ApiError, apiRequest } from '@/lib/api/client';
import { config } from '@/lib/config';

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
  });
}

function mockFetch(response: Response | Error): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn(() =>
    response instanceof Error ? Promise.reject(response) : Promise.resolve(response),
  );
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('apiRequest', () => {
  it('unwraps the envelope data on success', async () => {
    mockFetch(jsonResponse({ success: true, data: { id: 'p1' }, error: null }));

    await expect(apiRequest<{ id: string }>('/projects')).resolves.toEqual({ id: 'p1' });
  });

  it('applies the version prefix by default', async () => {
    const fetchMock = mockFetch(jsonResponse({ success: true, data: {}, error: null }));

    await apiRequest('/projects');

    expect(fetchMock).toHaveBeenCalledWith(
      `${config.apiBaseUrl}${config.apiVersionPrefix}/projects`,
      expect.anything(),
    );
  });

  it('omits the version prefix when requested', async () => {
    const fetchMock = mockFetch(jsonResponse({ success: true, data: {}, error: null }));

    await apiRequest('/health', { versioned: false });

    expect(fetchMock).toHaveBeenCalledWith(`${config.apiBaseUrl}/health`, expect.anything());
  });

  it('uses an overridden base URL when supplied (server-side Docker resolution)', async () => {
    const fetchMock = mockFetch(jsonResponse({ success: true, data: {}, error: null }));

    await apiRequest('/health', { versioned: false, baseUrl: 'http://backend:8000' });

    expect(fetchMock).toHaveBeenCalledWith('http://backend:8000/health', expect.anything());
  });

  it('attaches a bearer token when supplied', async () => {
    const fetchMock = mockFetch(jsonResponse({ success: true, data: {}, error: null }));

    await apiRequest('/auth/me', { token: 'abc' });

    const headers = fetchMock.mock.calls[0]?.[1]?.headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer abc');
  });

  it('raises ApiError carrying the envelope code and request id', async () => {
    mockFetch(
      jsonResponse(
        { success: false, data: null, error: { code: 'NOT_FOUND', message: 'No such project.' } },
        { status: 404, headers: { 'X-Request-ID': 'req-9' } },
      ),
    );

    await expect(apiRequest('/projects/x')).rejects.toMatchObject({
      name: 'ApiError',
      code: 'NOT_FOUND',
      message: 'No such project.',
      status: 404,
      requestId: 'req-9',
    });
  });

  it('raises ApiError when the transport fails', async () => {
    mockFetch(new TypeError('network down'));

    const error = await apiRequest('/projects').catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe('INTERNAL_ERROR');
    expect((error as ApiError).status).toBe(0);
  });

  it('resolves to null for a success envelope with no payload (e.g. delete/logout)', async () => {
    mockFetch(jsonResponse({ success: true, data: null, error: null }));

    await expect(apiRequest('/projects/x')).resolves.toBeNull();
  });

  it('raises ApiError when the body is not valid JSON', async () => {
    mockFetch(new Response('<html>502</html>', { status: 502 }));

    await expect(apiRequest('/projects')).rejects.toMatchObject({ code: 'INTERNAL_ERROR' });
  });
});
