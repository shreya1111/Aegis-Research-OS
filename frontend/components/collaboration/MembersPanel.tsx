'use client';

import { useCallback, useEffect, useState } from 'react';

import { listMembers, inviteMember, removeMember, updateMemberRole } from '@/lib/api/collaboration';
import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import { useToast } from '@/lib/toast/toast-context';
import type { ProjectMember, ProjectRole } from '@/types/api';

import { Skeleton } from '@/components/feedback/Skeleton';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

/** Invitable roles — ownership is transferred, never invited (design §2.2). */
type InvitableRole = Exclude<ProjectRole, 'owner'>;

export interface MembersPanelProps {
  projectId: string;
  /** The caller's role. Controls are hidden for anyone who is not the owner;
   * the server enforces the same rule regardless. */
  role: ProjectRole | null;
}

function roleLabel(role: ProjectRole): string {
  return role === 'owner' ? 'Owner' : role === 'editor' ? 'Editor' : 'Viewer';
}

function roleHint(role: ProjectRole): string {
  if (role === 'owner') return 'Full control, including membership and deletion.';
  if (role === 'editor') return 'Can add documents, ask questions, and generate reports.';
  return 'Read-only access to documents, answers, and artifacts.';
}

export function MembersPanel({ projectId, role }: MembersPanelProps): React.JSX.Element {
  const { getValidAccessToken } = useAuth();
  const { notify } = useToast();

  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isMutating, setIsMutating] = useState(false);
  const [email, setEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<InvitableRole>('viewer');

  const isOwner = role === 'owner';

  const loadMembers = useCallback(async () => {
    setIsLoading(true);
    try {
      const token = await getValidAccessToken();
      if (token) {
        setMembers(await listMembers(token, projectId));
      }
    } catch (caught) {
      notify('error', caught instanceof ApiError ? caught.message : 'Could not load members.');
    } finally {
      setIsLoading(false);
    }
  }, [getValidAccessToken, notify, projectId]);

  useEffect(() => {
    void loadMembers();
  }, [loadMembers]);

  async function handleInvite(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const trimmed = email.trim();
    if (!trimmed) return;

    setIsMutating(true);
    try {
      const token = await getValidAccessToken();
      if (!token) {
        notify('error', 'Your session has expired. Please sign in again.');
        return;
      }
      setMembers(await inviteMember(token, projectId, { email: trimmed, role: inviteRole }));
      setEmail('');
      notify('success', `${trimmed} now has ${inviteRole} access.`);
    } catch (caught) {
      notify('error', caught instanceof ApiError ? caught.message : 'Could not add that member.');
    } finally {
      setIsMutating(false);
    }
  }

  async function handleRoleChange(member: ProjectMember, next: InvitableRole): Promise<void> {
    if (!member.id) return;
    setIsMutating(true);
    try {
      const token = await getValidAccessToken();
      if (!token) return;
      setMembers(await updateMemberRole(token, projectId, member.id, next));
      notify('success', `${member.name} is now ${next}.`);
    } catch (caught) {
      notify('error', caught instanceof ApiError ? caught.message : 'Could not change the role.');
    } finally {
      setIsMutating(false);
    }
  }

  async function handleRemove(member: ProjectMember): Promise<void> {
    if (!member.id) return;
    setIsMutating(true);
    try {
      const token = await getValidAccessToken();
      if (!token) return;
      setMembers(await removeMember(token, projectId, member.id));
      notify('success', `${member.name} no longer has access.`);
    } catch (caught) {
      notify('error', caught instanceof ApiError ? caught.message : 'Could not remove that member.');
    } finally {
      setIsMutating(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Members</CardTitle>
        <CardDescription>
          People with access to this workspace. Invitations take effect immediately — the account
          must already exist.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        {isLoading ? (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : (
          <ul className="flex flex-col divide-y" aria-label="Project members">
            {members.map((member) => (
              <li
                key={member.user_id}
                className="flex flex-wrap items-center justify-between gap-3 py-3"
              >
                <div className="min-w-0">
                  <p className="truncate text-body-sm font-medium">{member.name}</p>
                  <p className="truncate text-body-sm text-muted-foreground">{member.email}</p>
                </div>

                <div className="flex items-center gap-2">
                  {isOwner && member.role !== 'owner' ? (
                    <>
                      <Label htmlFor={`role-${member.user_id}`} className="sr-only">
                        Role for {member.name}
                      </Label>
                      <select
                        id={`role-${member.user_id}`}
                        className="h-9 rounded-md border bg-background px-2 text-body-sm"
                        value={member.role}
                        disabled={isMutating}
                        onChange={(event) =>
                          void handleRoleChange(member, event.target.value as InvitableRole)
                        }
                      >
                        <option value="viewer">Viewer</option>
                        <option value="editor">Editor</option>
                      </select>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={isMutating}
                        onClick={() => void handleRemove(member)}
                      >
                        Remove
                      </Button>
                    </>
                  ) : (
                    <Badge variant={member.role === 'owner' ? 'default' : 'secondary'}>
                      {roleLabel(member.role)}
                    </Badge>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}

        {isOwner ? (
          <form className="flex flex-col gap-3 rounded-md border p-4" onSubmit={handleInvite}>
            <p className="text-body-sm font-medium">Invite someone</p>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <div className="flex-1">
                <Label htmlFor="invite-email">Email address</Label>
                <Input
                  id="invite-email"
                  type="email"
                  required
                  autoComplete="off"
                  placeholder="collaborator@university.edu"
                  className="mt-1"
                  value={email}
                  disabled={isMutating}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="invite-role">Role</Label>
                <select
                  id="invite-role"
                  className="mt-1 h-10 rounded-md border bg-background px-2 text-body-sm"
                  value={inviteRole}
                  disabled={isMutating}
                  onChange={(event) => setInviteRole(event.target.value as InvitableRole)}
                >
                  <option value="viewer">Viewer</option>
                  <option value="editor">Editor</option>
                </select>
              </div>
              <Button type="submit" disabled={isMutating || !email.trim()}>
                {isMutating ? 'Adding…' : 'Add member'}
              </Button>
            </div>
            <p className="text-body-sm text-muted-foreground">
              Editor: {roleHint('editor')} Viewer: {roleHint('viewer')}
            </p>
          </form>
        ) : (
          <Alert>
            You have {role ? roleLabel(role).toLowerCase() : 'read-only'} access. Only the project
            owner can change who is a member.
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
