import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { DocumentDropzone } from '@/components/documents/DocumentDropzone';

describe('DocumentDropzone', () => {
  it('renders accepted formats and a browse affordance', () => {
    render(<DocumentDropzone onFilesSelected={vi.fn()} />);
    expect(screen.getByText(/PDF or DOCX/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upload documents/i })).toBeInTheDocument();
  });

  it('emits selected files from the hidden input', async () => {
    const onFilesSelected = vi.fn();
    const { container } = render(<DocumentDropzone onFilesSelected={onFilesSelected} />);
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;

    const file = new File([new Uint8Array([1, 2, 3])], 'paper.pdf', { type: 'application/pdf' });
    await userEvent.upload(input, file);

    expect(onFilesSelected).toHaveBeenCalledTimes(1);
    expect(onFilesSelected.mock.calls[0]![0][0].name).toBe('paper.pdf');
  });

  it('is keyboard focusable when enabled', () => {
    render(<DocumentDropzone onFilesSelected={vi.fn()} />);
    expect(screen.getByRole('button', { name: /upload documents/i })).toHaveAttribute(
      'tabindex',
      '0',
    );
  });

  it('is marked disabled and not focusable when disabled', () => {
    render(<DocumentDropzone onFilesSelected={vi.fn()} disabled />);
    const dropzone = screen.getByRole('button', { name: /upload documents/i });
    expect(dropzone).toHaveAttribute('aria-disabled', 'true');
    expect(dropzone).toHaveAttribute('tabindex', '-1');
  });
});
