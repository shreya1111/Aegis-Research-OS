# API Contract — Aegis Research OS

Authoritative reference: [`design.md` §6.1](../design.md). Resource names match
[`db-schema.md`](./db-schema.md).

## Conventions

**Base URL.** Versioned routes are mounted under `/api/v1`. The health probe is
mounted at the application root so deployment probes need not track API versions.

**Envelope.** Every response — success and failure — uses one shape.

```json
{ "success": true, "data": {}, "error": null }
```

```json
{ "success": false, "data": null, "error": { "code": "VALIDATION_ERROR", "message": "..." } }
```

**Pagination.** `?page=&page_size=` (`page` ≥ 1, `page_size` 1–100), returning:

```json
{ "success": true, "data": { "items": [], "total": 0, "page": 1, "page_size": 20 }, "error": null }
```

**Authentication.** All routes except `/health`, `/auth/register`, `/auth/login`, and
`/auth/refresh` require `Authorization: Bearer <access_token>`.

**Scoping.** Project-owned resources are addressed under `/projects/{id}/…`. Access to
a project outside the caller's scope returns **404**, not 403: the API does not
disclose the existence of resources the caller cannot see.

**Correlation.** Every response carries `X-Request-ID`. Clients may supply one and it
is echoed back, so a user-reported failure can be traced in the logs.

**Async operations.** Long operations return an identifier immediately; progress is
observed via a status resource or the trace stream.

## Error codes

Closed enum. Clients may branch on these values.

| Code | Status | Meaning |
| --- | --- | --- |
| `VALIDATION_ERROR` | 422 | Request or domain payload invalid |
| `UNAUTHENTICATED` | 401 | Missing, malformed, or expired credentials |
| `FORBIDDEN` | 403 | Authenticated but not permitted (Phase 10 roles) |
| `NOT_FOUND` | 404 | Resource absent, or outside the caller's scope |
| `CONFLICT` | 409 | Conflicts with existing state, e.g. duplicate email |
| `RATE_LIMITED` | 429 | Rate limit or usage quota exceeded |
| `UNSUPPORTED_FILE_TYPE` | 400 | Upload type not on the allow-list |
| `FILE_TOO_LARGE` | 400 | Upload exceeds the configured size limit |
| `LLM_PROVIDER_ERROR` | 502 | Active LLM provider unavailable |
| `EXPORT_FAILED` | 500 | Artifact export rendering failed |
| `INTERNAL_ERROR` | 500 | Unexpected fault; details in logs only |

## Endpoints

### Available now (Phase 0)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | none | Liveness. Returns `status`, `service`, `version`, `environment` |

### Authentication (Phase 1)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/register` | none | Create an account |
| POST | `/api/v1/auth/login` | none | Obtain access + refresh tokens |
| POST | `/api/v1/auth/refresh` | refresh token | Exchange for a new access token |
| GET | `/api/v1/auth/me` | bearer | Current user profile |

### Projects (Phase 1)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/projects` | bearer | List accessible projects (paginated) |
| POST | `/api/v1/projects` | bearer | Create a project |
| GET | `/api/v1/projects/{id}` | bearer | Project detail |
| DELETE | `/api/v1/projects/{id}` | bearer | Delete a project and all its content |

### Documents (Phase 3)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/projects/{id}/documents` | bearer | Upload a document (multipart; PDF, DOCX) |
| GET | `/api/v1/projects/{id}/documents` | bearer | List documents with processing status |
| GET | `/api/v1/documents/{id}` | bearer | Document detail, metadata, status |
| DELETE | `/api/v1/documents/{id}` | bearer | Delete a document and its chunks |

### Query and traces (Phases 4–5)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/projects/{id}/query` | bearer | Run hybrid RAG or the agent pipeline; streams the answer |
| GET | `/api/v1/projects/{id}/traces/{run_id}` | bearer | Ordered agent trace for a run |
| GET | `/api/v1/projects/{id}/traces/{run_id}/stream` | bearer | SSE stream of trace events for a live run |

### Reports (Phases 6, 9)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/projects/{id}/reports` | bearer | Generate an artifact (`literature_review`, `gap_analysis`, `comparison`, `survey`) |
| GET | `/api/v1/projects/{id}/reports` | bearer | List generated reports (paginated) |
| GET | `/api/v1/projects/{id}/reports/{report_id}` | bearer | Artifact Markdown and citations |
| GET | `/api/v1/projects/{id}/reports/{report_id}/export?format=` | bearer | Export as `pdf`, `docx`, or `latex` |

### Stretch

| Method | Path | Phase | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/projects/{id}/graph` | 7 | Knowledge graph nodes and edges |
| POST/GET | `/api/v1/projects/{id}/datasets` | 8 | CSV upload and profiling |
| GET/POST/DELETE | `/api/v1/projects/{id}/members` | 10 | Membership and roles |
| GET | `/api/v1/projects/{id}/activity` | 10 | Activity audit log |
| GET | `/api/v1/projects/{id}/usage` | 10 | Token, cost, and query counts from `agent_traces` |

## Rate limits

| Scope | Basis |
| --- | --- |
| `/auth/login`, `/auth/register` | Per IP and per email, short window |
| `/auth/refresh` | Per user |
| `/projects/{id}/query` | Per user |
| `/projects/{id}/reports` | Per user, tighter |
| Document upload | Per user, per project |
| Usage quotas | Per user and project, monthly token/query ceilings |

Exceeding a limit returns 429 with `error.code = "RATE_LIMITED"`.
