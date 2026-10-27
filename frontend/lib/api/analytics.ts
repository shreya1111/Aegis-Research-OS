/**
 * Analytics API client for Phase 8 (CSV upload, profiling, AI analysis).
 */

import type {
  AnalyticsAnalysis,
  AnalyticsDataset,
  ApiResponse,
} from '@/types/api';
import { apiClient } from './client';

/**
 * Upload a CSV dataset for analysis.
 */
export async function uploadDataset(
  projectId: string,
  file: File,
  token: string
): Promise<AnalyticsDataset> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<ApiResponse<AnalyticsDataset>>(
    `/projects/${projectId}/analytics/datasets`,
    formData,
    {
      headers: {
        Authorization: `Bearer ${token}`,
        // Don't set Content-Type; browser will set it with boundary
      },
    }
  );

  if (!response.data.success || !response.data.data) {
    throw new Error(response.data.error?.message || 'Upload failed');
  }

  return response.data.data;
}

/**
 * List all datasets in a project.
 */
export async function listDatasets(
  projectId: string,
  token: string
): Promise<AnalyticsDataset[]> {
  const response = await apiClient.get<ApiResponse<AnalyticsDataset[]>>(
    `/projects/${projectId}/analytics/datasets`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );

  if (!response.data.success || !response.data.data) {
    throw new Error(response.data.error?.message || 'Failed to list datasets');
  }

  return response.data.data;
}

/**
 * Get dataset details including profile.
 */
export async function getDataset(
  datasetId: string,
  token: string
): Promise<AnalyticsDataset> {
  const response = await apiClient.get<ApiResponse<AnalyticsDataset>>(
    `/analytics/datasets/${datasetId}`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );

  if (!response.data.success || !response.data.data) {
    throw new Error(response.data.error?.message || 'Failed to get dataset');
  }

  return response.data.data;
}

/**
 * Ask an analysis question about a dataset.
 */
export async function analyzeDataset(
  datasetId: string,
  question: string,
  token: string
): Promise<AnalyticsAnalysis> {
  const response = await apiClient.post<ApiResponse<AnalyticsAnalysis>>(
    `/analytics/datasets/${datasetId}/analyze`,
    { question },
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );

  if (!response.data.success || !response.data.data) {
    throw new Error(response.data.error?.message || 'Analysis failed');
  }

  return response.data.data;
}

/**
 * List all analyses for a dataset.
 */
export async function listAnalyses(
  datasetId: string,
  token: string
): Promise<AnalyticsAnalysis[]> {
  const response = await apiClient.get<ApiResponse<AnalyticsAnalysis[]>>(
    `/analytics/datasets/${datasetId}/analyses`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );

  if (!response.data.success || !response.data.data) {
    throw new Error(response.data.error?.message || 'Failed to list analyses');
  }

  return response.data.data;
}

/**
 * Get analysis results.
 */
export async function getAnalysis(
  analysisId: string,
  token: string
): Promise<AnalyticsAnalysis> {
  const response = await apiClient.get<ApiResponse<AnalyticsAnalysis>>(
    `/analytics/analyses/${analysisId}`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );

  if (!response.data.success || !response.data.data) {
    throw new Error(response.data.error?.message || 'Failed to get analysis');
  }

  return response.data.data;
}

/**
 * Delete a dataset and all its analyses.
 */
export async function deleteDataset(
  datasetId: string,
  token: string
): Promise<void> {
  const response = await apiClient.delete<ApiResponse<null>>(
    `/analytics/datasets/${datasetId}`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );

  if (!response.data.success) {
    throw new Error(response.data.error?.message || 'Delete failed');
  }
}
