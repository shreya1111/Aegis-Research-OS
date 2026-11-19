import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { TraceMetrics } from '@/components/trace/TraceMetrics';
import { TraceStep } from '@/components/trace/TraceStep';
import type { TraceStep as TraceStepData } from '@/types/api';

function makeStep(overrides: Partial<TraceStepData> = {}): TraceStepData {
  return {
    id: 's1',
    agent_name: 'retrieval',
    input_summary: 'query: transformers',
    output_summary: 'found 8 chunks',
    tokens_used: 120,
    latency_ms: 842.4,
    estimated_cost: 0.0012,
    status: 'completed',
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  } as TraceStepData;
}

describe('TraceStep', () => {
  it('shows the agent, its output summary, and its cost', () => {
    render(
      <ul>
        <TraceStep step={makeStep()} />
      </ul>,
    );

    expect(screen.getByText('retrieval')).toBeInTheDocument();
    expect(screen.getByText('completed')).toBeInTheDocument();
    expect(screen.getByText('found 8 chunks')).toBeInTheDocument();
    expect(screen.getByText('842 ms')).toBeInTheDocument();
    expect(screen.getByText('120 tokens')).toBeInTheDocument();
    expect(screen.getByText('$0.0012')).toBeInTheDocument();
  });

  it('falls back to the input summary when there is no output yet', () => {
    render(
      <ul>
        <TraceStep step={makeStep({ output_summary: '' })} />
      </ul>,
    );

    expect(screen.getByText('query: transformers')).toBeInTheDocument();
  });

  it('hides token and cost figures when they are zero', () => {
    render(
      <ul>
        <TraceStep step={makeStep({ tokens_used: 0, estimated_cost: 0 })} />
      </ul>,
    );

    expect(screen.queryByText(/tokens/)).not.toBeInTheDocument();
    expect(screen.queryByText(/^\$/)).not.toBeInTheDocument();
  });

  it('marks a failed step visibly', () => {
    render(
      <ul>
        <TraceStep step={makeStep({ status: 'failed' })} />
      </ul>,
    );

    expect(screen.getByText('failed')).toHaveClass('text-destructive');
  });
});

describe('TraceMetrics', () => {
  it('totals tokens, cost, and time across steps', () => {
    render(
      <TraceMetrics
        steps={[
          makeStep({ id: 'a', tokens_used: 100, estimated_cost: 0.001, latency_ms: 1000 }),
          makeStep({ id: 'b', tokens_used: 250, estimated_cost: 0.0025, latency_ms: 2500 }),
        ]}
      />,
    );

    expect(screen.getByText('Steps').nextSibling).toHaveTextContent('2');
    expect(screen.getByText('Tokens').nextSibling).toHaveTextContent('350');
    expect(screen.getByText('Cost').nextSibling).toHaveTextContent('$0.0035');
    expect(screen.getByText('Total time').nextSibling).toHaveTextContent('3.5s');
  });

  it('renders zeros for an empty run', () => {
    render(<TraceMetrics steps={[]} />);

    expect(screen.getByText('Steps').nextSibling).toHaveTextContent('0');
    expect(screen.getByText('Cost').nextSibling).toHaveTextContent('$0.0000');
  });
});
