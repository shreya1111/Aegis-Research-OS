import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { NodeDetailsSidebar } from '@/components/graph/NodeDetailsSidebar';
import type { NodeDetails } from '@/types/graph';

const details: NodeDetails = {
  node: {
    id: 'n1',
    name: 'Ada Lovelace',
    type: 'author',
    metadata: { affiliation: 'Analytical Engine Lab', papers: 3 },
    createdAt: '2026-01-01T00:00:00Z',
  },
  neighbors: [
    { id: 'n2', name: 'Machine learning', type: 'topic' },
    { id: 'n3', name: 'Royal Society', type: 'institution' },
  ],
  connections: [
    {
      id: 'e1',
      type: 'topic_membership',
      weight: 2.5,
      sourceId: 'n1',
      targetId: 'n2',
      metadata: {},
    },
    {
      id: 'e2',
      type: 'institutional_affiliation',
      weight: 1,
      sourceId: 'n3',
      targetId: 'n1',
      metadata: {},
    },
  ],
};

describe('NodeDetailsSidebar', () => {
  it('renders nothing when no node is selected', () => {
    const { container } = render(<NodeDetailsSidebar details={null} onClose={vi.fn()} />);

    expect(container).toBeEmptyDOMElement();
  });

  it('shows the node, its type, and its metadata', () => {
    render(<NodeDetailsSidebar details={details} onClose={vi.fn()} />);

    expect(screen.getByText('Ada Lovelace')).toBeInTheDocument();
    expect(screen.getByText('Author')).toBeInTheDocument();
    expect(screen.getByText('Analytical Engine Lab')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('lists connected nodes with a count', () => {
    render(<NodeDetailsSidebar details={details} onClose={vi.fn()} />);

    expect(screen.getByText('Connected Nodes (2)')).toBeInTheDocument();
    expect(screen.getByText('Machine learning')).toBeInTheDocument();
    expect(screen.getByText('Royal Society')).toBeInTheDocument();
  });

  it('labels relationship direction relative to the selected node', () => {
    render(<NodeDetailsSidebar details={details} onClose={vi.fn()} />);

    expect(screen.getByText('Relationships (2)')).toBeInTheDocument();
    expect(screen.getByText('Topic Membership')).toBeInTheDocument();
    expect(screen.getByText('Outgoing relationship')).toBeInTheDocument();
    expect(screen.getByText('Incoming relationship')).toBeInTheDocument();
    expect(screen.getByText('Weight: 2.5')).toBeInTheDocument();
  });

  it('omits the neighbour and relationship sections when there are none', () => {
    render(
      <NodeDetailsSidebar
        details={{ ...details, neighbors: [], connections: [] }}
        onClose={vi.fn()}
      />,
    );

    expect(screen.queryByText(/Connected Nodes/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Relationships/)).not.toBeInTheDocument();
  });

  it('calls onClose from the close button', async () => {
    const onClose = vi.fn();
    render(<NodeDetailsSidebar details={details} onClose={onClose} />);

    await userEvent.click(screen.getByRole('button'));

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
