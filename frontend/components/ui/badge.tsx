import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils/cn';

/**
 * Neo Brutalism badge: compact box with heavy border and optional color fill
 */
const badgeVariants = cva(
  'inline-flex items-center rounded-control border-annotation px-2 py-1 brutal-label font-emphasis',
  {
    variants: {
      variant: {
        default: 'border-foreground bg-card text-foreground',
        primary: 'border-foreground bg-primary text-primary-foreground',
        secondary: 'border-foreground bg-secondary text-secondary-foreground',
        destructive: 'border-foreground bg-destructive text-destructive-foreground',
        accent: 'border-foreground bg-accent text-accent-foreground',
        outline: 'border-foreground text-foreground',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
