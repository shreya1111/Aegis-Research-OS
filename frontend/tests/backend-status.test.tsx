import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { BackendStatus } from '@/components/system/BackendStatus';

describe('BackendStatus', () => {
  it('reports a reachable API with service metadata', () => {
    render(
      <BackendStatus
        health={{
          status: 'ok',
          service: 'Aegis Research OS',
          version: '0.1.0',
          environment: 'development',
        }}
      />,
    );

    const status = screen.getByRole('status');
    expect(status).toHaveTextContent('API reachable');
    expect(status).toHaveTextContent('Aegis Research OS');
    expect(status).toHaveTextContent('0.1.0');
    expect(status).toHaveTextContent('development');
  });

  it('reports an unreachable API with a recovery action', () => {
    render(<BackendStatus health={null} />);

    expect(screen.getByRole('status')).toHaveTextContent('API unreachable');
    expect(screen.getByRole('status')).toHaveTextContent('Start the backend');
  });

  it('announces status changes politely', () => {
    render(<BackendStatus health={null} />);

    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite');
  });
});
