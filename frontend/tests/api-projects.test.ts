import { afterEach, describe, expect, it, vi } from 'vitest';

import { createProject, deleteProject, getProject, listProjects } from '@/lib/api/projects';
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

const project = {
  id: 'p1',
  title: 'My Thesis',
  description: 'Lit review',
  created_at: '2026-01-01T00:00:00Z',
};

describe('projects API client', () => {
  it('listProjects requests the default page with no query params', async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(
        jsonResponse({
          success: true,
          data: { items: [project], total: 1, page: 1, page_size: 20 },
          error: null,
        }),
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    const page = await listProjects('token');

    expect(page.items).toEqual([project]);
    expect(fetchMock).toHaveBeenCalledWith(`${apiBase}/projects`, expect.anything());
  });

  it('listProjects forwards page and pageSize as query params', async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(
        jsonResponse({
          success: true,
          data: { items: [], total: 0, page: 2, page_size: 5 },
          error: null,
        }),
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await listProjects('token', { page: 2, pageSize: 5 });

    expect(fetchMock).toHaveBeenCalledWith(
      `${apiBase}/projects?page=2&page_size=5`,
      expect.anything(),
    );
  });

  it('createProject posts the payload and returns the created project', async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(jsonResponse({ success: true, data: project, error: null })),
    );
    vi.stubGlobal('fetch', fetchMock);

    const created = await createProject('token', { title: 'My Thesis' });

    expect(created).toEqual(project);
    expect(fetchMock).toHaveBeenCalledWith(
      `${apiBase}/projects`,
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('getProject requests the project by id', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(jsonResponse({ success: true, data: project, error: null }))),
    );

    const fetched = await getProject('token', 'p1');

    expect(fetched).toEqual(project);
  });

  it('getProject surfaces a NOT_FOUND ApiError for a missing project', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          jsonResponse(
            { success: false, data: null, error: { code: 'NOT_FOUND', message: 'Not found.' } },
            { status: 404 },
          ),
        ),
      ),
    );

    await expect(getProject('token', 'missing')).rejects.toMatchObject({ code: 'NOT_FOUND' });
  });

  it('deleteProject issues a DELETE request', async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(jsonResponse({ success: true, data: null, error: null })),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(deleteProject('token', 'p1')).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(
      `${apiBase}/projects/p1`,
      expect.objectContaining({ method: 'DELETE' }),
    );
  });
});
