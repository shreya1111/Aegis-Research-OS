/** Labelled empty state for the Reasoning Trace panel before any run has
 * happened (design §5.1 "placeholder honesty": unbuilt or unused features
 * show a labelled empty state, never fabricated data). */
export function TraceEmptyState(): React.JSX.Element {
  return (
    <div className="flex flex-col items-center gap-2 rounded-surface border border-dashed px-4 py-8 text-center">
      <p className="text-body-sm font-medium">No reasoning trace yet</p>
      <p className="max-w-xs text-caption text-muted-foreground">
        Ask a question in the chat to see each agent step — retrieval, summarisation, synthesis,
        review — appear here as it runs.
      </p>
    </div>
  );
}
