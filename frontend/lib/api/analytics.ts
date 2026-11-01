/**
 * Analytics API client for Phase 8 (CSV upload, profiling, AI analysis).
 *
 * Uses the shared `apiRequest` helper so envelope handling and `ApiError`
 * mapping stay in one place (design §6.1).
 */

import type { AnalyticsAnalysis, AnalyticsDataset } from '@/types/api';

import { apiRequest } from './client';

/**
 * Upload a CSV dataset for analysis.
 */
export async function uploadDataset(
  projectId: string,
  file: File,
  token: string,
): Promise<AnalyticsDataset> {
  const formData = new FormData();
  formData.append('file', file);

  return await apiRequest<AnalyticsDataset>(`/projects/${projectId}/analytics/datasets`, {
    method: 'POST',
    body: formData,
    token,
  });
}

/**
 * List all datasets in a project.
 */
export async function listDatasets(
  projectId: string,
  token: string,
): Promise<AnalyticsDataset[]> {
  return await apiRequest<AnalyticsDataset[]>(`/projects/${projectId}/analytics/datasets`, {
    token,
  });
}

/**
 * Get dataset details including profile.
 */
export async function getDataset(
  datasetId: string,
  token: string,
): Promise<AnalyticsDataset> {
  return await apiRequest<AnalyticsDataset>(`/analytics/datasets/${datasetId}`, { token });
}

/**
 * Ask an analysis question about a dataset.
 */
export async function analyzeDataset(
  datasetId: string,
  question: string,
  token: string,
): Promise<AnalyticsAnalysis> {
  return await apiRequest<AnalyticsAnalysis>(`/analytics/datasets/${datasetId}/analyze`, {
    method: 'POST',
    body: { question },
    token,
  });
}

/**
 * List all analyses for a dataset.
 */
export async function listAnalyses(
  datasetId: string,
  token: string,
): Promise<AnalyticsAnalysis[]> {
  return await apiRequest<AnalyticsAnalysis[]>(`/analytics/datasets/${datasetId}/analyses`, {
    token,
  });
}

/**
 * Get analysis results.
 */
export async function getAnalysis(
  analysisId: string,
  token: string,
): Promise<AnalyticsAnalysis> {
  return await apiRequest<AnalyticsAnalysis>(`/analytics/analyses/${analysisId}`, { token });
}

/**
 * Delete a dataset and all its analyses.
 */
export async function deleteDataset(datasetId: string, token: string): Promise<void> {
  await apiRequest<null>(`/analytics/datasets/${datasetId}`, {
    method: 'DELETE',
    token,
  });
}
