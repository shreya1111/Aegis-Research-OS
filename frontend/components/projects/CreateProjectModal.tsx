'use client';

import { useState } from 'react';

import { ApiError } from '@/lib/api/client';
import { createProject } from '@/lib/api/projects';
import { useAuth } from '@/lib/auth/auth-context';

import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { Project } from '@/types/api';

export interface CreateProjectModalProps {
  onCreated: (project: Project) => void;
  trigger: React.ReactNode;
}

export function CreateProjectModal({
  onCreated,
  trigger,
}: CreateProjectModalProps): React.JSX.Element {
  const { getValidAccessToken } = useAuth();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function resetAndClose(): void {
    setTitle('');
    setDescription('');
    setError(null);
    setOpen(false);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const token = await getValidAccessToken();
      if (!token) {
        setError('Your session has expired. Please sign in again.');
        return;
      }
      const project = await createProject(token, {
        title,
        description: description.trim() ? description.trim() : undefined,
      });
      onCreated(project);
      resetAndClose();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Could not create the project.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create a project</DialogTitle>
          <DialogDescription>
            A project is a research workspace: its own documents, conversations, and memory.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
          {error && <Alert variant="destructive">{error}</Alert>}

          <div className="flex flex-col gap-2">
            <Label htmlFor="project-title">Title</Label>
            <Input
              id="project-title"
              required
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="e.g. Literature review on transformer efficiency"
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="project-description">Description (optional)</Label>
            <Input
              id="project-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>

          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" disabled={isSubmitting || title.trim().length === 0}>
              {isSubmitting ? 'Creating…' : 'Create project'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
