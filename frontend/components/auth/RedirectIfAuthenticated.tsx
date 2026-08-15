'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { useAuth } from '@/lib/auth/auth-context';

/**
 * Sends an already-authenticated visitor away from `/login` and `/register`
 * to the dashboard (design §5.2 route map).
 */
export function RedirectIfAuthenticated(): null {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && user) {
      router.replace('/dashboard');
    }
  }, [isLoading, user, router]);

  return null;
}
