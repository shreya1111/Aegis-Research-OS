import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { UsageSummaryPanel } from '@/components/collaboration/UsageSummaryPanel';
import { ApiError } from '@/lib/api/client';
import { getUsage } from '@/lib/api/collaboration';
import type { ProjectUsage } from '@/types/api';

vi.mock('@/lib/api/collaboration', () => ({ getUsage: vi.fn() }));
// A stable reference, as in the real hook: components list it as an effect dependency.
const getValidAccessToken = vi.hoisted(() => () => Promise.resolve('token-1'));
vi.mock('@/lib/auth/auth-context', () => ({ useAuth: () => ({ getValidAccessToken }) }));

const usage: ProjectUsage = {
  run_count: 12,
  trace_count: 84,
  tokens_used: 15300,
  estimated_cost: 0.4213,
  by_agent: [
    { agent_name: 'retrieval', trace_count: 40, tokens_used: 9000, estimated_cost: 0.25 },
    { agent_name: 'critic', trace_count: 44, tokens_used: 6300, estimated_cost: 0.1713 },
  ],
} as ProjectUsage;

beforeEach(() => {
  vi.mocked(getUsage).mockReset();
});

describe('UsageSummaryPanel', () => {
  it('renders totals and the per-agent breakdown', async () => {
    vi.mocked(getUsage).mockResolvedValue(usage);

    render(<UsageSummaryPanel projectId="p1" />);

    expect(await screen.findByText('Questions answered')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText((15300).toLocaleString())).toBeInTheDocument();
    expect(screen.getByText('$0.4213')).toBeInTheDocument();
    expect(screen.getByRole('rowheader', { name: 'retrieval' })).toBeInTheDocument();
    expect(screen.getByRole('rowheader', { name: 'critic' })).toBeInTheDocument();
    expect(getUsage).toHaveBeenCalledWith('token-1', 'p1');
  });

  it('shows a message when no agent has run yet', async () => {
    vi.mocked(getUsage).mockResolvedValue({
      ...usage,
      run_count: 0,
      trace_count: 0,
      tokens_used: 0,
      estimated_cost: 0,
      by_agent: [],
    });

    render(<UsageSummaryPanel projectId="p1" />);

    expect(await screen.findByText(/no agent runs recorded yet/i)).toBeInTheDocument();
  });

  it('shows the API error message when loading fails', async () => {
    vi.mocked(getUsage).mockRejectedValue(
      new ApiError({ code: 'FORBIDDEN', message: 'Not allowed.', status: 403 }),
    );

    render(<UsageSummaryPanel projectId="p1" />);

    expect(await screen.findByText('Not allowed.')).toBeInTheDocument();
  });

  it('falls back to a generic message for unexpected failures', async () => {
    vi.mocked(getUsage).mockRejectedValue(new Error('boom'));

    render(<UsageSummaryPanel projectId="p1" />);

    expect(await screen.findByText('Could not load usage.')).toBeInTheDocument();
  });
});
