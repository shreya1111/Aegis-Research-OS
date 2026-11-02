import { AlertCircle, CheckCircle2 } from 'lucide-react';

import { cn } from '@/lib/utils/cn';
import type { HealthStatus } from '@/types/api';

export interface BackendStatusProps {
  /** Health payload, or `null` when the backend could not be reached. */
  health: HealthStatus | null;
}

/**
 * Reports whether the API is reachable.
 *
 * Status is conveyed by icon and text as well as colour, never colour alone
 * (design §5.9).
 */
export function BackendStatus({ health }: BackendStatusProps): React.JSX.Element {
  const isOnline = health !== null;
  const Icon = isOnline ? CheckCircle2 : AlertCircle;

  return (
    <div
      className={cn(
        'flex items-center gap-3 rounded-surface border px-4 py-3 text-body-sm',
        isOnline
          ? 'border-success/30 bg-success/10 text-success'
          : 'border-destructive/30 bg-destructive/10 text-destructive',
      )}
      role="status"
      aria-live="polite"
    >
      <Icon className="size-4 shrink-0" aria-hidden />
      {isOnline ? (
        <span>
          API reachable — <span className="font-mono">{health.service}</span> v
          <span className="font-mono">{health.version}</span> ({health.environment})
        </span>
      ) : (
        <span>API unreachable. Start the backend, then reload this page.</span>
      )}
    </div>
  );
}
