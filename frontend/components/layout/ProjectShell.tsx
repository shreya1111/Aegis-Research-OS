'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';

import { ApiError } from '@/lib/api/client';
import { getProject } from '@/lib/api/projects';
import { useAuth } from '@/lib/auth/auth-context';
import { cn } from '@/lib/utils/cn';
import type { Project } from '@/types/api';

import { SideNav } from '@/components/layout/SideNav';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/feedback/Skeleton';

export interface ProjectShellProps {
  projectId: string;
  children: React.ReactNode;
}

type LoadState = 'loading' | 'ready' | 'not-found' | 'error';

/**
 * Persistent workspace layout (design §5.1): left nav docked on desktop, a
 * hamburger drawer on mobile, and a breadcrumb header. Only the main content
 * region — ``children`` — changes as the user moves between tabs.
 */
export function ProjectShell({ projectId, children }: ProjectShellProps): React.JSX.Element {
  const { getValidAccessToken } = useAuth();
  const [project, setProject] = useState<Project | null>(null);
  const [loadState, setLoadState] = useState<LoadState>('loading');
  const [drawerOpen, setDrawerOpen] = useState(false);

  const loadProject = useCallback(async () => {
    setLoadState('loading');
    try {
      const token = await getValidAccessToken();
      if (!token) {
        setLoadState('error');
        return;
      }
      setProject(await getProject(token, projectId));
      setLoadState('ready');
    } catch (caught) {
      setLoadState(
        caught instanceof ApiError && caught.code === 'NOT_FOUND' ? 'not-found' : 'error',
      );
    }
  }, [getValidAccessToken, projectId]);

  useEffect(() => {
    void loadProject();
  }, [loadProject]);

  if (loadState === 'not-found') {
    return (
      <div className="container py-10">
        <Alert variant="destructive">
          This project doesn&apos;t exist, or you don&apos;t have access to it.
        </Alert>
      </div>
    );
  }

  if (loadState === 'error') {
    return (
      <div className="container flex flex-col items-start gap-3 py-10">
        <Alert variant="destructive">Could not load this project.</Alert>
        <Button type="button" variant="outline" size="sm" onClick={() => void loadProject()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col">
      {/* Breadcrumb + mobile nav toggle */}
      <div className="flex items-center gap-3 border-b px-4 py-3 lg:px-6">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="lg:hidden"
          aria-label="Open navigation"
          aria-expanded={drawerOpen}
          onClick={() => setDrawerOpen(true)}
        >
          <span aria-hidden="true">☰</span>
        </Button>
        <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-body-sm">
          <Link href="/dashboard" className="text-muted-foreground hover:text-foreground">
            Dashboard
          </Link>
          <span aria-hidden="true" className="text-muted-foreground">
            /
          </span>
          {loadState === 'loading' ? (
            <Skeleton className="h-4 w-32" />
          ) : (
            <span className="font-medium">{project?.title}</span>
          )}
        </nav>
      </div>

      <div className="flex flex-1">
        {/* Desktop sidebar */}
        <aside className="hidden w-64 shrink-0 border-r lg:block">
          <SideNav projectId={projectId} />
        </aside>

        {/* Mobile drawer */}
        {drawerOpen && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <button
              type="button"
              aria-label="Close navigation"
              className="absolute inset-0 bg-background/80 backdrop-blur-sm"
              onClick={() => setDrawerOpen(false)}
            />
            <div
              className={cn(
                'absolute left-0 top-0 h-full w-64 border-r bg-card shadow-lg',
                'duration-200 animate-in slide-in-from-left',
              )}
            >
              <SideNav projectId={projectId} onNavigate={() => setDrawerOpen(false)} />
            </div>
          </div>
        )}

        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
