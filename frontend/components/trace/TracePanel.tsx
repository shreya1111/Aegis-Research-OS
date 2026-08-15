'use client';

import { useCallback, useEffect, useState } from 'react';

import { getTrace } from '@/lib/api/query';
import { useAuth } from '@/lib/auth/auth-context';
import { cn } from '@/lib/utils/cn';
import type { TraceStep as TraceStepData } from '@/types/api';

import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/feedback/Skeleton';
import { TraceEmptyState } from '@/components/trace/TraceEmptyState';
import { TraceMetrics } from '@/components/trace/TraceMetrics';
import { TraceStep } from '@/components/trace/TraceStep';

export interface TracePanelProps {
  projectId: string;
  /** The active run to display, or `null` before any query has been sent. */
  runId: string | null;
}

//: Poll interval while a run is in flight (design §5.7: "poll or stream from
//: the traces endpoint"). The backend has no run-completion signal of its
//: own yet, so polling stops once a fixed number of consecutive polls return
//: an unchanged step count.
const POLL_INTERVAL_MS = 1500;
const MAX_STABLE_POLLS = 3;

/**
 * Collapsible "Reasoning Trace" right rail (design §5.1, §5.7): the live
 * sequence of agent steps for the current run. Collapsed by default on
 * narrow viewports so it never crowds the chat on mobile.
 */
export function TracePanel({ projectId, runId }: TracePanelProps): React.JSX.Element {
  const { getValidAccessToken } = useAuth();
  const [isOpen, setIsOpen] = useState(true);
  const [steps, setSteps] = useState<TraceStepData[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchTrace = useCallback(async (): Promise<number> => {
    if (!runId) return 0;
    try {
      const token = await getValidAccessToken();
      if (!token) return 0;
      const trace = await getTrace(token, projectId, runId);
      setSteps(trace.steps);
      return trace.steps.length;
    } catch {
      // The trace panel is a secondary, best-effort view: a transient
      // failure to fetch it must never disrupt the primary chat flow.
      return 0;
    }
  }, [getValidAccessToken, projectId, runId]);

  useEffect(() => {
    if (!runId) {
      setSteps([]);
      return;
    }

    let stablePollCount = 0;
    let lastStepCount = 0;
    let cancelled = false;

    setIsLoading(true);
    void fetchTrace()
      .then((count) => {
        lastStepCount = count;
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    const interval = window.setInterval(() => {
      void fetchTrace().then((count) => {
        if (cancelled) return;
        if (count === lastStepCount) {
          stablePollCount += 1;
        } else {
          stablePollCount = 0;
          lastStepCount = count;
        }
        if (stablePollCount >= MAX_STABLE_POLLS) {
          window.clearInterval(interval);
        }
      });
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [runId, fetchTrace]);

  return (
    <aside
      className={cn(
        'flex shrink-0 flex-col border-l bg-background transition-[width]',
        isOpen ? 'w-full max-w-sm' : 'w-12',
      )}
    >
      <div className="flex items-center justify-between border-b px-3 py-2">
        {isOpen && <h2 className="text-body-sm font-semibold">Reasoning Trace</h2>}
        <Button
          type="button"
          variant="ghost"
          size="sm"
          aria-expanded={isOpen}
          aria-label={isOpen ? 'Collapse reasoning trace panel' : 'Expand reasoning trace panel'}
          onClick={() => setIsOpen((current) => !current)}
        >
          <span aria-hidden="true">{isOpen ? '»' : '«'}</span>
        </Button>
      </div>

      {isOpen && (
        <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-3">
          {!runId && <TraceEmptyState />}

          {runId && isLoading && steps.length === 0 && (
            <div className="flex flex-col gap-2">
              {Array.from({ length: 3 }, (_, index) => (
                <Skeleton key={index} className="h-16 w-full" />
              ))}
            </div>
          )}

          {runId && steps.length > 0 && (
            <>
              <TraceMetrics steps={steps} />
              <ul className="flex flex-col gap-2">
                {steps.map((step) => (
                  <TraceStep key={step.id} step={step} />
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </aside>
  );
}
