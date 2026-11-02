'use client';

import { useParams } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

import { ApiError } from '@/lib/api/client';
import {
  analyzeDataset,
  deleteDataset,
  listAnalyses,
  listDatasets,
  uploadDataset,
} from '@/lib/api/analytics';
import { useAuth } from '@/lib/auth/auth-context';
import { useToast } from '@/lib/toast/toast-context';
import type { AnalyticsAnalysis, AnalyticsDataset } from '@/types/api';

import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/feedback/EmptyState';
import { Skeleton } from '@/components/feedback/Skeleton';

type LoadState = 'loading' | 'ready' | 'error';

// Poll interval while datasets are being profiled
const POLL_INTERVAL_MS = 3000;

function hasInFlightDatasets(datasets: AnalyticsDataset[]): boolean {
  return datasets.some((ds) => ds.status === 'pending');
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
        const data = await listDatasets(projectId, token);
        setDatasets(data);
        setLoadState('ready');
      } catch (error) {
        console.error('Failed to fetch datasets:', error);
        if (mode === 'initial') {
          setLoadState('error');
        }
      }
    },
    [projectId, getValidAccessToken],
  );

  const fetchAnalyses = useCallback(
    async (datasetId: string) => {
      try {
        const token = await getValidAccessToken();
        if (!token) return;
        const data = await listAnalyses(datasetId, token);
        setAnalyses(data);
      } catch (error) {
        console.error('Failed to fetch analyses:', error);
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
      if (pollRef.current) {
        window.clearTimeout(pollRef.current);
      }
    };
  }, [datasets, fetchDatasets]);

  useEffect(() => {
    if (selectedDataset) {
      void fetchAnalyses(selectedDataset.id);
    }
  }, [selectedDataset, fetchAnalyses]);

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      notify('error', 'Please upload a CSV file');
      return;
    }

    setIsUploading(true);
    try {
      const token = await getValidAccessToken();
      if (!token) {
        throw new Error('Not authenticated');
      }
      await uploadDataset(projectId, file, token);
      notify('success', 'Dataset uploaded successfully');
      await fetchDatasets('refresh');
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Failed to upload dataset';
      notify('error', message);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDelete = async (datasetId: string) => {
    if (!confirm('Delete this dataset and all its analyses?')) return;

    setDeletingId(datasetId);
    try {
      const token = await getValidAccessToken();
      if (!token) {
        throw new Error('Not authenticated');
      }
      await deleteDataset(datasetId, token);
      notify('success', 'Dataset deleted');
      if (selectedDataset?.id === datasetId) {
        setSelectedDataset(null);
        setAnalyses([]);
      }
      await fetchDatasets('refresh');
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Failed to delete dataset';
      notify('error', message);
    } finally {
      setDeletingId(null);
    }
  };

  const handleAnalyze = async () => {
    if (!selectedDataset || !question.trim()) return;

    setIsAnalyzing(true);
    try {
      const token = await getValidAccessToken();
      if (!token) {
        throw new Error('Not authenticated');
      }
      await analyzeDataset(selectedDataset.id, question.trim(), token);
      notify('success', 'Analysis started');
      setQuestion('');
      // Poll for results
      setTimeout(() => fetchAnalyses(selectedDataset.id), 2000);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Analysis failed';
      notify('error', message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  if (loadState === 'loading') {
    return (
      <div className="space-y-4 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (loadState === 'error') {
    return (
      <div className="p-6">
        <Alert variant="destructive">Failed to load analytics. Please refresh the page.</Alert>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Left panel: Dataset list */}
      <div className="w-80 space-y-4 overflow-y-auto border-r border-neutral-200 p-4 dark:border-neutral-800">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Datasets</h2>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={handleUpload}
          />
          <Button size="sm" onClick={() => fileInputRef.current?.click()} disabled={isUploading}>
            {isUploading ? 'Uploading...' : 'Upload CSV'}
          </Button>
        </div>

        {datasets.length === 0 ? (
          <EmptyState title="No datasets yet" description="Upload a CSV file to get started" />
        ) : (
          <div className="space-y-2">
            {datasets.map((dataset) => (
              <div
                key={dataset.id}
                className={`cursor-pointer rounded-lg border p-3 transition-colors ${
                  selectedDataset?.id === dataset.id
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-950'
                    : 'border-neutral-200 hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900'
                }`}
                onClick={() => setSelectedDataset(dataset)}
              >
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{dataset.filename}</p>
                    <p className="text-xs text-neutral-600 dark:text-neutral-400">
                      {dataset.status === 'profiled' && dataset.row_count
                        ? `${dataset.row_count} rows × ${dataset.column_count} cols`
                        : dataset.status}
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(dataset.id);
                    }}
                    disabled={deletingId === dataset.id}
                    className="ml-2 text-xs text-neutral-400 hover:text-red-600"
                  >
                    {deletingId === dataset.id ? '...' : '×'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Right panel: Dataset details and analysis */}
      <div className="flex-1 overflow-y-auto p-6">
        {!selectedDataset ? (
          <EmptyState
            title="Select a dataset"
            description="Choose a dataset on the left to view its profile and run analyses."
          />
        ) : (
          <div className="space-y-6">
            {/* Dataset profile */}
            <div>
              <h3 className="mb-2 text-lg font-semibold">Dataset Profile</h3>
              {selectedDataset.status === 'pending' && (
                <Alert variant="info">Profiling dataset...</Alert>
              )}
              {selectedDataset.status === 'failed' && (
                <Alert variant="destructive">
                  Profiling failed: {String(selectedDataset.profile_data?.error ?? 'Unknown error')}
                </Alert>
              )}
              {selectedDataset.status === 'profiled' && selectedDataset.profile_data && (
                <div className="space-y-2 rounded-lg bg-neutral-50 p-4 dark:bg-neutral-900">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-neutral-600 dark:text-neutral-400">Rows:</span>{' '}
                      <span className="font-medium">{selectedDataset.row_count}</span>
                    </div>
                    <div>
                      <span className="text-neutral-600 dark:text-neutral-400">Columns:</span>{' '}
                      <span className="font-medium">{selectedDataset.column_count}</span>
                    </div>
                  </div>
                  {selectedDataset.profile_data.columns && (
                    <div className="mt-4">
                      <p className="mb-2 text-sm font-medium">Columns:</p>
                      <div className="max-h-48 space-y-1 overflow-y-auto">
                        {Object.entries(
                          selectedDataset.profile_data.columns as Record<
                            string,
                            { dtype?: string }
                          >,
                        ).map(([name, info]) => (
                          <div
                            key={name}
                            className="flex items-center justify-between rounded bg-white px-2 py-1 text-xs dark:bg-neutral-800"
                          >
                            <span className="font-mono">{name}</span>
                            <span className="text-neutral-600 dark:text-neutral-400">
                              {info.dtype}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Analysis question */}
            {selectedDataset.status === 'profiled' && (
              <div>
                <h3 className="mb-2 text-lg font-semibold">Ask a Question</h3>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
                    placeholder="E.g., What is the average age by gender?"
                    className="flex-1 rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
                    disabled={isAnalyzing}
                  />
                  <Button onClick={handleAnalyze} disabled={!question.trim() || isAnalyzing}>
                    {isAnalyzing ? 'Analyzing...' : 'Analyze'}
                  </Button>
                </div>
              </div>
            )}

            {/* Analyses list */}
            <div>
              <h3 className="mb-2 text-lg font-semibold">Analyses</h3>
              {analyses.length === 0 ? (
                <EmptyState title="No analyses yet" description="Ask a question to get started" />
              ) : (
                <div className="space-y-4">
                  {analyses.map((analysis) => (
                    <div
                      key={analysis.id}
                      className="space-y-3 rounded-lg border border-neutral-200 p-4 dark:border-neutral-800"
                    >
                      <div>
                        <p className="text-sm font-medium">{analysis.question}</p>
                        <p className="mt-1 text-xs text-neutral-600 dark:text-neutral-400">
                          {new Date(analysis.created_at).toLocaleString()}
                        </p>
                      </div>

                      {analysis.status === 'pending' && (
                        <Alert variant="info">Running analysis...</Alert>
                      )}

                      {analysis.status === 'failed' && (
                        <Alert variant="destructive">
                          {analysis.error_message || 'Analysis failed'}
                        </Alert>
                      )}

                      {analysis.status === 'completed' && (
                        <>
                          {analysis.explanation && (
                            <div className="rounded bg-blue-50 p-3 text-sm dark:bg-blue-950">
                              <p className="mb-1 font-medium text-blue-900 dark:text-blue-100">
                                Explanation
                              </p>
                              <p className="text-blue-800 dark:text-blue-200">
                                {analysis.explanation}
                              </p>
                            </div>
                          )}

                          {analysis.analysis_code && (
                            <div>
                              <p className="mb-1 text-xs font-medium text-neutral-600 dark:text-neutral-400">
                                Generated Code
                              </p>
                              <pre className="overflow-x-auto rounded bg-neutral-900 p-3 text-xs text-neutral-100">
                                {analysis.analysis_code}
                              </pre>
                            </div>
                          )}

                          {analysis.result_data && (
                            <div>
                              <p className="mb-1 text-xs font-medium text-neutral-600 dark:text-neutral-400">
                                Results
                              </p>
                              <pre className="overflow-x-auto rounded bg-neutral-50 p-3 text-xs dark:bg-neutral-900">
                                {JSON.stringify(analysis.result_data, null, 2)}
                              </pre>
                            </div>
                          )}

                          {analysis.chart_data && (
                            <div>
                              <p className="mb-1 text-xs font-medium text-neutral-600 dark:text-neutral-400">
                                Chart
                              </p>
                              <div className="rounded bg-neutral-50 p-4 dark:bg-neutral-900">
                                {analysis.chart_data.image_base64 ? (
                                  <img
                                    src={`data:image/png;base64,${analysis.chart_data.image_base64}`}
                                    alt="Analysis chart"
                                    className="h-auto max-w-full"
                                  />
                                ) : (
                                  <pre className="overflow-x-auto text-xs">
                                    {JSON.stringify(analysis.chart_data, null, 2)}
                                  </pre>
                                )}
                              </div>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
