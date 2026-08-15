/**
 * Typed API client.
 *
 * Every backend response — success or failure — uses one envelope, so the client
 * has exactly one response-handling path (design §6.1). Callers receive unwrapped
 * `data` or an `ApiError` they can branch on by `code`.
 */

import { config } from '@/lib/config';
import type { ApiResponse, ErrorCode } from '@/types/api';

export class ApiError extends Error {
  readonly code: ErrorCode;
  readonly status: number;
  readonly requestId: string | null;

  constructor(params: {
    code: ErrorCode;
    message: string;
    status: number;
    requestId?: string | null;
  }) {
    super(params.message);
    this.name = 'ApiError';
    this.code = params.code;
    this.status = params.status;
    this.requestId = params.requestId ?? null;
  }
}

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  /** JSON-serialisable request body. */
  body?: unknown;
  /** Prefix the path with the API version segment. Defaults to `true`. */
  versioned?: boolean;
  /** Access token for authenticated routes. */
  token?: string | null;
  /**
   * Override the API base URL for this call. Server Components should pass
   * `config.serverApiBaseUrl` (design: Docker service-name resolution differs
   * from the browser-visible URL — see `lib/config.ts`).
   */
  baseUrl?: string;
}

function buildUrl(path: string, versioned: boolean, baseUrl: string): string {
  const normalisedPath = path.startsWith('/') ? path : `/${path}`;
  const prefix = versioned ? config.apiVersionPrefix : '';
  return `${baseUrl}${prefix}${normalisedPath}`;
}

function buildHeaders(options: RequestOptions): Headers {
  const headers = new Headers(options.headers);
  headers.set('Accept', 'application/json');

  if (options.body !== undefined) {
    headers.set('Content-Type', 'application/json');
  }
  if (options.token) {
    headers.set('Authorization', `Bearer ${options.token}`);
  }

  return headers;
}

async function readEnvelope<TData>(response: Response): Promise<ApiResponse<TData> | null> {
  try {
    return (await response.json()) as ApiResponse<TData>;
  } catch {
    // A non-JSON body means the failure happened before the application layer
    // (proxy error, connection reset). Handled by the caller as INTERNAL_ERROR.
    return null;
  }
}

/**
 * Perform a request and unwrap the envelope.
 *
 * `data` is `null` on success for endpoints with no payload (e.g. logout,
 * delete — design §6.1 shows `{ "success": true, "data": null }` as a valid
 * response), so callers that expect a value must type the generic parameter
 * accordingly rather than relying on a runtime null-check here.
 *
 * @throws {ApiError} when the transport fails or the envelope reports failure.
 */
export async function apiRequest<TData>(
  path: string,
  options: RequestOptions = {},
): Promise<TData> {
  const { body, versioned = true, token, baseUrl = config.apiBaseUrl, ...init } = options;
  void token; // consumed by buildHeaders; excluded from the fetch init

  let response: Response;
  try {
    response = await fetch(buildUrl(path, versioned, baseUrl), {
      ...init,
      headers: buildHeaders(options),
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError({
      code: 'INTERNAL_ERROR',
      message: 'The server could not be reached.',
      status: 0,
      requestId: null,
    });
  }

  const requestId = response.headers.get('X-Request-ID');
  const envelope = await readEnvelope<TData>(response);

  if (!response.ok || envelope?.success !== true) {
    throw new ApiError({
      code: envelope?.error?.code ?? 'INTERNAL_ERROR',
      message: envelope?.error?.message ?? 'The request failed.',
      status: response.status,
      requestId,
    });
  }

  return envelope.data as TData;
}
