'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { useAuth } from '@/lib/auth/auth-context';

/**
 * Route protection for authenticated pages (design §5.2, Phase 1 route map).
 *
 * Renders nothing while the session check is in flight, then either the
 * protected content or a redirect to `/login` with a return path — client-side
 * enforcement is a UX affordance; the API remains the actual security
 * boundary (design §9.3 rule 1).
 */
export function AuthGuard({ children }: { children: React.ReactNode }): React.JSX.Element | null {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      const returnTo = typeof window !== 'undefined' ? window.location.pathname : '/dashboard';
      router.replace(`/login?returnTo=${encodeURIComponent(returnTo)}`);
    }
  }, [isLoading, user, router]);

  if (isLoading || !user) {
    return null;
  }

  return <>{children}</>;
}
