import * as LabelPrimitive from '@radix-ui/react-label';
import { forwardRef } from 'react';

import { cn } from '@/lib/utils/cn';

/**
 * Neo Brutalism label: small uppercase bold text
 */
export const Label = forwardRef<
  React.ComponentRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root>
>(({ className, ...props }, ref) => (
  <LabelPrimitive.Root
    ref={ref}
    className={cn('brutal-label', className)}
    {...props}
  />
));
Label.displayName = 'Label';
