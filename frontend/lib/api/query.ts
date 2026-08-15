/** Query / agent-run resource client (design §6.1, §6.5, FR-D, FR-E). */

import { apiRequest } from '@/lib/api/client';
import type { QueryRequestPayload, QueryResponse, TraceRun } from '@/types/api';

export async function runQuery(
  token: string,
  projectId: string,
  payload: QueryRequestPayload,
): Promise<QueryResponse> {
  return apiRequest<QueryResponse>(`/projects/${projectId}/query`, {
    method: 'POST',
    body: payload,
    token,
  });
}

export async function getTrace(token: string, projectId: string, runId: string): Promise<TraceRun> {
  return apiRequest<TraceRun>(`/projects/${projectId}/traces/${runId}`, {
    token,
    cache: 'no-store',
  });
}
