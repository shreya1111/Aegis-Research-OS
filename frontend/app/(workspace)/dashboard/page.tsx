'use client';

import { useCallback, useEffect, useState } from 'react';

import { ApiError } from '@/lib/api/client';
import { listProjects } from '@/lib/api/projects';
import { useAuth } from '@/lib/auth/auth-context';

import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/feedback/EmptyState';
import { CreateProjectModal } from '@/components/projects/CreateProjectModal';
import { ProjectCard } from '@/components/projects/ProjectCard';
import { ProjectGridSkeleton } from '@/components/projects/ProjectGridSkeleton';
import type { Project } from '@/types/api';

type LoadState = 'loading' | 'ready' | 'error';

export default function DashboardPage(): React.JSX.Element {
  const { getValidAccessToken } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loadState, setLoadState] = useState<LoadState>('loading');
  const [error, setError] = useState<string | null>(null);

  const loadProjects = useCallback(async () => {
    setLoadState('loading');
    setError(null);
    try {
      const token = await getValidAccessToken();
      if (!token) {
        setError('Your session has expired. Please sign in again.');
        setLoadState('error');
        return;
      }
      const page = await listProjects(token, { page: 1, pageSize: 50 });
      setProjects(page.items);
      setLoadState('ready');
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Could not load your projects.');
      setLoadState('error');
    }
  }, [getValidAccessToken]);

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  function handleCreated(project: Project): void {
    setProjects((current) => [project, ...current]);
  }

  return (
    <div className="container flex flex-col gap-6 py-10">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h1 font-semibold">Dashboard</h1>
          <p className="text-body-sm text-muted-foreground">
            Pick up a research workspace, or start a new one.
          </p>
        </div>
        {loadState === 'ready' && projects.length > 0 && (
          <CreateProjectModal
            onCreated={handleCreated}
            trigger={<Button type="button">New project</Button>}
          />
        )}
      </div>

      {loadState === 'loading' && <ProjectGridSkeleton />}

      {loadState === 'error' && error && (
        <Alert variant="destructive" className="flex-col items-start gap-3">
          <span>{error}</span>
          <Button type="button" variant="outline" size="sm" onClick={() => void loadProjects()}>
            Retry
          </Button>
        </Alert>
      )}

      {loadState === 'ready' && projects.length === 0 && (
        <EmptyState
          title="No projects yet"
          description="A project is a research workspace with its own documents, conversations, and memory. Create one to get started."
          action={
            <CreateProjectModal
              onCreated={handleCreated}
              trigger={<Button type="button">Create your first project</Button>}
            />
          }
        />
      )}

      {loadState === 'ready' && projects.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}
    </div>
  );
}
