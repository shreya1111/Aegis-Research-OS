/** Auth resource client (design §6.1, FR-A). */

import { apiRequest } from '@/lib/api/client';
import type { AccessToken, TokenPair, UserProfile } from '@/types/api';

export interface RegisterPayload {
  email: string;
  password: string;
  name: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export async function register(payload: RegisterPayload): Promise<UserProfile> {
  return apiRequest<UserProfile>('/auth/register', { method: 'POST', body: payload });
}

export async function login(payload: LoginPayload): Promise<TokenPair> {
  return apiRequest<TokenPair>('/auth/login', { method: 'POST', body: payload });
}

export async function refreshAccessToken(refreshToken: string): Promise<AccessToken> {
  return apiRequest<AccessToken>('/auth/refresh', {
    method: 'POST',
    body: { refresh_token: refreshToken },
  });
}

export async function fetchCurrentUser(accessToken: string): Promise<UserProfile> {
  return apiRequest<UserProfile>('/auth/me', { token: accessToken });
}

export async function logout(accessToken: string): Promise<void> {
  await apiRequest<null>('/auth/logout', { method: 'POST', token: accessToken });
}
