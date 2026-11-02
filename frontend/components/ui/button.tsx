import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { forwardRef } from 'react';

import { cn } from '@/lib/utils/cn';

/**
 * Neo Brutalism button: heavy outlines, solid offset shadows, immediate interaction.
 * Hover lifts the control up, press brings it back down. Square corners, bold text.
 */
const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-control font-emphasis uppercase transition-all duration-interaction disabled:pointer-events-none disabled:opacity-50 border-panel brutal-hover',
  {
    variants: {
      variant: {
        // Primary: yellow poster with black text
        primary: 'bg-primary text-primary-foreground border-foreground shadow-brutal',
        // Secondary: violet field with black text
        secondary: 'bg-secondary text-secondary-foreground border-foreground shadow-brutal',
        // Destructive: red signal with black text
        destructive: 'bg-destructive text-destructive-foreground border-foreground shadow-brutal',
        // Outline: cream/white bg with black border
        outline: 'border-foreground bg-card text-foreground shadow-brutal',
        // Ghost: minimal with border only
        ghost: 'border-foreground bg-transparent text-foreground hover:bg-accent hover:shadow-brutal',
        // Contrast: white panel for dark backgrounds
        contrast: 'bg-card text-card-foreground border-foreground shadow-brutal',
      },
      size: {
        sm: 'h-10 px-4 text-label',
        md: 'h-12 px-6 text-small',
        lg: 'h-14 px-8 text-body',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  /** Render as the single child element instead of a `<button>` (Radix Slot). */
  asChild?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Component = asChild ? Slot : 'button';
    return (
      <Component
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        {...props}
      />
    );
  },
);
Button.displayName = 'Button';
