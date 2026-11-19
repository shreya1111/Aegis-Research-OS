# Aegis Research OS - Phase Log

## Phase 0: Analysis & Planning
- ✅ Requirements gathered and documented in design.md
- ✅ Architecture specified (modular monolith with agentic core)
- ✅ Database design (PostgreSQL + pgvector, Redis)
- ✅ API contract defined

## Phase 1: Authentication & Projects
- ✅ FR-A: Registration, login, bcrypt hashing, JWT tokens
- ✅ FR-B: Project create/list/access with ownership
- ✅ Tests: Registration, project creation, ownership

## Phase 2: (Not originally numbered - see design)

## Phase 3: Document Ingestion
- ✅ FR-C: PDF/DOCX upload, text extraction, OCR fallback
- ✅ Token-aware chunking with page references
- ✅ Embedding generation with sentence-transformers
- ✅ Status tracking (pending → processing → ready/failed)

## Phase 4: Hybrid RAG
- ✅ FR-D: Semantic (pgvector) + keyword (FTS) retrieval
- ✅ RRF fusion, optional cross-encoder re-ranking
- ✅ Metadata filtering, cited answer generation
- ✅ End-to-end RAG < 8s

## Phase 5: Multi-Agent System
- ✅ FR-E: 7 LangGraph agents (Supervisor, Retrieval, Summarizer, Fact-Checker, Synthesis, Memory, Critic)
- ✅ Agent traces logged with tokens/latency/cost
- ✅ Reasoning Trace panel in frontend
- ✅ Memory agent for project-level context

## Phase 6: Research Intelligence
- ⚠️ FR-F: Literature review, gap analysis, source comparison, survey generation.
  Report generation still runs on the templated `MockAgentService`
  (`report_service` → `agent_service_mock`), so artifacts are not yet retrieved from the
  project corpus. Wiring the real `AgentService` into `report_runner` is open work.
- ✅ Structured Markdown export
- ✅ Citation integrity validation

## Phase 7: Knowledge Graph (Stretch)
- ✅ Entity extraction during ingestion and retrieval
- ✅ Relational node/edge tables in PostgreSQL (migration `f3f6c804751d`)
- ✅ Interactive graph visualization (reactflow) with node-details sidebar
- ✅ Graph API with node-type filtering; unit and integration tests

## Phase 8: Dataset Analytics (Stretch)
- ✅ CSV upload with pandas profiling (migration `0008`)
- ✅ AI-generated analysis code run in a constrained child process: static checks,
  isolated interpreter, scratch directory, minimal environment, timeout, POSIX rlimits
- ✅ Chart generation; editor role required to upload or delete datasets
- ⚠️ Known limit: rlimits are POSIX-only, so generated code is refused outside POSIX
  when `ENVIRONMENT=production`
## Phase 9: Reports & Export (Core/Polish)
- ✅ FR-G: Markdown → PDF/DOCX/LaTeX export
- ✅ Executive summary generator
- ✅ Reports tab with re-export options

## Phase 10: Team Collaboration (Complete)
- ✅ FR-H6: Project membership (owner/editor/viewer roles)
- ✅ FR-H7: Activity audit log
- ✅ FR-H8: In-app notifications (member added, etc.)
- ✅ FR-H9: Per-project usage dashboard (tokens, cost, query counts)
- ✅ 12/12 integration tests passing
- ✅ 81/81 frontend unit tests passing
- ✅ Member roster, role changes, removals functional
- ✅ Viewer blocked from upload/delete
- ✅ Notification scoping (only owner can mark own notifications read)

## Phase 11: Testing/Security/Deployment Continuous
Delivered:
- ✅ `X-Request-ID` correlation across proxy, API logs, and responses
- ✅ Container health checks (Postgres, Redis, backend, frontend, proxy)
- ✅ CI: ruff, strict mypy, unit and integration tests, prettier, eslint, tsc, vitest,
  next build, `pip-audit`, `npm audit`, Docker image builds
- ✅ Frontend on Next.js 15 (clears the Next.js 14 advisories); patched test toolchain
- ✅ Security headers on API responses (nosniff, referrer policy, COOP, `frame-ancestors`,
  HSTS outside development); login, register, and query rate limits
- ✅ Production compose overlay behind an nginx proxy

Not delivered (tracked as follow-ups):
- ⬜ Metrics endpoint
- ⬜ Full Content-Security-Policy for the Next.js frontend
- ⬜ httpOnly-cookie token storage (tokens are in `localStorage`; design §9.2)
- ⬜ Durable job queue (`BackgroundTasks` jobs do not survive a restart; design R18)
- ⬜ Stronger analytics sandbox boundary (container or unprivileged user)