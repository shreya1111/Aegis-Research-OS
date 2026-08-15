/** Document resource client (design §6.1, FR-C). */

import { ApiError, apiRequest } from '@/lib/api/client';
import { config } from '@/lib/config';
import type { ApiResponse, Document } from '@/types/api';

/**
 * Upload a document via multipart form data.
 *
 * Uses ``fetch`` directly rather than the JSON ``apiRequest`` helper because
 * the body is ``FormData`` (the browser sets the multipart boundary), but
 * still consumes the same uniform envelope so error handling is identical.
 */
export async function uploadDocument(
  token: string,
  projectId: string,
  file: File,
): Promise<Document> {
  const form = new FormData();
  form.append('file', file);

  let response: Response;
  try {
    response = await fetch(
      `${config.apiBaseUrl}${config.apiVersionPrefix}/projects/${projectId}/documents`,
      {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      },
    );
  } catch {
    throw new ApiError({
      code: 'INTERNAL_ERROR',
      message: 'The server could not be reached.',
      status: 0,
    });
  }

  const requestId = response.headers.get('X-Request-ID');
  let envelope: ApiResponse<Document> | null = null;
  try {
    envelope = (await response.json()) as ApiResponse<Document>;
  } catch {
    envelope = null;
  }

  if (!response.ok || envelope?.success !== true || envelope.data === null) {
    throw new ApiError({
      code: envelope?.error?.code ?? 'INTERNAL_ERROR',
      message: envelope?.error?.message ?? 'The upload failed.',
      status: response.status,
      requestId,
    });
  }

  return envelope.data;
}

export async function listDocuments(token: string, projectId: string): Promise<Document[]> {
  return apiRequest<Document[]>(`/projects/${projectId}/documents`, { token, cache: 'no-store' });
}

export async function getDocument(token: string, documentId: string): Promise<Document> {
  return apiRequest<Document>(`/documents/${documentId}`, { token, cache: 'no-store' });
}

export async function deleteDocument(token: string, documentId: string): Promise<void> {
  await apiRequest<null>(`/documents/${documentId}`, { method: 'DELETE', token });
}
