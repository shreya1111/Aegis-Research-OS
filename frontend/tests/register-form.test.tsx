import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRouter } from 'next/navigation';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { RegisterForm } from '@/components/auth/RegisterForm';
import { AuthProvider } from '@/lib/auth/auth-context';
import { config } from '@/lib/config';

vi.mock('next/navigation', () => ({
  useRouter: vi.fn(),
}));

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
  });
}

const apiBase = `${config.apiBaseUrl}${config.apiVersionPrefix}`;

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
  window.localStorage.clear();
});

describe('RegisterForm', () => {
  it('renders name, email, and password fields', async () => {
    vi.mocked(useRouter).mockReturnValue({ push: vi.fn() } as unknown as ReturnType<
      typeof useRouter
    >);
    vi.stubGlobal('fetch', vi.fn());

    render(<RegisterForm />, { wrapper: AuthProvider });

    // Let AuthProvider's initial (no-op, since no tokens are stored) session
    // check settle before asserting, so its state update is inside `act`.
    await screen.findByLabelText('Name');
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
  });

  it('registers, logs in, and navigates to the dashboard', async () => {
    const push = vi.fn();
    vi.mocked(useRouter).mockReturnValue({ push } as unknown as ReturnType<typeof useRouter>);

    const fetchMock = vi.fn((url: string) => {
      if (url === `${apiBase}/auth/register`) {
        return Promise.resolve(
          jsonResponse({
            success: true,
            data: { id: 'u1', email: 'alice@example.com', name: 'Alice', created_at: 'x' },
            error: null,
          }),
        );
      }
      if (url === `${apiBase}/auth/login`) {
        return Promise.resolve(
          jsonResponse({
            success: true,
            data: { access_token: 'access-1', refresh_token: 'refresh-1', token_type: 'bearer' },
            error: null,
          }),
        );
      }
      return Promise.resolve(
        jsonResponse({
          success: true,
          data: { id: 'u1', email: 'alice@example.com', name: 'Alice', created_at: 'x' },
          error: null,
        }),
      );
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<RegisterForm />, { wrapper: AuthProvider });

    await userEvent.type(screen.getByLabelText('Name'), 'Alice');
    await userEvent.type(screen.getByLabelText('Email'), 'alice@example.com');
    await userEvent.type(screen.getByLabelText('Password'), 'correct-horse-battery');
    await userEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => expect(push).toHaveBeenCalledWith('/dashboard'));
  });

  it('shows a conflict error for a duplicate email', async () => {
    vi.mocked(useRouter).mockReturnValue({ push: vi.fn() } as unknown as ReturnType<
      typeof useRouter
    >);
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          jsonResponse(
            {
              success: false,
              data: null,
              error: { code: 'CONFLICT', message: 'An account with this email already exists.' },
            },
            { status: 409 },
          ),
        ),
      ),
    );

    render(<RegisterForm />, { wrapper: AuthProvider });

    await userEvent.type(screen.getByLabelText('Name'), 'Alice');
    await userEvent.type(screen.getByLabelText('Email'), 'alice@example.com');
    await userEvent.type(screen.getByLabelText('Password'), 'correct-horse-battery');
    await userEvent.click(screen.getByRole('button', { name: /create account/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'An account with this email already exists.',
    );
  });
});
