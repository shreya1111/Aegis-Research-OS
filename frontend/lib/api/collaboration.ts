/** Collaboration client: members, audit log, and usage (Phase 10, FR-H6–H9). */

import { apiRequest } from '@/lib/api/client';
import type { ActivityEntry, Page, ProjectMember, ProjectRole, ProjectUsage } from '@/types/api';

export async function listMembers(token: string, projectId: string): Promise<ProjectMember[]> {
  return apiRequest<ProjectMember[]>(`/projects/${projectId}/members`, { token });
}

/**
 * Mutations return the refreshed roster, so the panel never has to reconcile a
 * single row against the list it already holds.
 */
export async function inviteMember(
  token: string,
  projectId: string,
  payload: { email: string; role: Exclude<ProjectRole, 'owner'> },
): Promise<ProjectMember[]> {
  return apiRequest<ProjectMember[]>(`/projects/${projectId}/members`, {
    method: 'POST',
    body: payload,
    token,
  });
}

export async function updateMemberRole(
  token: string,
  projectId: string,
  memberId: string,
  role: Exclude<ProjectRole, 'owner'>,
): Promise<ProjectMember[]> {
  return apiRequest<ProjectMember[]>(`/projects/${projectId}/members/${memberId}`, {
    method: 'PATCH',
    body: { role },
    token,
  });
}

export async function removeMember(
  token: string,
  projectId: string,
  memberId: string,
): Promise<ProjectMember[]> {
  return apiRequest<ProjectMember[]>(`/projects/${projectId}/members/${memberId}`, {
    method: 'DELETE',
    token,
  });
}

export async function listActivity(
  token: string,
  projectId: string,
  params: { page?: number; pageSize?: number } = {},
): Promise<Page<ActivityEntry>> {
  const query = new URLSearchParams();
  if (params.page) query.set('page', String(params.page));
  if (params.pageSize) query.set('page_size', String(params.pageSize));
  const suffix = query.toString() ? `?${query.toString()}` : '';

  return apiRequest<Page<ActivityEntry>>(`/projects/${projectId}/activity${suffix}`, { token });
}

export async function getUsage(token: string, projectId: string): Promise<ProjectUsage> {
  return apiRequest<ProjectUsage>(`/projects/${projectId}/usage`, { token });
}
