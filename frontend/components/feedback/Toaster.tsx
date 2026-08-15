'use client';

import { useToast, type ToastVariant } from '@/lib/toast/toast-context';
import { cn } from '@/lib/utils/cn';

//: Status is conveyed by glyph and text as well as colour (design §5.9).
const VARIANT_STYLES: Record<ToastVariant, { className: string; glyph: string; label: string }> = {
  success: {
    className: 'border-success/30 bg-success/10 text-success',
    glyph: '✓',
    label: 'Success',
  },
  error: {
    className: 'border-destructive/30 bg-destructive/10 text-destructive',
    glyph: '✕',
    label: 'Error',
  },
  info: {
    className: 'border-info/30 bg-info/10 text-info',
    glyph: 'ℹ',
    label: 'Notice',
  },
};

/**
 * Renders the toast queue. Announced politely so it does not steal focus
 * (design §5.9 live regions).
 */
export function Toaster(): React.JSX.Element {
  const { toasts, dismiss } = useToast();

  return (
    <div
      aria-live="polite"
      aria-atomic="false"
      className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2"
    >
      {toasts.map((toast) => {
        const style = VARIANT_STYLES[toast.variant];
        return (
          <div
            key={toast.id}
            role="status"
            className={cn(
              'pointer-events-auto flex items-start gap-3 rounded-surface border px-4 py-3 text-body-sm shadow-lg',
              'duration-200 animate-in fade-in slide-in-from-bottom-2',
              style.className,
            )}
          >
            <span aria-hidden="true" className="font-mono">
              {style.glyph}
            </span>
            <span className="sr-only">{style.label}:</span>
            <span className="flex-1">{toast.message}</span>
            <button
              type="button"
              onClick={() => dismiss(toast.id)}
              className="text-caption underline-offset-2 hover:underline"
              aria-label="Dismiss notification"
            >
              Dismiss
            </button>
          </div>
        );
      })}
    </div>
  );
}
