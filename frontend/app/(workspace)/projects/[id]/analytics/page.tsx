'use client';

import { Trash2, Upload } from 'lucide-react';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

import {
  analyzeDataset,
  deleteDataset,
  listAnalyses,
  listDatasets,
  uploadDataset,
} from '@/lib/api/analytics';
import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import { useToast } from '@/lib/toast/toast-context';
import { cn } from '@/lib/utils/cn';
import type { AnalyticsAnalysis, AnalyticsDataset } from '@/types/api';

import { EmptyState } from '@/components/feedback/EmptyState';
import { Skeleton } from '@/components/feedback/Skeleton';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';

type LoadState = 'loading' | 'ready' | 'error';

//: Poll while any dataset is still being profiled in the background.
const POLL_INTERVAL_MS = 3000;

function hasInFlightDatasets(datasets: AnalyticsDataset[]): boolean {
  return datasets.some((dataset) => dataset.status === 'pending');
}

function datasetSummary(dataset: AnalyticsDataset): string {
  if (dataset.status === 'profiled' && dataset.row_count !== null) {
    return `${dataset.row_count.toLocaleString()} rows · ${dataset.column_count ?? 0} columns`;
  }
  return dataset.status === 'failed' ? 'Profiling failed' : 'Profiling…';
}

export default function ProjectAnalyticsPage(): React.JSX.Element {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const { getValidAccessToken } = useAuth();
  const { notify } = useToast();

  const [datasets, setDatasets] = useState<AnalyticsDataset[]>([]);
  const [loadState, setLoadState] = useState<LoadState>('loading');
  const [isUploading, setIsUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [selectedDataset, setSelectedDataset] = useState<AnalyticsDataset | null>(null);
  const [analyses, setAnalyses] = useState<AnalyticsAnalysis[]>([]);
  const [question, setQuestion] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<AnalyticsDataset | null>(null);
  const pollRef = useRef<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDatasets = useCallback(
    async (mode: 'initial' | 'refresh') => {
      if (mode === 'initial') {
        setLoadState('loading');
      }
      try {
        const token = await getValidAccessToken();
        if (!token) {
          setLoadState('error');
          return;
        }
        setDatasets(await listDatasets(projectId, token));
        setLoadState('ready');
      } catch {
        // A failed refresh leaves the last good list in place; the next poll retries.
        if (mode === 'initial') {
          setLoadState('error');
        }
      }
    },
    [getValidAccessToken, projectId],
  );

  const fetchAnalyses = useCallback(
    async (datasetId: string) => {
      try {
        const token = await getValidAccessToken();
        if (!token) return;
        setAnalyses(await listAnalyses(datasetId, token));
      } catch {
        // Analyses are re-fetched on every selection; a transient failure is not
        // worth interrupting the user for.
      }
    },
    [getValidAccessToken],
  );

  useEffect(() => {
    void fetchDatasets('initial');
  }, [fetchDatasets]);

  useEffect(() => {
    if (hasInFlightDatasets(datasets)) {
      pollRef.current = window.setTimeout(() => {
        void fetchDatasets('refresh');
      }, POLL_INTERVAL_MS);
    }
    return () => {
      if (pollRef.current !== null) {
        window.clearTimeout(pollRef.current);
      }
    };
  }, [datasets, fetchDatasets]);

  useEffect(() => {
    if (selectedDataset) {
      void fetchAnalyses(selectedDataset.id);
    }
  }, [selectedDataset, fetchAnalyses]);

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>): Promise<void> {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.csv')) {
      notify('error', 'Analytics accepts CSV files only.');
      return;
    }

    setIsUploading(true);
    try {
      const token = await getValidAccessToken();
      if (!token) {
        notify('error', 'Your session has expired. Please sign in again.');
        return;
      }
      await uploadDataset(projectId, file, token);
      notify('success', `"${file.name}" uploaded. Profiling starts now.`);
      await fetchDatasets('refresh');
    } catch (caught) {
      notify(
        'error',
        caught instanceof ApiError ? caught.message : `Could not upload "${file.name}".`,
      );
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  }

  async function handleDelete(datasetId: string): Promise<void> {
    setDeletingId(datasetId);
    try {
      const token = await getValidAccessToken();
      if (!token) {
        notify('error', 'Your session has expired. Please sign in again.');
        return;
      }
      await deleteDataset(datasetId, token);
      notify('success', 'Dataset deleted.');
      if (selectedDataset?.id === datasetId) {
        setSelectedDataset(null);
        setAnalyses([]);
      }
      await fetchDatasets('refresh');
    } catch (caught) {
      notify(
        'error',
        caught instanceof ApiError ? caught.message : 'Could not delete the dataset.',
      );
    } finally {
      setDeletingId(null);
    }
  }

  async function handleAnalyze(): Promise<void> {
    if (!selectedDataset || !question.trim()) return;

    setIsAnalyzing(true);
    try {
      const token = await getValidAccessToken();
      if (!token) {
        notify('error', 'Your session has expired. Please sign in again.');
        return;
      }
      await analyzeDataset(selectedDataset.id, question.trim(), token);
      notify('success', 'Analysis started.');
      setQuestion('');
      window.setTimeout(() => void fetchAnalyses(selectedDataset.id), 2000);
    } catch (caught) {
      notify(
        'error',
        caught instanceof ApiError ? caught.message : 'Could not start the analysis.',
      );
    } finally {
      setIsAnalyzing(false);
    }
  }

  if (loadState === 'loading') {
    return (
      <div className="flex flex-col gap-4 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (loadState === 'error') {
    return (
      <div className="p-6">
        <Alert variant="destructive" className="flex-col items-start gap-3">
          <span>Could not load analytics for this project.</span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void fetchDatasets('initial')}
          >
            Retry
          </Button>
        </Alert>
      </div>
    );
  }

  const columns = selectedDataset?.profile_data?.columns as
    | Record<string, { dtype?: string }>
    | undefined;

  return (
    <div className="flex h-full min-h-0">
      <aside className="flex w-72 shrink-0 flex-col gap-4 border-r p-4">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-h3 font-semibold">Datasets</h2>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            className="sr-only"
            onChange={(event) => void handleUpload(event)}
          />
          <Button
            type="button"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
          >
            <Upload className="size-4" aria-hidden />
            {isUploading ? 'Uploading…' : 'Upload CSV'}
          </Button>
        </div>

        {datasets.length === 0 ? (
          <p className="rounded-surface border border-dashed px-4 py-6 text-center text-body-sm text-muted-foreground">
            No datasets yet. Upload a CSV to profile it.
          </p>
        ) : (
          <ul className="flex flex-col gap-2 overflow-y-auto">
            {datasets.map((dataset) => {
              const selected = selectedDataset?.id === dataset.id;
              return (
                <li
                  key={dataset.id}
                  className={cn(
                    'flex items-start gap-1 rounded-surface border p-2 transition-colors',
                    selected ? 'border-primary/40 bg-accent' : 'border-border hover:bg-muted/60',
                  )}
                >
                  <button
                    type="button"
                    onClick={() => setSelectedDataset(dataset)}
                    aria-current={selected ? 'true' : undefined}
                    className="min-w-0 flex-1 rounded-control px-2 py-1 text-left"
                  >
                    <span className="block truncate text-body-sm font-medium">
                      {dataset.filename}
                    </span>
                    <span className="block text-caption text-muted-foreground">
                      {datasetSummary(dataset)}
                    </span>
                  </button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="shrink-0 text-muted-foreground hover:text-destructive"
                    aria-label={`Delete ${dataset.filename}`}
                    disabled={deletingId === dataset.id}
                    onClick={() => setPendingDelete(dataset)}
                  >
                    <Trash2 className="size-4" aria-hidden />
                  </Button>
                </li>
              );
            })}
          </ul>
        )}
      </aside>

      <div className="flex min-w-0 flex-1 flex-col gap-6 overflow-y-auto p-6">
        <div>
          <h1 className="text-h1 font-semibold">Analytics</h1>
          <p className="text-body-sm text-muted-foreground">
            Profile a CSV, then ask questions of it. Generated code runs in a sandbox and every
            answer is explained.
          </p>
        </div>

        {!selectedDataset ? (
          <EmptyState
            title="Select a dataset"
            description="Choose a dataset on the left to see its profile and run analyses."
          />
        ) : (
          <>
            <section className="flex flex-col gap-3">
              <h2 className="text-h3 font-semibold">Dataset profile</h2>

              {selectedDataset.status === 'pending' && (
                <Alert variant="info">Profiling this dataset…</Alert>
              )}

              {selectedDataset.status === 'failed' && (
                <Alert variant="destructive">
                  Profiling failed: {String(selectedDataset.profile_data?.error ?? 'Unknown error')}
                </Alert>
              )}

              {selectedDataset.status === 'profiled' && selectedDataset.profile_data && (
                <div className="flex flex-col gap-4 rounded-surface border bg-muted/40 p-4">
                  <dl className="grid grid-cols-2 gap-4 text-body-sm">
                    <div className="flex flex-col gap-0.5">
                      <dt className="text-caption text-muted-foreground">Rows</dt>
                      <dd className="font-medium">
                        {selectedDataset.row_count?.toLocaleString() ?? '—'}
                      </dd>
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <dt className="text-caption text-muted-foreground">Columns</dt>
                      <dd className="font-medium">{selectedDataset.column_count ?? '—'}</dd>
                    </div>
                  </dl>

                  {columns && (
                    <div className="flex flex-col gap-1">
                      <p className="text-caption font-medium text-muted-foreground">Columns</p>
                      <div className="overflow-y-auto rounded-control border bg-card">
                        {Object.entries(columns).map(([name, info]) => (
                          <div
                            key={name}
                            className="flex items-center justify-between gap-3 border-b px-2 py-1 text-caption last:border-0"
                          >
                            <span className="truncate font-mono">{name}</span>
                            <span className="shrink-0 text-muted-foreground">{info.dtype}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </section>

            {selectedDataset.status === 'profiled' && (
              <section className="flex flex-col gap-2">
                <h2 className="text-h3 font-semibold">Ask a question</h2>
                <div className="flex gap-2">
                  <Input
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') void handleAnalyze();
                    }}
                    placeholder="e.g. What is the average value per category?"
                    aria-label="Question about this dataset"
                    disabled={isAnalyzing}
                  />
                  <Button
                    type="button"
                    onClick={() => void handleAnalyze()}
                    disabled={!question.trim() || isAnalyzing}
                  >
                    {isAnalyzing ? 'Analyzing…' : 'Analyze'}
                  </Button>
                </div>
              </section>
            )}

            <section className="flex flex-col gap-3">
              <h2 className="text-h3 font-semibold">Analyses</h2>

              {analyses.length === 0 ? (
                <p className="rounded-surface border border-dashed px-4 py-6 text-center text-body-sm text-muted-foreground">
                  No analyses yet. Ask a question above to start one.
                </p>
              ) : (
                <div className="flex flex-col gap-4">
                  {analyses.map((analysis) => (
                    <article
                      key={analysis.id}
                      className="flex flex-col gap-3 rounded-surface border p-4"
                    >
                      <div>
                        <p className="text-body-sm font-medium">{analysis.question}</p>
                        <p className="text-caption text-muted-foreground">
                          {new Date(analysis.created_at).toLocaleString()}
                        </p>
                      </div>

                      {analysis.status === 'pending' && (
                        <Alert variant="info">Running this analysis…</Alert>
                      )}

                      {analysis.status === 'failed' && (
                        <Alert variant="destructive">
                          {analysis.error_message ?? 'Analysis failed.'}
                        </Alert>
                      )}

                      {analysis.status === 'completed' && (
                        <>
                          {analysis.explanation && (
                            <div className="flex flex-col gap-1 rounded-control border border-info/30 bg-info/10 p-3 text-info">
                              <p className="text-caption font-medium">Explanation</p>
                              <p className="text-body-sm">{analysis.explanation}</p>
                            </div>
                          )}

                          {analysis.analysis_code && (
                            <div className="flex flex-col gap-1">
                              <p className="text-caption font-medium text-muted-foreground">
                                Generated code
                              </p>
                              <pre className="overflow-x-auto rounded-control bg-muted p-3 font-mono text-caption">
                                {analysis.analysis_code}
                              </pre>
                            </div>
                          )}

                          {analysis.result_data && (
                            <div className="flex flex-col gap-1">
                              <p className="text-caption font-medium text-muted-foreground">
                                Results
                              </p>
                              <pre className="overflow-x-auto rounded-control bg-muted p-3 font-mono text-caption">
                                {JSON.stringify(analysis.result_data, null, 2)}
                              </pre>
                            </div>
                          )}

                          {analysis.chart_data && (
                            <div className="flex flex-col gap-1">
                              <p className="text-caption font-medium text-muted-foreground">
                                Chart
                              </p>
                              <div className="rounded-control border bg-card p-4">
                                {analysis.chart_data.image_base64 ? (
                                  // eslint-disable-next-line @next/next/no-img-element -- data URL, not a remote asset
                                  <img
                                    src={`data:image/png;base64,${analysis.chart_data.image_base64}`}
                                    alt="Chart produced by this analysis"
                                    className="h-auto max-w-full"
                                  />
                                ) : (
                                  <pre className="overflow-x-auto font-mono text-caption">
                                    {JSON.stringify(analysis.chart_data, null, 2)}
                                  </pre>
                                )}
                              </div>
                            </div>
                          )}
                        </>
                      )}
                    </article>
                  ))}
                </div>
              )}
            </section>
          </>
        )}
      </div>

      <Dialog
        open={pendingDelete !== null}
        onOpenChange={(open) => {
          if (!open) setPendingDelete(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this dataset?</DialogTitle>
            <DialogDescription>
              {pendingDelete?.filename} and its analyses will be removed. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </DialogClose>
            <Button
              type="button"
              variant="destructive"
              onClick={() => {
                const target = pendingDelete;
                setPendingDelete(null);
                if (target) void handleDelete(target.id);
              }}
            >
              Delete dataset
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
