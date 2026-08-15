/** Project resource client (design §6.1, FR-B). */

import { apiRequest } from '@/lib/api/client';
import type { Page, Project } from '@/types/api';

export interface CreateProjectPayload {
  title: string;
  description?: string;
}

export async function listProjects(
  token: string,
  params: { page?: number; pageSize?: number } = {},
): Promise<Page<Project>> {
  const query = new URLSearchParams();
  if (params.page) query.set('page', String(params.page));
  if (params.pageSize) query.set('page_size', String(params.pageSize));
  const suffix = query.toString() ? `?${query.toString()}` : '';

  return apiRequest<Page<Project>>(`/projects${suffix}`, { token });
}

export async function createProject(
  token: string,
  payload: CreateProjectPayload,
): Promise<Project> {
  return apiRequest<Project>('/projects', { method: 'POST', body: payload, token });
}

export async function getProject(token: string, projectId: string): Promise<Project> {
  return apiRequest<Project>(`/projects/${projectId}`, { token });
}

export async function deleteProject(token: string, projectId: string): Promise<void> {
  await apiRequest<null>(`/projects/${projectId}`, { method: 'DELETE', token });
}
