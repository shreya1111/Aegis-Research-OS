import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { CitationChip } from '@/components/chat/CitationChip';
import type { Citation } from '@/types/api';

const documentCitation: Citation = {
  marker: 'Doc 1, p.2',
  chunk_id: 'c1',
  document_id: 'd1',
  page: 2,
};

const externalCitation: Citation = {
  marker: 'arXiv 1',
  external_source: { title: 'A Paper', url: 'https://example.com/paper', provider: 'arXiv' },
};

describe('CitationChip', () => {
  it('renders an unresolved marker as plain text, never as a chip', () => {
    render(<CitationChip marker="Doc 99, p.1" citation={undefined} />);

    expect(screen.getByText('[Doc 99, p.1]')).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('renders a resolved document citation as a clickable chip', () => {
    render(<CitationChip marker="Doc 1, p.2" citation={documentCitation} />);

    expect(screen.getByRole('button', { name: 'Doc 1, p.2' })).toBeInTheDocument();
  });

  it('opens a popover with page info for a document citation on click', async () => {
    render(<CitationChip marker="Doc 1, p.2" citation={documentCitation} />);

    await userEvent.click(screen.getByRole('button', { name: 'Doc 1, p.2' }));

    expect(screen.getByRole('dialog')).toHaveTextContent('Page 2');
  });

  it('opens a popover with the source link for an external citation', async () => {
    render(<CitationChip marker="arXiv 1" citation={externalCitation} />);

    await userEvent.click(screen.getByRole('button', { name: 'arXiv 1' }));

    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveTextContent('A Paper');
    expect(dialog).toHaveTextContent('arXiv');
    expect(screen.getByRole('link', { name: /view source/i })).toHaveAttribute(
      'href',
      'https://example.com/paper',
    );
  });

  it('closes the popover on Escape', async () => {
    render(<CitationChip marker="Doc 1, p.2" citation={documentCitation} />);

    await userEvent.click(screen.getByRole('button', { name: 'Doc 1, p.2' }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    await userEvent.keyboard('{Escape}');

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
