/**
 * Wire contracts mirroring the backend Pydantic schemas (design §6.1).
 *
 * Field names are `snake_case` on purpose: the API and the client share one
 * vocabulary so no translation layer is needed.
 */

export const ERROR_CODES = [
  'VALIDATION_ERROR',
  'UNAUTHENTICATED',
  'FORBIDDEN',
  'NOT_FOUND',
  'CONFLICT',
  'RATE_LIMITED',
  'UNSUPPORTED_FILE_TYPE',
  'FILE_TOO_LARGE',
  'LLM_PROVIDER_ERROR',
  'EXPORT_FAILED',
  'INTERNAL_ERROR',
] as const;

export type ErrorCode = (typeof ERROR_CODES)[number];

export interface ErrorDetail {
  code: ErrorCode;
  message: string;
}

export interface ApiResponse<TData> {
  success: boolean;
  data: TData | null;
  error: ErrorDetail | null;
}

export interface Page<TItem> {
  items: TItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  environment: string;
}

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AccessToken {
  access_token: string;
  token_type: string;
}

export interface Project {
  id: string;
  title: string;
  description: string | null;
  created_at: string;
}

export const DOCUMENT_STATUSES = ['pending', 'processing', 'ready', 'failed'] as const;

export type DocumentStatus = (typeof DOCUMENT_STATUSES)[number];

export interface DocumentMetadata {
  title: string | null;
  authors: string[];
  page_count: number | null;
  mime_type: string;
  size_bytes: number;
  ocr_used: boolean;
  ocr_low_confidence: boolean;
  ocr_min_confidence: number | null;
  failure_reason: string | null;
}

export interface Document {
  id: string;
  project_id: string;
  filename: string;
  status: DocumentStatus;
  metadata: DocumentMetadata;
  uploaded_at: string;
}

/** design §6.1, §8.8 — one retrieved chunk returned alongside an answer. */
export interface QuerySource {
  chunk_id: string;
  document_id: string;
  document_filename: string;
  content: string;
  source_ref: Record<string, unknown>;
  rank: number;
}

/** design §7.2 — one resolved citation marker in ``messages.citations``. */
export interface Citation {
  marker: string;
  chunk_id?: string;
  document_id?: string;
  page?: number | null;
  external_source?: {
    title: string;
    url: string | null;
    provider: string;
  };
}

export interface QueryFilters {
  document_ids?: string[];
  uploaded_after?: string;
  uploaded_before?: string;
}

export interface QueryRequestPayload {
  question: string;
  conversation_id?: string;
  filters?: QueryFilters;
}

/** design §6.5 — ``pipeline`` distinguishes the Phase 4 fast path from a
 * Phase 5 multi-agent run; both share this response shape. */
export interface QueryResponse {
  run_id: string;
  message_id: string;
  answer: string;
  citations: Citation[];
  sources: QuerySource[];
  citation_warning: boolean;
  pipeline: 'rag' | 'agent';
}

/** design §4.6, §5.7 — one agent-node invocation, rendered in the trace panel. */
export interface TraceStep {
  id: string;
  agent_name: string;
  input_summary: string;
  output_summary: string;
  tokens_used: number;
  latency_ms: number;
  estimated_cost: number;
  status: string;
  created_at: string;
}

export interface TraceRun {
  run_id: string;
  steps: TraceStep[];
}

// Analytics types for Phase 8
export const ANALYTICS_DATASET_STATUSES = ['pending', 'profiled', 'failed'] as const;
export type AnalyticsDatasetStatus = (typeof ANALYTICS_DATASET_STATUSES)[number];

export const ANALYTICS_ANALYSIS_STATUSES = ['pending', 'completed', 'failed'] as const;
export type AnalyticsAnalysisStatus = (typeof ANALYTICS_ANALYSIS_STATUSES)[number];

export interface AnalyticsDataset {
  id: string;
  project_id: string;
  filename: string;
  status: AnalyticsDatasetStatus;
  row_count: number | null;
  column_count: number | null;
  profile_data: Record<string, any> | null;
  file_path: string;
  created_at: string;
}

export interface AnalyticsAnalysis {
  id: string;
  dataset_id: string;
  project_id: string;
  question: string;
  analysis_code: string | null;
  result_data: Record<string, any> | null;
  chart_data: Record<string, any> | null;
  explanation: string | null;
  status: AnalyticsAnalysisStatus;
  error_message: string | null;
  created_at: string;
}
