import { cva, type VariantProps } from 'class-variance-authority';
import { forwardRef } from 'react';

import { cn } from '@/lib/utils/cn';

/**
 * Neo Brutalism alert: heavy border with optional colored background
 */
const alertVariants = cva('flex items-start gap-3 rounded-control border-panel px-4 py-3 shadow-brutal-sm text-small font-reading', {
  variants: {
    variant: {
      destructive: 'border-foreground bg-destructive/20 text-foreground',
      warning: 'border-foreground bg-accent/20 text-foreground',
      success: 'border-foreground bg-success/20 text-foreground',
      info: 'border-foreground bg-card text-foreground',
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

export const AlertDescription = forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('text-sm [&_p]:leading-relaxed', className)} {...props} />
));
AlertDescription.displayName = 'AlertDescription';
