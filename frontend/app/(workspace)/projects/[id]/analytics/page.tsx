'use client';

import { useParams } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

import { ApiError } from '@/lib/api/client';
import {
  analyzeDataset,
  deleteDataset,
  getDataset,
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
    [projectId, getValidAccessToken]
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
    [getValidAccessToken]
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
      notify({ message: 'Please upload a CSV file', type: 'error' });
      return;
    }

    setIsUploading(true);
    try {
      const token = await getValidAccessToken();
      if (!token) {
        throw new Error('Not authenticated');
      }
      await uploadDataset(projectId, file, token);
      notify({ message: 'Dataset uploaded successfully', type: 'success' });
      await fetchDatasets('refresh');
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : 'Failed to upload dataset';
      notify({ message, type: 'error' });
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
      notify({ message: 'Dataset deleted', type: 'success' });
      if (selectedDataset?.id === datasetId) {
        setSelectedDataset(null);
        setAnalyses([]);
      }
      await fetchDatasets('refresh');
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : 'Failed to delete dataset';
      notify({ message, type: 'error' });
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
      notify({ message: 'Analysis started', type: 'success' });
      setQuestion('');
      // Poll for results
      setTimeout(() => fetchAnalyses(selectedDataset.id), 2000);
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : 'Analysis failed';
      notify({ message, type: 'error' });
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
        <Alert type="error">
          Failed to load analytics. Please refresh the page.
        </Alert>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Left panel: Dataset list */}
      <div className="w-80 border-r border-neutral-200 dark:border-neutral-800 p-4 space-y-4 overflow-y-auto">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Datasets</h2>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={handleUpload}
          />
          <Button
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
          >
            {isUploading ? 'Uploading...' : 'Upload CSV'}
          </Button>
        </div>

        {datasets.length === 0 ? (
          <EmptyState
            message="No datasets yet"
            description="Upload a CSV file to get started"
          />
        ) : (
          <div className="space-y-2">
            {datasets.map((dataset) => (
              <div
                key={dataset.id}
                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                  selectedDataset?.id === dataset.id
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-950'
                    : 'border-neutral-200 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-900'
                }`}
                onClick={() => setSelectedDataset(dataset)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {dataset.filename}
                    </p>
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
                    className="ml-2 text-neutral-400 hover:text-red-600 text-xs"
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
      <div className="flex-1 p-6 overflow-y-auto">
        {!selectedDataset ? (
          <EmptyState message="Select a dataset to view details and run analyses" />
        ) : (
          <div className="space-y-6">
            {/* Dataset profile */}
            <div>
              <h3 className="text-lg font-semibold mb-2">Dataset Profile</h3>
              {selectedDataset.status === 'pending' && (
                <Alert type="info">Profiling dataset...</Alert>
              )}
              {selectedDataset.status === 'failed' && (
                <Alert type="error">
                  Profiling failed: {selectedDataset.profile_data?.error || 'Unknown error'}
                </Alert>
              )}
              {selectedDataset.status === 'profiled' && selectedDataset.profile_data && (
                <div className="bg-neutral-50 dark:bg-neutral-900 p-4 rounded-lg space-y-2">
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
                      <p className="text-sm font-medium mb-2">Columns:</p>
                      <div className="space-y-1 max-h-48 overflow-y-auto">
                        {Object.entries(selectedDataset.profile_data.columns).map(
                          ([name, info]: [string, any]) => (
                            <div
                              key={name}
                              className="text-xs flex items-center justify-between py-1 px-2 bg-white dark:bg-neutral-800 rounded"
                            >
                              <span className="font-mono">{name}</span>
                              <span className="text-neutral-600 dark:text-neutral-400">
                                {info.dtype}
                              </span>
                            </div>
                          )
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Analysis question */}
            {selectedDataset.status === 'profiled' && (
              <div>
                <h3 className="text-lg font-semibold mb-2">Ask a Question</h3>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
                    placeholder="E.g., What is the average age by gender?"
                    className="flex-1 px-3 py-2 border border-neutral-300 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-900 text-sm"
                    disabled={isAnalyzing}
                  />
                  <Button
                    onClick={handleAnalyze}
                    disabled={!question.trim() || isAnalyzing}
                  >
                    {isAnalyzing ? 'Analyzing...' : 'Analyze'}
                  </Button>
                </div>
              </div>
            )}

            {/* Analyses list */}
            <div>
              <h3 className="text-lg font-semibold mb-2">Analyses</h3>
              {analyses.length === 0 ? (
                <EmptyState message="No analyses yet" description="Ask a question to get started" />
              ) : (
                <div className="space-y-4">
                  {analyses.map((analysis) => (
                    <div
                      key={analysis.id}
                      className="border border-neutral-200 dark:border-neutral-800 rounded-lg p-4 space-y-3"
                    >
                      <div>
                        <p className="font-medium text-sm">{analysis.question}</p>
                        <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-1">
                          {new Date(analysis.created_at).toLocaleString()}
                        </p>
                      </div>

                      {analysis.status === 'pending' && (
                        <Alert type="info">Running analysis...</Alert>
                      )}

                      {analysis.status === 'failed' && (
                        <Alert type="error">
                          {analysis.error_message || 'Analysis failed'}
                        </Alert>
                      )}

                      {analysis.status === 'completed' && (
                        <>
                          {analysis.explanation && (
                            <div className="bg-blue-50 dark:bg-blue-950 p-3 rounded text-sm">
                              <p className="font-medium text-blue-900 dark:text-blue-100 mb-1">
                                Explanation
                              </p>
                              <p className="text-blue-800 dark:text-blue-200">
                                {analysis.explanation}
                              </p>
                            </div>
                          )}

                          {analysis.analysis_code && (
                            <div>
                              <p className="text-xs font-medium mb-1 text-neutral-600 dark:text-neutral-400">
                                Generated Code
                              </p>
                              <pre className="bg-neutral-900 text-neutral-100 p-3 rounded text-xs overflow-x-auto">
                                {analysis.analysis_code}
                              </pre>
                            </div>
                          )}

                          {analysis.result_data && (
                            <div>
                              <p className="text-xs font-medium mb-1 text-neutral-600 dark:text-neutral-400">
                                Results
                              </p>
                              <pre className="bg-neutral-50 dark:bg-neutral-900 p-3 rounded text-xs overflow-x-auto">
                                {JSON.stringify(analysis.result_data, null, 2)}
                              </pre>
                            </div>
                          )}

                          {analysis.chart_data && (
                            <div>
                              <p className="text-xs font-medium mb-1 text-neutral-600 dark:text-neutral-400">
                                Chart
                              </p>
                              <div className="bg-neutral-50 dark:bg-neutral-900 p-4 rounded">
                                {analysis.chart_data.image_base64 ? (
                                  <img
                                    src={`data:image/png;base64,${analysis.chart_data.image_base64}`}
                                    alt="Analysis chart"
                                    className="max-w-full h-auto"
                                  />
                                ) : (
                                  <pre className="text-xs overflow-x-auto">
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
