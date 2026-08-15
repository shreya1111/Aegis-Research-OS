/**
 * Client configuration.
 *
 * Only non-sensitive, `NEXT_PUBLIC_`-prefixed values are read here — provider and
 * academic API keys are backend-only, always (design §9.8).
 */

const DEFAULT_API_URL = 'http://localhost:8000';

function requireValidUrl(value: string, variableName: string): string {
  try {
    // Fail fast on a malformed value rather than at the first request.
    new URL(value);
  } catch {
    throw new Error(`${variableName} is not a valid URL: "${value}"`);
  }
  return value.replace(/\/+$/, '');
}

function readBrowserApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL?.trim();
  return requireValidUrl(raw && raw.length > 0 ? raw : DEFAULT_API_URL, 'NEXT_PUBLIC_API_URL');
}

/**
 * The address a Server Component uses to reach the backend.
 *
 * In Docker Compose, the frontend and backend are separate containers: from
 * inside the frontend container, "localhost" refers to itself, not the
 * backend. `API_INTERNAL_URL` (server-only — no `NEXT_PUBLIC_` prefix, so it
 * never reaches the browser bundle) lets the compose file point server-side
 * fetches at the `backend` service name, while the browser-visible
 * `NEXT_PUBLIC_API_URL` continues to point at the host-exposed port. Falls
 * back to the browser URL so plain `npm run dev` (no Docker) needs no change.
 */
function readServerApiBaseUrl(): string {
  const raw = process.env.API_INTERNAL_URL?.trim();
  if (raw && raw.length > 0) {
    return requireValidUrl(raw, 'API_INTERNAL_URL');
  }
  return readBrowserApiBaseUrl();
}

export const config = {
  appName: 'Aegis Research OS',
  /** Use this from Client Components and browser-side code. */
  apiBaseUrl: readBrowserApiBaseUrl(),
  /** Use this from Server Components, route handlers, and other server-side code. */
  serverApiBaseUrl: readServerApiBaseUrl(),
  apiVersionPrefix: '/api/v1',
} as const;
