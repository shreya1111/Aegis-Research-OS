import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ReportList } from '@/components/reports/ReportList';
import { exportReport, generateSummary } from '@/lib/api/reports';
import type { Report } from '@/types/report';

const notify = vi.fn();

vi.mock('@/lib/api/reports', () => ({ exportReport: vi.fn(), generateSummary: vi.fn() }));
// A stable reference, as in the real hook: components list it as an effect dependency.
const getValidAccessToken = vi.hoisted(() => () => Promise.resolve('token-1'));
vi.mock('@/lib/auth/auth-context', () => ({ useAuth: () => ({ getValidAccessToken }) }));
vi.mock('@/lib/toast/toast-context', () => ({ useToast: () => ({ notify }) }));

function makeReport(overrides: Partial<Report> = {}): Report {
  return {
    id: 'r1',
    project_id: 'p1',
    type: 'literature_review',
    status: 'completed',
    title: 'Transformers review',
    content_markdown: '# Hello',
    error_message: null,
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

beforeEach(() => {
  notify.mockReset();
  vi.mocked(exportReport).mockReset();
  vi.mocked(generateSummary).mockReset();
});

describe('ReportList', () => {
  it('shows an empty state when there are no reports', () => {
    render(<ReportList reports={[]} isLoading={false} />);

    expect(screen.getByText('No reports yet')).toBeInTheDocument();
  });

  it('shows placeholders while loading and no report titles', () => {
    render(<ReportList reports={[makeReport()]} isLoading />);

    expect(screen.queryByText('Transformers review')).not.toBeInTheDocument();
    expect(screen.queryByText('No reports yet')).not.toBeInTheDocument();
  });

  it.each([
    ['pending', 'Queued'],
    ['generating', 'Generating'],
    ['completed', 'Completed'],
    ['failed', 'Failed'],
  ] as const)('labels a %s report as "%s"', (status, label) => {
    render(<ReportList reports={[makeReport({ status })]} isLoading={false} />);

    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it('offers export and summary only for completed reports', () => {
    const { rerender } = render(
      <ReportList reports={[makeReport({ status: 'completed' })]} isLoading={false} />,
    );
    expect(screen.getByRole('button', { name: /export/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /summary/i })).toBeInTheDocument();

    rerender(<ReportList reports={[makeReport({ status: 'generating' })]} isLoading={false} />);
    expect(screen.queryByRole('button', { name: /export/i })).not.toBeInTheDocument();
  });

  it('shows the error message of a failed report', () => {
    render(
      <ReportList
        reports={[makeReport({ status: 'failed', error_message: 'Report generation failed: x' })]}
        isLoading={false}
      />,
    );

    expect(screen.getByText('Report generation failed: x')).toBeInTheDocument();
  });

  it('calls onDelete with the report id', async () => {
    const onDelete = vi.fn();
    render(<ReportList reports={[makeReport()]} isLoading={false} onDelete={onDelete} />);

    await userEvent.click(screen.getByRole('button', { name: 'Delete Transformers review' }));

    expect(onDelete).toHaveBeenCalledWith('r1');
  });

  it('exports in the chosen format and downloads the file', async () => {
    vi.mocked(exportReport).mockResolvedValue(new Blob(['x']));
    const createObjectURL = vi.fn(() => 'blob:fake');
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', { ...URL, createObjectURL, revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    render(<ReportList reports={[makeReport()]} isLoading={false} />);
    await userEvent.click(screen.getByRole('button', { name: /export/i }));
    await userEvent.click(await screen.findByRole('menuitem', { name: 'LaTeX' }));

    await waitFor(() => expect(exportReport).toHaveBeenCalledWith('r1', 'latex', 'token-1'));
    await waitFor(() => expect(notify).toHaveBeenCalledWith('success', 'Exported as LATEX.'));
    expect(click).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:fake');

    vi.unstubAllGlobals();
  });

  it('reports an export failure instead of throwing', async () => {
    vi.mocked(exportReport).mockRejectedValue(new Error('Export failed'));

    render(<ReportList reports={[makeReport()]} isLoading={false} />);
    await userEvent.click(screen.getByRole('button', { name: /export/i }));
    await userEvent.click(await screen.findByRole('menuitem', { name: 'HTML' }));

    await waitFor(() => expect(notify).toHaveBeenCalledWith('error', 'Export failed'));
  });

  it('shows the generated executive summary in a dialog', async () => {
    vi.mocked(generateSummary).mockResolvedValue('Short summary text.');

    render(<ReportList reports={[makeReport()]} isLoading={false} />);
    await userEvent.click(screen.getByRole('button', { name: /summary/i }));

    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('Executive summary');
    expect(dialog).toHaveTextContent('Short summary text.');
    expect(generateSummary).toHaveBeenCalledWith('r1', 'token-1');
  });
});
