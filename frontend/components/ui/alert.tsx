import { cva, type VariantProps } from 'class-variance-authority';
import { forwardRef } from 'react';

import { cn } from '@/lib/utils/cn';

/**
 * Status is conveyed by icon and text as well as colour, never colour alone
 * (design §5.9). Callers supply the icon; this component only sets tone.
 */
const alertVariants = cva('flex items-start gap-3 rounded-surface border px-4 py-3 text-body-sm', {
  variants: {
    variant: {
      destructive: 'border-destructive/30 bg-destructive/10 text-destructive',
      warning: 'border-warning/30 bg-warning/10 text-warning',
      success: 'border-success/30 bg-success/10 text-success',
      info: 'border-info/30 bg-info/10 text-info',
    },
  },
  defaultVariants: {
    variant: 'info',
  },
});

export interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {}

export const Alert = forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant, role = 'alert', ...props }, ref) => (
    <div
      ref={ref}
      role={role}
      aria-live="assertive"
      className={cn(alertVariants({ variant }), className)}
      {...props}
    />
  ),
);
Alert.displayName = 'Alert';
