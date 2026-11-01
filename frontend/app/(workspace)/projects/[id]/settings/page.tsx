'use client';

import { useParams, useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { ApiError } from '@/lib/api/client';
import { deleteProject, getProject } from '@/lib/api/projects';
import { useAuth } from '@/lib/auth/auth-context';
import { useToast } from '@/lib/toast/toast-context';
import type { Project } from '@/types/api';

import { MembersPanel } from '@/components/collaboration/MembersPanel';
import { Skeleton } from '@/components/feedback/Skeleton';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

export default function ProjectSettingsPage(): React.JSX.Element {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { getValidAccessToken } = useAuth();
  const { notify } = useToast();

  const [project, setProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDeleting, setIsDeleting] = useState(false);

  const loadProject = useCallback(async () => {
    setIsLoading(true);
    try {
      const token = await getValidAccessToken();
      if (token) {
        setProject(await getProject(token, params.id));
      }
    } catch {
      // The surrounding shell already surfaces load failures; keep settings quiet.
    } finally {
      setIsLoading(false);
    }
  }, [getValidAccessToken, params.id]);

  useEffect(() => {
    void loadProject();
  }, [loadProject]);

  async function handleDelete(): Promise<void> {
    setIsDeleting(true);
    try {
      const token = await getValidAccessToken();
      if (!token) {
        notify('error', 'Your session has expired. Please sign in again.');
        return;
      }
      await deleteProject(token, params.id);
      notify('success', 'Project deleted.');
      router.push('/dashboard');
    } catch (caught) {
      notify(
        'error',
        caught instanceof ApiError ? caught.message : 'Could not delete the project.',
      );
      setIsDeleting(false);
    }
  }

  const isOwner = project?.role === 'owner';

  return (
    <div className="container flex max-w-2xl flex-col gap-6 py-10">
      <div>
        <h1 className="text-h1 font-semibold">Settings</h1>
        <p className="text-body-sm text-muted-foreground">Manage this research workspace.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Project details</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {isLoading ? (
            <>
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-4 w-3/4" />
            </>
          ) : (
            <dl className="flex flex-col gap-3 text-body-sm">
              <div className="flex flex-col gap-1">
                <dt className="text-muted-foreground">Title</dt>
                <dd className="font-medium">{project?.title}</dd>
              </div>
              <div className="flex flex-col gap-1">
                <dt className="text-muted-foreground">Description</dt>
                <dd>{project?.description ?? 'No description.'}</dd>
              </div>
              <div className="flex flex-col gap-1">
                <dt className="text-muted-foreground">Your role</dt>
                <dd>
                  {project?.role ? (
                    <Badge variant={project.role === 'owner' ? 'default' : 'secondary'}>
                      {project.role}
                    </Badge>
                  ) : (
                    'Unknown'
                  )}
                </dd>
              </div>
            </dl>
          )}
        </CardContent>
      </Card>

      <MembersPanel projectId={params.id} role={project?.role ?? null} />

      {project !== null && !isOwner ? (
        <Card>
          <CardHeader>
            <CardTitle>Deleting this project</CardTitle>
            <CardDescription>Only the project owner can delete this workspace.</CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <Card className="border-destructive/30">
          <CardHeader>
            <CardTitle>Danger zone</CardTitle>
            <CardDescription>
              Deleting a project permanently removes its documents, conversations, and reports. This
              cannot be undone.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Dialog>
              <DialogTrigger asChild>
                <Button type="button" variant="destructive" disabled={isLoading}>
                  Delete project
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Delete this project?</DialogTitle>
                  <DialogDescription>
                    All of its documents and generated content will be permanently deleted. This
                    action cannot be undone.
                  </DialogDescription>
                </DialogHeader>
                <Alert variant="warning">
                  This will permanently delete <strong>{project?.title}</strong>.
                </Alert>
                <DialogFooter>
                  <DialogClose asChild>
                    <Button type="button" variant="outline">
                      Cancel
                    </Button>
                  </DialogClose>
                  <Button
                    type="button"
                    variant="destructive"
                    disabled={isDeleting}
                    onClick={handleDelete}
                  >
                    {isDeleting ? 'Deleting…' : 'Delete permanently'}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
