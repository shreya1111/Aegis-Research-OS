import { cn } from '@/lib/utils/cn';
import type { TraceStep as TraceStepData } from '@/types/api';

export interface TraceStepProps {
  step: TraceStepData;
}

/** One agent-node invocation in the Reasoning Trace panel (design §4.6 rule 3,
 * §5.7): agent name, what it produced, and its cost — the debugger and demo
 * feature described in design §4.6. */
export function TraceStep({ step }: TraceStepProps): React.JSX.Element {
  const isFailed = step.status === 'failed';

  return (
    <li
      className={cn(
        'flex flex-col gap-1 rounded-surface border px-3 py-2 text-body-sm',
        isFailed ? 'border-destructive/40 bg-destructive/5' : 'border-border bg-card',
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium">{step.agent_name}</span>
        <span
          className={cn(
            'rounded-full px-2 py-0.5 text-caption font-medium',
            isFailed ? 'bg-destructive/15 text-destructive' : 'bg-success/15 text-success',
          )}
        >
          {step.status}
        </span>
      </div>
      <p className="text-caption text-muted-foreground">
        {step.output_summary || step.input_summary}
      </p>
      <div className="flex gap-3 text-caption text-muted-foreground">
        <span>{Math.round(step.latency_ms)} ms</span>
        {step.tokens_used > 0 && <span>{step.tokens_used} tokens</span>}
        {step.estimated_cost > 0 && <span>${step.estimated_cost.toFixed(4)}</span>}
      </div>
    </li>
  );
}
