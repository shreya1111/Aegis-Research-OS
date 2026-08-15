/** Health resource client. */

import { apiRequest } from '@/lib/api/client';
import { config } from '@/lib/config';
import type { HealthStatus } from '@/types/api';

/**
 * Fetch backend liveness from server-side code (e.g. a Server Component).
 *
 * The health endpoint is mounted at the application root, not under the version
 * prefix, so deployment probes need not track API versions. Uses
 * `serverApiBaseUrl` because this call happens inside the Next.js server
 * process, which in Docker Compose must reach the backend by its service name
 * rather than the browser-visible host port (see `lib/config.ts`).
 */
export async function fetchHealth(): Promise<HealthStatus> {
  return apiRequest<HealthStatus>('/health', {
    versioned: false,
    cache: 'no-store',
    baseUrl: config.serverApiBaseUrl,
  });
}
