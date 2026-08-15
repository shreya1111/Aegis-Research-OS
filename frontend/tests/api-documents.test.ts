import { afterEach, describe, expect, it, vi } from 'vitest';

import { deleteDocument, listDocuments, uploadDocument } from '@/lib/api/documents';
import { config } from '@/lib/config';

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
  });
}

const apiBase = `${config.apiBaseUrl}${config.apiVersionPrefix}`;

const sampleDocument = {
  id: 'd1',
  project_id: 'p1',
  filename: 'paper.pdf',
  status: 'pending',
  metadata: {
    title: null,
    authors: [],
    page_count: null,
    mime_type: 'application/pdf',
    size_bytes: 1024,
    ocr_used: false,
    ocr_low_confidence: false,
    ocr_min_confidence: null,
    failure_reason: null,
  },
  uploaded_at: '2026-01-01T00:00:00Z',
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('documents API client', () => {
  it('uploadDocument posts multipart form data with the bearer token', async () => {
    const fetchMock = vi.fn((_url: string, _init?: RequestInit) =>
      Promise.resolve(jsonResponse({ success: true, data: sampleDocument, error: null })),
    );
    vi.stubGlobal('fetch', fetchMock);

    const file = new File([new Uint8Array([1, 2, 3])], 'paper.pdf', { type: 'application/pdf' });
    const result = await uploadDocument('token', 'p1', file);

    expect(result.filename).toBe('paper.pdf');
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe(`${apiBase}/projects/p1/documents`);
    expect(init?.method).toBe('POST');
    expect((init?.headers as Record<string, string>).Authorization).toBe('Bearer token');
    expect(init?.body).toBeInstanceOf(FormData);
  });

  it('uploadDocument surfaces an ApiError for an unsupported type', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          jsonResponse(
            {
              success: false,
              data: null,
              error: { code: 'UNSUPPORTED_FILE_TYPE', message: 'Only PDF and DOCX.' },
            },
            { status: 400 },
          ),
        ),
      ),
    );

    const file = new File([new Uint8Array([1])], 'notes.txt', { type: 'text/plain' });
    await expect(uploadDocument('token', 'p1', file)).rejects.toMatchObject({
      code: 'UNSUPPORTED_FILE_TYPE',
    });
  });

  it('uploadDocument raises when the transport fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new TypeError('network down'))),
    );

    const file = new File([new Uint8Array([1])], 'paper.pdf', { type: 'application/pdf' });
    await expect(uploadDocument('token', 'p1', file)).rejects.toMatchObject({
      code: 'INTERNAL_ERROR',
      status: 0,
    });
  });

  it('listDocuments returns the document array', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(jsonResponse({ success: true, data: [sampleDocument], error: null })),
      ),
    );

    await expect(listDocuments('token', 'p1')).resolves.toEqual([sampleDocument]);
  });

  it('deleteDocument issues a DELETE and resolves on the null envelope', async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(jsonResponse({ success: true, data: null, error: null })),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(deleteDocument('token', 'd1')).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(
      `${apiBase}/documents/d1`,
      expect.objectContaining({ method: 'DELETE' }),
    );
  });
});
