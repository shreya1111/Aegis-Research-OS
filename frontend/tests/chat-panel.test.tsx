import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useParams } from 'next/navigation';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ChatPanel } from '@/components/chat/ChatPanel';
import { AuthProvider } from '@/lib/auth/auth-context';
import { config } from '@/lib/config';

vi.mock('next/navigation', () => ({
  useParams: vi.fn(),
}));

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
  });
}

const apiBase = `${config.apiBaseUrl}${config.apiVersionPrefix}`;

const currentUser = { id: 'u1', email: 'alice@example.com', name: 'Alice', created_at: 'x' };

function seedStoredTokens(): void {
  window.localStorage.setItem('aegis.auth.access_token', 'access-1');
  window.localStorage.setItem('aegis.auth.refresh_token', 'refresh-1');
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
  window.localStorage.clear();
});

function renderChatPanel(): void {
  vi.mocked(useParams).mockReturnValue({ id: 'p1' });
  render(<ChatPanel />, { wrapper: AuthProvider });
}

describe('ChatPanel', () => {
  it('shows the empty-state prompt before any question is asked', async () => {
    vi.stubGlobal('fetch', vi.fn());
    renderChatPanel();

    expect(await screen.findByText(/ask a research question/i)).toBeInTheDocument();
  });

  it('sends a question and renders the cited answer', async () => {
    seedStoredTokens();
    const queryResponse = {
      run_id: 'r1',
      message_id: 'm1',
      answer: 'The finding is X, per the source [Doc 1, p.1].',
      citations: [{ marker: 'Doc 1, p.1', chunk_id: 'c1', document_id: 'd1', page: 1 }],
      sources: [],
      citation_warning: false,
      pipeline: 'rag',
    };

    const fetchMock = vi.fn((url: string) => {
      if (url === `${apiBase}/auth/me`) {
        return Promise.resolve(jsonResponse({ success: true, data: currentUser, error: null }));
      }
      if (url === `${apiBase}/projects/p1/query`) {
        return Promise.resolve(jsonResponse({ success: true, data: queryResponse, error: null }));
      }
      return Promise.resolve(
        jsonResponse({ success: true, data: { run_id: 'r1', steps: [] }, error: null }),
      );
    });
    vi.stubGlobal('fetch', fetchMock);

    renderChatPanel();

    const input = await screen.findByLabelText('Research question');
    await userEvent.type(input, 'What is the finding?');
    await userEvent.click(screen.getByRole('button', { name: /send/i }));

    expect(await screen.findByText(/the finding is x/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Doc 1, p.1' })).toBeInTheDocument();
  });

  it('shows a citation-warning notice when the backend flags one', async () => {
    seedStoredTokens();
    const queryResponse = {
      run_id: 'r1',
      message_id: 'm1',
      answer: 'An answer with an unresolved citation.',
      citations: [],
      sources: [],
      citation_warning: true,
      pipeline: 'rag',
    };

    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url === `${apiBase}/auth/me`) {
          return Promise.resolve(jsonResponse({ success: true, data: currentUser, error: null }));
        }
        if (url === `${apiBase}/projects/p1/query`) {
          return Promise.resolve(jsonResponse({ success: true, data: queryResponse, error: null }));
        }
        return Promise.resolve(
          jsonResponse({ success: true, data: { run_id: 'r1', steps: [] }, error: null }),
        );
      }),
    );

    renderChatPanel();

    const input = await screen.findByLabelText('Research question');
    await userEvent.type(input, 'A question.');
    await userEvent.click(screen.getByRole('button', { name: /send/i }));

    expect(await screen.findByText(/could not be fully verified/i)).toBeInTheDocument();
  });

  it('labels an agent-pipeline answer distinctly from a RAG answer', async () => {
    seedStoredTokens();
    const queryResponse = {
      run_id: 'r1',
      message_id: 'm1',
      answer: 'A synthesised multi-agent answer.',
      citations: [],
      sources: [],
      citation_warning: false,
      pipeline: 'agent',
    };

    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url === `${apiBase}/auth/me`) {
          return Promise.resolve(jsonResponse({ success: true, data: currentUser, error: null }));
        }
        if (url === `${apiBase}/projects/p1/query`) {
          return Promise.resolve(jsonResponse({ success: true, data: queryResponse, error: null }));
        }
        return Promise.resolve(
          jsonResponse({ success: true, data: { run_id: 'r1', steps: [] }, error: null }),
        );
      }),
    );

    renderChatPanel();

    const input = await screen.findByLabelText('Research question');
    await userEvent.type(input, 'Compare A and B and identify open gaps.');
    await userEvent.click(screen.getByRole('button', { name: /send/i }));

    expect(await screen.findByText(/multi-agent research pipeline/i)).toBeInTheDocument();
  });

  it('shows an error message when the query fails', async () => {
    seedStoredTokens();
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url === `${apiBase}/auth/me`) {
          return Promise.resolve(jsonResponse({ success: true, data: currentUser, error: null }));
        }
        return Promise.resolve(
          jsonResponse(
            {
              success: false,
              data: null,
              error: { code: 'RATE_LIMITED', message: 'Too many questions.' },
            },
            { status: 429 },
          ),
        );
      }),
    );

    renderChatPanel();

    const input = await screen.findByLabelText('Research question');
    await userEvent.type(input, 'A question.');
    await userEvent.click(screen.getByRole('button', { name: /send/i }));

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Too many questions.'));
  });

  it('disables the send button while a question is empty', async () => {
    vi.stubGlobal('fetch', vi.fn());
    renderChatPanel();

    await screen.findByLabelText('Research question');
    expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
  });
});
