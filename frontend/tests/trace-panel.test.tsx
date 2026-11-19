import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { TracePanel } from '@/components/trace/TracePanel';
import { getTrace } from '@/lib/api/query';
import type { TraceStep } from '@/types/api';

vi.mock('@/lib/api/query', () => ({ getTrace: vi.fn() }));
// A stable reference, as in the real hook: components list it as an effect dependency.
const getValidAccessToken = vi.hoisted(() => () => Promise.resolve('token-1'));
vi.mock('@/lib/auth/auth-context', () => ({ useAuth: () => ({ getValidAccessToken }) }));

const step: TraceStep = {
  id: 's1',
  agent_name: 'supervisor',
  input_summary: 'plan the work',
  output_summary: 'planned 2 subtasks',
  tokens_used: 50,
  latency_ms: 300,
  estimated_cost: 0.0005,
  status: 'completed',
  created_at: '2026-01-01T00:00:00Z',
} as TraceStep;

beforeEach(() => {
  vi.mocked(getTrace).mockReset();
});

describe('TracePanel', () => {
  it('shows the empty state before any run exists and does not call the API', () => {
    render(<TracePanel projectId="p1" runId={null} />);

    expect(screen.getByRole('heading', { name: 'Reasoning Trace' })).toBeInTheDocument();
    expect(getTrace).not.toHaveBeenCalled();
  });

  it('loads and renders the steps of the active run', async () => {
    vi.mocked(getTrace).mockResolvedValue({ run_id: 'r1', steps: [step] });

    render(<TracePanel projectId="p1" runId="r1" />);

    expect(await screen.findByText('supervisor')).toBeInTheDocument();
    expect(screen.getByText('planned 2 subtasks')).toBeInTheDocument();
    expect(getTrace).toHaveBeenCalledWith('token-1', 'p1', 'r1');
  });

  it('stays usable when the trace request fails', async () => {
    vi.mocked(getTrace).mockRejectedValue(new Error('network down'));

    render(<TracePanel projectId="p1" runId="r1" />);

    await waitFor(() => expect(getTrace).toHaveBeenCalled());
    expect(screen.getByRole('heading', { name: 'Reasoning Trace' })).toBeInTheDocument();
  });

  it('collapses and expands', async () => {
    render(<TracePanel projectId="p1" runId={null} />);

    await userEvent.click(screen.getByRole('button', { name: /collapse reasoning trace panel/i }));
    expect(screen.queryByRole('heading', { name: 'Reasoning Trace' })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /expand reasoning trace panel/i }));
    expect(screen.getByRole('heading', { name: 'Reasoning Trace' })).toBeInTheDocument();
  });
});
