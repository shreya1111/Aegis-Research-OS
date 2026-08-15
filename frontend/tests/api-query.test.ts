import { afterEach, describe, expect, it, vi } from 'vitest';

import { getTrace, runQuery } from '@/lib/api/query';
import { config } from '@/lib/config';

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
  });
}

const apiBase = `${config.apiBaseUrl}${config.apiVersionPrefix}`;

const sampleQueryResponse = {
  run_id: 'r1',
  message_id: 'm1',
  answer: 'The answer, cited [Doc 1, p.1].',
  citations: [{ marker: 'Doc 1, p.1', chunk_id: 'c1', document_id: 'd1', page: 1 }],
  sources: [],
  citation_warning: false,
  pipeline: 'rag',
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('query API client', () => {
  it('runQuery posts the question and returns the unwrapped response', async () => {
    const fetchMock = vi.fn((_url: string, _init?: RequestInit) =>
      Promise.resolve(jsonResponse({ success: true, data: sampleQueryResponse, error: null })),
    );
    vi.stubGlobal('fetch', fetchMock);

    const result = await runQuery('token', 'p1', { question: 'What is the finding?' });

    expect(result).toEqual(sampleQueryResponse);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe(`${apiBase}/projects/p1/query`);
    expect(init?.method).toBe('POST');
    expect(JSON.parse(init?.body as string)).toEqual({ question: 'What is the finding?' });
  });

  it('runQuery surfaces a RATE_LIMITED ApiError', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          jsonResponse(
            {
              success: false,
              data: null,
              error: { code: 'RATE_LIMITED', message: 'Too many questions.' },
            },
            { status: 429 },
          ),
        ),
      ),
    );

    await expect(runQuery('token', 'p1', { question: 'q' })).rejects.toMatchObject({
      code: 'RATE_LIMITED',
    });
  });

  it('getTrace requests the ordered trace for a run', async () => {
    const trace = { run_id: 'r1', steps: [] };
    const fetchMock = vi.fn(() =>
      Promise.resolve(jsonResponse({ success: true, data: trace, error: null })),
    );
    vi.stubGlobal('fetch', fetchMock);

    const result = await getTrace('token', 'p1', 'r1');

    expect(result).toEqual(trace);
    expect(fetchMock).toHaveBeenCalledWith(`${apiBase}/projects/p1/traces/r1`, expect.anything());
  });

  it('getTrace surfaces a NOT_FOUND ApiError for a missing run', async () => {
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

    await expect(getTrace('token', 'p1', 'missing')).rejects.toMatchObject({ code: 'NOT_FOUND' });
  });
});
