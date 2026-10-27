/**
 * Client-side authentication utilities.
 */

import { readStoredTokens } from './token-storage';

/**
 * Get the current access token from storage.
 */
export function getAuthToken(): string | null {
  const tokens = readStoredTokens();
  return tokens?.accessToken || null;
}