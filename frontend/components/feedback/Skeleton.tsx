import { cn } from '@/lib/utils/cn';

/** Gentle shimmer skeleton, matching the geometry of the content it precedes
 * so there is no layout shift on arrival (design §5.3, §14.5). */
export function Skeleton({ className }: { className?: string }): React.JSX.Element {
  return <div className={cn('animate-pulse rounded-surface bg-muted', className)} />;
}
