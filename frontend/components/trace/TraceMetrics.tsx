import type { TraceStep as TraceStepData } from '@/types/api';

export interface TraceMetricsProps {
  steps: TraceStepData[];
}

/** Aggregate cost/latency summary for a run (design §4.6 rule 3: traces are
 * "the data source for the cost-analysis section of the report"). */
export function TraceMetrics({ steps }: TraceMetricsProps): React.JSX.Element {
  const totalTokens = steps.reduce((sum, step) => sum + step.tokens_used, 0);
  const totalCost = steps.reduce((sum, step) => sum + step.estimated_cost, 0);
  const totalLatencyMs = steps.reduce((sum, step) => sum + step.latency_ms, 0);

  return (
    <dl className="grid grid-cols-3 gap-2 rounded-surface border bg-muted/40 px-3 py-2 text-center text-caption">
      <div>
        <dt className="text-muted-foreground">Steps</dt>
        <dd className="font-medium">{steps.length}</dd>
      </div>
      <div>
        <dt className="text-muted-foreground">Tokens</dt>
        <dd className="font-medium">{totalTokens}</dd>
      </div>
      <div>
        <dt className="text-muted-foreground">Cost</dt>
        <dd className="font-medium">${totalCost.toFixed(4)}</dd>
      </div>
      <div className="col-span-3">
        <dt className="text-muted-foreground">Total time</dt>
        <dd className="font-medium">{(totalLatencyMs / 1000).toFixed(1)}s</dd>
      </div>
    </dl>
  );
}
