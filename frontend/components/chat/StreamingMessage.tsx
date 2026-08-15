import { Fragment } from 'react';

import { CitationChip } from '@/components/chat/CitationChip';
import type { Citation } from '@/types/api';

//: Mirrors the backend's marker pattern (design §8.8: `_MARKER_PATTERN`) so
//: the exact same `[...]`-bracketed spans become clickable chips here.
const MARKER_PATTERN = /\[([^[\]]+)\]/g;

export interface StreamingMessageProps {
  content: string;
  citations: Citation[];
}

/**
 * Renders an assistant answer with every citation marker turned into a
 * clickable {@link CitationChip} (design §5.7). Named for the eventual
 * progressive-rendering case (design §3.4: "Streaming response (SSE /
 * chunked)"); today it renders the complete answer once the request
 * settles, since the backend does not yet stream tokens.
 */
export function StreamingMessage({ content, citations }: StreamingMessageProps): React.JSX.Element {
  const citationsByMarker = new Map(citations.map((citation) => [citation.marker, citation]));

  const segments: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  // eslint-disable-next-line no-cond-assign -- standard exec-loop pattern
  while ((match = MARKER_PATTERN.exec(content)) !== null) {
    if (match.index > lastIndex) {
      segments.push(
        <Fragment key={`text-${lastIndex}`}>{content.slice(lastIndex, match.index)}</Fragment>,
      );
    }
    const marker = match[1] ?? '';
    segments.push(
      <CitationChip
        key={`citation-${match.index}`}
        marker={marker}
        citation={citationsByMarker.get(marker)}
      />,
    );
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < content.length) {
    segments.push(<Fragment key={`text-${lastIndex}`}>{content.slice(lastIndex)}</Fragment>);
  }

  return <p className="whitespace-pre-wrap">{segments}</p>;
}
