'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import {
  fetchCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  refreshAccessToken,
  register as registerRequest,
} from '@/lib/api/auth';
import { ApiError } from '@/lib/api/client';
import {
  clearStoredTokens,
  readStoredTokens,
  writeAccessToken,
  writeStoredTokens,
} from '@/lib/auth/token-storage';
import type { UserProfile } from '@/types/api';

export interface AuthContextValue {
  /** The authenticated user, or `null` once the initial check has settled. */
  user: UserProfile | null;
  /** `true` while the initial session check (or a login/register call) is in flight. */
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
  /** Read the current access token, refreshing once if it has expired. */
  getValidAccessToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * Resolve the current user for a stored access token, refreshing it exactly
 * once via the refresh token if the access token has expired (design §9.2,
 * "refresh interceptor").
 */
async function resolveSession(): Promise<{ user: UserProfile; accessToken: string } | null> {
  const stored = readStoredTokens();
  if (!stored) {
    return null;
  }

  try {
    const user = await fetchCurrentUser(stored.accessToken);
    return { user, accessToken: stored.accessToken };
  } catch (error) {
    if (!(error instanceof ApiError) || error.code !== 'UNAUTHENTICATED') {
      throw error;
    }
  }

  try {
    const refreshed = await refreshAccessToken(stored.refreshToken);
    writeAccessToken(refreshed.access_token);
    const user = await fetchCurrentUser(refreshed.access_token);
    return { user, accessToken: refreshed.access_token };
  } catch {
    clearStoredTokens();
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    resolveSession()
      .then((session) => {
        if (!isMounted) return;
        setUser(session?.user ?? null);
        setAccessToken(session?.accessToken ?? null);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const tokens = await loginRequest({ email, password });
      writeStoredTokens({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
      const profile = await fetchCurrentUser(tokens.access_token);
      setAccessToken(tokens.access_token);
      setUser(profile);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const register = useCallback(
    async (email: string, password: string, name: string) => {
      setIsLoading(true);
      try {
        await registerRequest({ email, password, name });
        await login(email, password);
      } finally {
        setIsLoading(false);
      }
    },
    [login],
  );

  const logout = useCallback(async () => {
    if (accessToken) {
      try {
        await logoutRequest(accessToken);
      } catch {
        // Logout is best-effort: the client clears local state regardless, so
        // a transient network failure never traps the user in a signed-in UI.
      }
    }
    clearStoredTokens();
    setAccessToken(null);
    setUser(null);
  }, [accessToken]);

  const getValidAccessToken = useCallback(async (): Promise<string | null> => {
    const stored = readStoredTokens();
    if (!stored) {
      return null;
    }
    try {
      await fetchCurrentUser(stored.accessToken);
      return stored.accessToken;
    } catch (error) {
      if (!(error instanceof ApiError) || error.code !== 'UNAUTHENTICATED') {
        throw error;
      }
    }
    try {
      const refreshed = await refreshAccessToken(stored.refreshToken);
      writeAccessToken(refreshed.access_token);
      setAccessToken(refreshed.access_token);
      return refreshed.access_token;
    } catch {
      clearStoredTokens();
      setAccessToken(null);
      setUser(null);
      return null;
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, isLoading, login, register, logout, getValidAccessToken }),
    [user, isLoading, login, register, logout, getValidAccessToken],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider.');
  }
  return context;
}
