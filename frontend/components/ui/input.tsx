import { forwardRef } from 'react';

import { cn } from '@/lib/utils/cn';

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

/**
 * Neo Brutalism input: heavy border, square corners, clear focus with yellow ring
 */
export const Input = forwardRef<HTMLInputElement, InputProps>(({ className, ...props }, ref) => {
  return (
    <input
      ref={ref}
      className={cn(
        'flex h-12 w-full rounded-control border-panel border-input bg-card px-4 py-3 text-body font-reading',
        'placeholder:text-muted-foreground placeholder:font-reading',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'aria-invalid:border-destructive',
        className,
      )}
      {...props}
    />
  );
});
Input.displayName = 'Input';
