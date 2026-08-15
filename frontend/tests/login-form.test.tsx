import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRouter, useSearchParams } from 'next/navigation';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { LoginForm } from '@/components/auth/LoginForm';
import { AuthProvider } from '@/lib/auth/auth-context';
import { config } from '@/lib/config';

vi.mock('next/navigation', () => ({
  useRouter: vi.fn(),
  useSearchParams: vi.fn(),
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

function renderLoginForm(): void {
  vi.mocked(useRouter).mockReturnValue({
    push: vi.fn(),
    replace: vi.fn(),
  } as unknown as ReturnType<typeof useRouter>);
  vi.mocked(useSearchParams).mockReturnValue(
    new URLSearchParams() as unknown as ReturnType<typeof useSearchParams>,
  );

  render(<LoginForm />, { wrapper: AuthProvider });
}

describe('LoginForm', () => {
  it('renders email and password fields', async () => {
    vi.stubGlobal('fetch', vi.fn());
    renderLoginForm();

    // Let AuthProvider's initial (no-op, since no tokens are stored) session
    // check settle before asserting, so its state update is inside `act`.
    await screen.findByLabelText('Email');
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
  });

  it('submits credentials and navigates to the dashboard on success', async () => {
    const push = vi.fn();
    vi.mocked(useRouter).mockReturnValue({ push, replace: vi.fn() } as unknown as ReturnType<
      typeof useRouter
    >);
    vi.mocked(useSearchParams).mockReturnValue(
      new URLSearchParams() as unknown as ReturnType<typeof useSearchParams>,
    );

    const fetchMock = vi.fn((url: string) => {
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

    render(<LoginForm />, { wrapper: AuthProvider });

    await userEvent.type(screen.getByLabelText('Email'), 'alice@example.com');
    await userEvent.type(screen.getByLabelText('Password'), 'correct-horse');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => expect(push).toHaveBeenCalledWith('/dashboard'));
  });

  it('shows the server error message on failed login', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          jsonResponse(
            {
              success: false,
              data: null,
              error: { code: 'UNAUTHENTICATED', message: 'Invalid email or password.' },
            },
            { status: 401 },
          ),
        ),
      ),
    );
    renderLoginForm();

    await userEvent.type(screen.getByLabelText('Email'), 'alice@example.com');
    await userEvent.type(screen.getByLabelText('Password'), 'wrong-password');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password.');
  });

  it('disables the submit button while the request is in flight', async () => {
    let resolveLogin: (() => void) | undefined;
    vi.stubGlobal(
      'fetch',
      vi.fn(
        () =>
          new Promise<Response>((resolve) => {
            resolveLogin = () =>
              resolve(
                jsonResponse(
                  {
                    success: false,
                    data: null,
                    error: { code: 'UNAUTHENTICATED', message: 'nope' },
                  },
                  { status: 401 },
                ),
              );
          }),
      ),
    );
    renderLoginForm();

    await userEvent.type(screen.getByLabelText('Email'), 'alice@example.com');
    await userEvent.type(screen.getByLabelText('Password'), 'wrong-password');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled();

    resolveLogin?.();
    await screen.findByRole('alert');
  });
});
