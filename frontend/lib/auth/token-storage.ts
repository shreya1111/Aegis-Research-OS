/**
 * Client-side token persistence.
 *
 * design §9.2 prefers an httpOnly cookie but explicitly accepts token storage
 * for Phase 1 ("token storage acceptable as documented in Phase 1"). This
 * implementation persists both tokens in `localStorage` so a page reload does
 * not force a re-login, and is documented here as the Phase 1 choice: it is
 * vulnerable to XSS-based token theft, which is the known trade-off of this
 * storage mode, mitigated by the short access-token TTL and server-side
 * revocation via the Redis denylist on logout.
 */

const ACCESS_TOKEN_KEY = 'aegis.auth.access_token';
const REFRESH_TOKEN_KEY = 'aegis.auth.refresh_token';

export interface StoredTokens {
  accessToken: string;
  refreshToken: string;
}

function isBrowser(): boolean {
  return typeof window !== 'undefined';
}

export function readStoredTokens(): StoredTokens | null {
  if (!isBrowser()) {
    return null;
  }

  const accessToken = window.localStorage.getItem(ACCESS_TOKEN_KEY);
  const refreshToken = window.localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!accessToken || !refreshToken) {
    return null;
  }
  return { accessToken, refreshToken };
}

export function writeStoredTokens(tokens: StoredTokens): void {
  if (!isBrowser()) {
    return;
  }
  window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.accessToken);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
}

export function writeAccessToken(accessToken: string): void {
  if (!isBrowser()) {
    return;
  }
  window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
}

export function clearStoredTokens(): void {
  if (!isBrowser()) {
    return;
  }
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}
