'use client';

import { useEffect, useId, useRef, useState } from 'react';

import { cn } from '@/lib/utils/cn';
import type { Citation } from '@/types/api';

export interface CitationChipProps {
  marker: string;
  citation: Citation | undefined;
}

/**
 * One inline citation marker (design §8.8, e.g. `[Doc 1, p.2]`), rendered as a
 * small clickable chip. A marker that never resolved against the citation map
 * (design §8.8 step 4 — the citation-validity enforcement point) renders as
 * plain, unstyled text instead of a chip: an unverifiable claim must never
 * look like a verified one.
 */
export function CitationChip({ marker, citation }: CitationChipProps): React.JSX.Element {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLSpanElement>(null);
  const popoverId = useId();

  useEffect(() => {
    if (!open) return;
    function handlePointerDown(event: PointerEvent): void {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    }
    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  if (!citation) {
    return <span className="text-muted-foreground">[{marker}]</span>;
  }

  return (
    <span ref={containerRef} className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-controls={popoverId}
        className={cn(
          'mx-0.5 inline-flex items-center rounded-full border border-primary/30 bg-primary/10',
          'px-1.5 py-0.5 text-caption font-medium text-primary hover:bg-primary/20',
        )}
      >
        {marker}
      </button>
      {open && (
        <span
          id={popoverId}
          role="dialog"
          aria-label={`Source for citation ${marker}`}
          className={cn(
            'absolute left-0 top-full z-20 mt-1 w-72 rounded-surface border bg-card p-3 text-left',
            'text-body-sm shadow-lg',
          )}
        >
          {citation.external_source ? (
            <>
              <p className="font-medium">{citation.external_source.title}</p>
              <p className="mt-1 text-caption text-muted-foreground">
                {citation.external_source.provider}
              </p>
              {citation.external_source.url && (
                <a
                  href={citation.external_source.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="mt-2 inline-block text-primary underline-offset-4 hover:underline"
                >
                  View source
                </a>
              )}
            </>
          ) : (
            <>
              <p className="font-medium">Document source</p>
              {typeof citation.page === 'number' && (
                <p className="mt-1 text-caption text-muted-foreground">Page {citation.page}</p>
              )}
            </>
          )}
        </span>
      )}
    </span>
  );
}
