export interface EmptyStateProps {
  title: string;
  description: string;
  action?: React.ReactNode;
}

/**
 * Onboarding, not apology (design §14.4): explains what belongs here and
 * offers the single action that fills it. Never renders fake sample data.
 */
export function EmptyState({ title, description, action }: EmptyStateProps): React.JSX.Element {
  return (
    <div className="flex flex-col items-center gap-3 rounded-surface border border-dashed px-6 py-16 text-center">
      <h3 className="text-h3 font-semibold">{title}</h3>
      <p className="max-w-sm text-body-sm text-muted-foreground">{description}</p>
      {action}
    </div>
  );
}
