'use client';

import { useParams } from 'next/navigation';
import { useCallback, useState } from 'react';

import { ApiError } from '@/lib/api/client';
import { runQuery } from '@/lib/api/query';
import { useAuth } from '@/lib/auth/auth-context';
import type { Citation } from '@/types/api';

import { StreamingMessage } from '@/components/chat/StreamingMessage';
import { TracePanel } from '@/components/trace/TracePanel';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface ChatTurn {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations: Citation[];
  citationWarning: boolean;
  pipeline: 'rag' | 'agent';
}

/**
 * Chat UI wired to the Phase 4 hybrid RAG / Phase 5 agent-graph query
 * endpoint (design §5.7, §6.5). ``POST /projects/{id}/query`` transparently
 * routes between the two pipelines server-side; this component only cares
 * about the shared response shape and which ``run_id`` to show in the
 * Reasoning Trace panel alongside it.
 */
export function ChatPanel(): React.JSX.Element {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const { getValidAccessToken } = useAuth();

  const [draft, setDraft] = useState('');
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const question = draft.trim();
      if (!question || isSubmitting) {
        return;
      }

      setDraft('');
      setError(null);
      setIsSubmitting(true);
      setTurns((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: 'user',
          content: question,
          citations: [],
          citationWarning: false,
          pipeline: 'rag',
        },
      ]);

      try {
        const token = await getValidAccessToken();
        if (!token) {
          setError('Your session has expired. Please sign in again.');
          return;
        }

        const response = await runQuery(token, projectId, { question });
        setActiveRunId(response.run_id);
        setTurns((current) => [
          ...current,
          {
            id: response.message_id,
            role: 'assistant',
            content: response.answer,
            citations: response.citations,
            citationWarning: response.citation_warning,
            pipeline: response.pipeline,
          },
        ]);
      } catch (caught) {
        setError(
          caught instanceof ApiError
            ? caught.message
            : 'Something went wrong answering that question.',
        );
      } finally {
        setIsSubmitting(false);
      }
    },
    [draft, getValidAccessToken, isSubmitting, projectId],
  );

  return (
    <div className="flex h-full">
      <div className="flex flex-1 flex-col">
        <div className="flex-1 overflow-y-auto p-4 lg:p-6">
          <div className="mx-auto flex max-w-prose flex-col gap-4">
            {turns.length === 0 ? (
              <div className="flex flex-col items-center gap-3 rounded-surface border border-dashed px-6 py-16 text-center">
                <h3 className="text-h3 font-semibold">Ask a research question</h3>
                <p className="max-w-md text-body-sm text-muted-foreground">
                  Simple factual questions run a fast retrieval-and-answer pass. A multi-part
                  request — try one of these — dispatches the full multi-agent pipeline instead:
                </p>
                <ul className="flex flex-col gap-1 text-body-sm text-muted-foreground">
                  <li>&ldquo;Summarise the methodology across my uploaded papers.&rdquo;</li>
                  <li>&ldquo;Compare approach A and approach B and identify open gaps.&rdquo;</li>
                  <li>&ldquo;What does the literature say about X, with citations?&rdquo;</li>
                </ul>
              </div>
            ) : (
              turns.map((turn) => (
                <div
                  key={turn.id}
                  className={
                    turn.role === 'user'
                      ? 'ml-auto max-w-[80%] rounded-surface bg-primary px-4 py-2 text-body-sm text-primary-foreground'
                      : 'mr-auto max-w-[80%] rounded-surface border bg-card px-4 py-3 text-body-sm'
                  }
                >
                  {turn.role === 'assistant' ? (
                    <>
                      <StreamingMessage content={turn.content} citations={turn.citations} />
                      {turn.citationWarning && (
                        <p className="mt-2 text-caption text-warning">
                          Some citations in this answer could not be fully verified.
                        </p>
                      )}
                      {turn.pipeline === 'agent' && (
                        <p className="mt-2 text-caption text-muted-foreground">
                          Answered by the multi-agent research pipeline — see the trace panel for
                          each step.
                        </p>
                      )}
                    </>
                  ) : (
                    turn.content
                  )}
                </div>
              ))
            )}

            {isSubmitting && (
              <div className="mr-auto max-w-[80%] rounded-surface border bg-card px-4 py-3 text-body-sm text-muted-foreground">
                Thinking…
              </div>
            )}

            {error && <Alert variant="destructive">{error}</Alert>}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="border-t p-4 lg:p-6">
          <div className="mx-auto flex max-w-prose items-center gap-2">
            <Input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Ask a question about your research…"
              aria-label="Research question"
              disabled={isSubmitting}
            />
            <Button type="submit" disabled={draft.trim().length === 0 || isSubmitting}>
              Send
            </Button>
          </div>
        </form>
      </div>

      <TracePanel projectId={projectId} runId={activeRunId} />
    </div>
  );
}
