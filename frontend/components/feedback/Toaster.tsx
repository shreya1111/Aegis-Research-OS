'use client';

import { AlertCircle, CheckCircle2, Info, X, type LucideIcon } from 'lucide-react';

import { useToast, type ToastVariant } from '@/lib/toast/toast-context';
import { cn } from '@/lib/utils/cn';

//: Status is conveyed by icon and text as well as colour (design §5.9).
const VARIANT_STYLES: Record<ToastVariant, { className: string; Icon: LucideIcon; label: string }> =
  {
    success: {
      className: 'border-success/30 bg-success/10 text-success',
      Icon: CheckCircle2,
      label: 'Success',
    },
    error: {
      className: 'border-destructive/30 bg-destructive/10 text-destructive',
      Icon: AlertCircle,
      label: 'Error',
    },
    info: {
      className: 'border-info/30 bg-info/10 text-info',
      Icon: Info,
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
        const Icon = style.Icon;
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
            <Icon className="mt-0.5 size-4 shrink-0" aria-hidden />
            <span className="sr-only">{style.label}:</span>
            <span className="flex-1">{toast.message}</span>
            <button
              type="button"
              onClick={() => dismiss(toast.id)}
              className="shrink-0 rounded-control p-0.5 opacity-70 transition-opacity hover:opacity-100"
              aria-label="Dismiss notification"
            >
              <X className="size-3.5" aria-hidden />
            </button>
          </div>
        );
      })}
    </div>
  );
}
