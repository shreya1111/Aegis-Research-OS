export interface ComingSoonProps {
  title: string;
  description: string;
}

/**
 * Honest placeholder for a feature that is navigable but not yet built
 * (design §5.1: "unbuilt features show a labelled empty state, never
 * fabricated data").
 */
export function ComingSoon({ title, description }: ComingSoonProps): React.JSX.Element {
  return (
    <div className="container py-10">
      <div className="flex flex-col items-center gap-3 rounded-surface border border-dashed px-6 py-16 text-center">
        <span className="rounded-full bg-muted px-3 py-1 text-caption uppercase tracking-widest text-muted-foreground">
          Coming soon
        </span>
        <h2 className="text-h2 font-semibold">{title}</h2>
        <p className="max-w-md text-body-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}
