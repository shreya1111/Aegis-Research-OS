import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { StreamingMessage } from '@/components/chat/StreamingMessage';
import type { Citation } from '@/types/api';

describe('StreamingMessage', () => {
  it('renders plain text with no markers unchanged', () => {
    render(<StreamingMessage content="No citations here." citations={[]} />);

    expect(screen.getByText('No citations here.')).toBeInTheDocument();
  });

  it('renders a resolved marker as a citation chip', () => {
    const citations: Citation[] = [{ marker: 'Doc 1, p.1', chunk_id: 'c1', document_id: 'd1' }];

    render(<StreamingMessage content="A claim, cited [Doc 1, p.1]." citations={citations} />);

    expect(screen.getByRole('button', { name: 'Doc 1, p.1' })).toBeInTheDocument();
  });

  it('renders an unresolved marker as plain bracketed text', () => {
    render(<StreamingMessage content="A fabricated claim [Doc 99, p.1]." citations={[]} />);

    expect(screen.getByText(/\[Doc 99, p\.1\]/)).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('renders multiple citation markers independently', () => {
    const citations: Citation[] = [
      { marker: 'Doc 1, p.1', chunk_id: 'c1', document_id: 'd1' },
      { marker: 'Doc 2, p.3', chunk_id: 'c2', document_id: 'd2' },
    ];

    render(
      <StreamingMessage
        content="First [Doc 1, p.1] and second [Doc 2, p.3]."
        citations={citations}
      />,
    );

    expect(screen.getByRole('button', { name: 'Doc 1, p.1' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Doc 2, p.3' })).toBeInTheDocument();
  });
});
