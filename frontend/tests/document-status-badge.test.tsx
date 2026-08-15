import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { DocumentStatusBadge } from '@/components/documents/DocumentStatusBadge';
import { DOCUMENT_STATUSES } from '@/types/api';

describe('DocumentStatusBadge', () => {
  it('renders a text label for every status (not colour alone)', () => {
    const labels: Record<string, string> = {
      pending: 'Pending',
      processing: 'Processing',
      ready: 'Ready',
      failed: 'Failed',
    };

    for (const status of DOCUMENT_STATUSES) {
      const { unmount } = render(<DocumentStatusBadge status={status} />);
      expect(screen.getByText(labels[status]!)).toBeInTheDocument();
      unmount();
    }
  });

  it('renders the ready status with a checkmark glyph', () => {
    render(<DocumentStatusBadge status="ready" />);
    expect(screen.getByText('Ready')).toBeInTheDocument();
    expect(screen.getByText('✓')).toBeInTheDocument();
  });
});
