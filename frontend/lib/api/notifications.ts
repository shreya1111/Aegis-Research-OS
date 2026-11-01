/** In-app notifications client (Phase 10, FR-H8). */

import { apiRequest } from '@/lib/api/client';
import type { NotificationInbox } from '@/types/api';

export async function listNotifications(token: string): Promise<NotificationInbox> {
  return apiRequest<NotificationInbox>('/notifications', { token });
}

export async function markNotificationRead(token: string, notificationId: string): Promise<void> {
  await apiRequest<null>(`/notifications/${notificationId}/read`, { method: 'POST', token });
}
