import { apiRequest } from './client';
import type { Report, ReportType } from '@/types/report';

export type ExportFormat = 'pdf' | 'docx' | 'html' | 'markdown' | 'latex';

export async function createReport(
  projectId: string,
  type: ReportType,
  title: string,
  token?: string,
): Promise<Report> {
  return await apiRequest<Report>(`/projects/${projectId}/reports`, {
    method: 'POST',
    body: { type, title },
    token,
  });
}

export async function listReports(projectId: string, token?: string): Promise<Report[]> {
  return await apiRequest<Report[]>(`/projects/${projectId}/reports`, {
    token,
  });
}

export async function getReport(reportId: string, token?: string): Promise<Report> {
  return await apiRequest<Report>(`/reports/${reportId}`, {
    token,
  });
}

export async function deleteReport(reportId: string, token?: string): Promise<void> {
  return await apiRequest<void>(`/reports/${reportId}`, {
    method: 'DELETE',
    token,
  });
}

export async function exportReport(
  reportId: string,
  format: ExportFormat,
  token?: string,
): Promise<Blob> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/reports/${reportId}/export?format=${format}`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }
  );

  if (!response.ok) {
    throw new Error(`Export failed: ${response.statusText}`);
  }

  return await response.blob();
}

export async function generateSummary(
  reportId: string,
  token?: string,
): Promise<string> {
  return await apiRequest<string>(`/reports/${reportId}/summary`, {
    method: 'POST',
    token,
  });
}
