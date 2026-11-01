'use client';

import { useCallback, useEffect, useState } from 'react';

import { listActivity } from '@/lib/api/collaboration';
import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import type { ActivityEntry } from '@/types/api';

import { Skeleton } from '@/components/feedback/Skeleton';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const PAGE_SIZE = 20;

/** Human labels for the audit actions the backend records. An unknown action
 * falls back to its raw name rather than disappearing — the log must not hide
 * events it does not recognise. */
const ACTION_LABELS: Record<string, string> = {
  'document.uploaded': 'Uploaded a document',
  'document.deleted': 'Deleted a document',
  'query.executed': 'Asked a question',
  'report.generated': 'Generated a report',
  'report.failed': 'Report generation failed',
  'member.invited': 'Added a member',
  'member.role_changed': 'Changed a member role',
  'member.removed': 'Removed a member',
};

const ACTION_GLYPHS: Record<string, string> = {
  document: '📄',
  query: '💬',
  report: '📊',
  member: '👥',
};

function describe(entry: ActivityEntry): string {
  const label = ACTION_LABELS[entry.action] ?? entry.action;
  const context = entry.context ?? {};

  if (typeof context.filename === 'string') return `${label}: ${context.filename}`;
  if (typeof context.title === 'string') return `${label}: “${context.title}”`;
  if (typeof context.email === 'string') return `${label}: ${context.email}`;
  if (typeof context.role === 'string' && entry.action === 'member.role_changed') {
    return `${label} to ${context.role}`;
  }
  return label;
}

function formatTimestamp(value: string): string {
  return new Date(value).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

export function ActivityFeed({ projectId }: { projectId: string }): React.JSX.Element {
  const { getValidAccessToken } = useAuth();

  const [entries, setEntries] = useState<ActivityEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPage = useCallback(
    async (page: number) => {
      setIsLoading(true);
      setError(null);
      try {
        const token = await getValidAccessToken();
        if (!token) return;
        const result = await listActivity(token, projectId, { page, pageSize: PAGE_SIZE });
        setEntries((previous) => (page === 1 ? result.items : [...previous, ...result.items]));
        setTotal(result.total);
      } catch (caught) {
        setError(caught instanceof ApiError ? caught.message : 'Could not load the activity log.');
      } finally {
        setIsLoading(false);
      }
    },
    [getValidAccessToken, projectId],
  );

  useEffect(() => {
    void loadPage(1);
  }, [loadPage]);

  const hasMore = entries.length < total;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Activity</CardTitle>
        <CardDescription>
          What has happened in this workspace, newest first. Only action summaries are recorded —
          never document text or question content.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {error ? <Alert variant="destructive">{error}</Alert> : null}

        {isLoading && entries.length === 0 ? (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : entries.length === 0 ? (
          <p className="text-body-sm text-muted-foreground">
            Nothing yet. Upload a document or ask a question to start the trail.
          </p>
        ) : (
          <ol className="flex flex-col divide-y" aria-label="Project activity">
            {entries.map((entry) => (
              <li key={entry.id} className="flex items-start gap-3 py-3">
                <span aria-hidden="true" className="text-lg leading-6">
                  {ACTION_GLYPHS[entry.entity_type ?? ''] ?? '•'}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-body-sm font-medium break-words">{describe(entry)}</p>
                  <p className="text-body-sm text-muted-foreground">
                    {entry.actor_name ?? 'A former member'} · {formatTimestamp(entry.created_at)}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        )}

        {hasMore ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={isLoading}
            onClick={() => void loadPage(Math.floor(entries.length / PAGE_SIZE) + 1)}
          >
            {isLoading ? 'Loading…' : 'Load more'}
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}
