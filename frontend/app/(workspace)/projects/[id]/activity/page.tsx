'use client';

import { useParams } from 'next/navigation';

import { ActivityFeed } from '@/components/collaboration/ActivityFeed';
import { UsageSummaryPanel } from '@/components/collaboration/UsageSummaryPanel';

/**
 * Activity tab (design §5.2, Phase 10 FR-H7/H9): the project's audit trail and
 * the spend it has accumulated, side by side so "what happened" and "what it
 * cost" are answered together.
 */
export default function ProjectActivityPage(): React.JSX.Element {
  const params = useParams<{ id: string }>();

  return (
    <div className="container flex max-w-3xl flex-col gap-6 py-10">
      <div>
        <h1 className="text-h1 font-semibold">Activity</h1>
        <p className="text-body-sm text-muted-foreground">
          Recent work in this workspace and the resources it has used.
        </p>
      </div>

      <UsageSummaryPanel projectId={params.id} />
      <ActivityFeed projectId={params.id} />
    </div>
  );
}
