'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';

import { useAuth } from '@/lib/auth/auth-context';
import { config } from '@/lib/config';

import { NotificationsMenu } from '@/components/collaboration/NotificationsMenu';
import { Button } from '@/components/ui/button';
import { ThemeToggle } from '@/components/layout/ThemeToggle';

/** Global top bar (design §5.2): logo, theme toggle, user menu. */
export function TopBar(): React.JSX.Element {
  const { user, logout } = useAuth();
  const router = useRouter();

  async function handleLogout(): Promise<void> {
    await logout();
    router.push('/login');
  }

  return (
    <header className="brutal-panel flex items-center justify-between px-gap py-4">
      <Link href="/dashboard" className="text-h2 font-emphasis uppercase">
        {config.appName}
      </Link>
      <div className="flex items-center gap-3">
        {user && <NotificationsMenu />}
        <ThemeToggle />
        {user && (
          <div className="flex items-center gap-3">
            <span className="text-small font-reading">{user.name}</span>
            <Button type="button" variant="outline" size="sm" onClick={handleLogout}>
              Log out
            </Button>
          </div>
        )}
      </div>
    </header>
  );
}
