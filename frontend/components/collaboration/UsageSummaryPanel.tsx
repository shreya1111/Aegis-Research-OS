'use client';

import { useCallback, useEffect, useState } from 'react';

import { getUsage } from '@/lib/api/collaboration';
import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import type { ProjectUsage } from '@/types/api';

import { Skeleton } from '@/components/feedback/Skeleton';
import { Alert } from '@/components/ui/alert';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

function formatNumber(value: number): string {
  return value.toLocaleString();
}

function formatCost(value: number): string {
  // Recorded costs are estimates; six decimals would read as false precision.
  return `$${value.toFixed(value < 1 ? 4 : 2)}`;
}

export function UsageSummaryPanel({ projectId }: { projectId: string }): React.JSX.Element {
  const { getValidAccessToken } = useAuth();
  const [usage, setUsage] = useState<ProjectUsage | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const token = await getValidAccessToken();
      if (token) setUsage(await getUsage(token, projectId));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Could not load usage.');
    } finally {
      setIsLoading(false);
    }
  }, [getValidAccessToken, projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  const totals = [
    { label: 'Questions answered', value: usage ? formatNumber(usage.run_count) : '—' },
    { label: 'Agent steps', value: usage ? formatNumber(usage.trace_count) : '—' },
    { label: 'Tokens used', value: usage ? formatNumber(usage.tokens_used) : '—' },
    { label: 'Estimated cost', value: usage ? formatCost(usage.estimated_cost) : '—' },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Usage</CardTitle>
        <CardDescription>
          Derived from the recorded reasoning traces, so it always matches the trace panel.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {error ? <Alert variant="destructive">{error}</Alert> : null}

        {isLoading ? (
          <Skeleton className="h-20 w-full" />
        ) : (
          <>
            <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {totals.map((item) => (
                <div key={item.label} className="flex flex-col gap-1">
                  <dt className="text-body-sm text-muted-foreground">{item.label}</dt>
                  <dd className="text-h3 font-semibold">{item.value}</dd>
                </div>
              ))}
            </dl>

            {usage && usage.by_agent.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-body-sm">
                  <caption className="sr-only">Usage by agent</caption>
                  <thead>
                    <tr className="border-b text-left text-muted-foreground">
                      <th scope="col" className="py-2 font-medium">
                        Agent
                      </th>
                      <th scope="col" className="py-2 text-right font-medium">
                        Steps
                      </th>
                      <th scope="col" className="py-2 text-right font-medium">
                        Tokens
                      </th>
                      <th scope="col" className="py-2 text-right font-medium">
                        Cost
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {usage.by_agent.map((agent) => (
                      <tr key={agent.agent_name} className="border-b last:border-0">
                        <th scope="row" className="py-2 text-left font-normal">
                          {agent.agent_name}
                        </th>
                        <td className="py-2 text-right">{formatNumber(agent.trace_count)}</td>
                        <td className="py-2 text-right">{formatNumber(agent.tokens_used)}</td>
                        <td className="py-2 text-right">{formatCost(agent.estimated_cost)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-body-sm text-muted-foreground">
                No agent runs recorded yet. Usage appears once a question is answered.
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
