import { cn } from '@/lib/utils/cn';
import type { DocumentStatus } from '@/types/api';

/**
 * Status shown with a glyph and label as well as colour, never colour alone
 * (design §5.6, §5.9). Colour mapping follows the domain-specific meanings in
 * design §5.6: ready→success, processing/pending→info, failed→destructive.
 */
const STATUS_STYLES: Record<DocumentStatus, { className: string; glyph: string; label: string }> = {
  pending: { className: 'border-info/30 bg-info/10 text-info', glyph: '◷', label: 'Pending' },
  processing: {
    className: 'border-info/30 bg-info/10 text-info',
    glyph: '↻',
    label: 'Processing',
  },
  ready: {
    className: 'border-success/30 bg-success/10 text-success',
    glyph: '✓',
    label: 'Ready',
  },
  failed: {
    className: 'border-destructive/30 bg-destructive/10 text-destructive',
    glyph: '✕',
    label: 'Failed',
  },
};

export function DocumentStatusBadge({ status }: { status: DocumentStatus }): React.JSX.Element {
  const style = STATUS_STYLES[status];
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-caption font-medium',
        style.className,
      )}
    >
      <span aria-hidden="true">{style.glyph}</span>
      {style.label}
    </span>
  );
}
