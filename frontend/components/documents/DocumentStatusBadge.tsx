import { CheckCircle2, Clock, Loader2, XCircle, type LucideIcon } from 'lucide-react';

import { cn } from '@/lib/utils/cn';
import type { DocumentStatus } from '@/types/api';

/**
 * Status shown with an icon and label as well as colour, never colour alone
 * (design §5.6, §5.9). Colour mapping follows the domain-specific meanings in
 * design §5.6: ready→success, processing/pending→info, failed→destructive.
 */
const STATUS_STYLES: Record<
  DocumentStatus,
  { className: string; Icon: LucideIcon; label: string; spin?: boolean }
> = {
  pending: { className: 'border-info/30 bg-info/10 text-info', Icon: Clock, label: 'Pending' },
  processing: {
    className: 'border-info/30 bg-info/10 text-info',
    Icon: Loader2,
    label: 'Processing',
    spin: true,
  },
  ready: {
    className: 'border-success/30 bg-success/10 text-success',
    Icon: CheckCircle2,
    label: 'Ready',
  },
  failed: {
    className: 'border-destructive/30 bg-destructive/10 text-destructive',
    Icon: XCircle,
    label: 'Failed',
  },
};

export function DocumentStatusBadge({ status }: { status: DocumentStatus }): React.JSX.Element {
  const style = STATUS_STYLES[status];
  const Icon = style.Icon;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-caption font-medium',
        style.className,
      )}
    >
      <Icon className={cn('size-3.5', style.spin && 'animate-spin')} aria-hidden />
      {style.label}
    </span>
  );
}
