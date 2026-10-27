export type ReportType = 'literature_review' | 'gap_analysis' | 'source_comparison' | 'survey';

export type ReportStatus = 'pending' | 'generating' | 'completed' | 'failed';

export interface Report {
  id: string;
  project_id: string;
  type: ReportType;
  status: ReportStatus;
  title: string;
  content_markdown: string | null;
  error_message: string | null;
  created_at: string;
}