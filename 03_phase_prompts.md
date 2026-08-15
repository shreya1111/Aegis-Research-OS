# Phase Prompts — Aegis Research OS

Run these **in order**, one at a time, after the master prompt has been accepted by your coding agent. Each is self-contained: paste it verbatim as a new message.

---

## Phase 0 — Research & Planning

```
PHASE 0: Research & Planning

Goal: Produce the complete blueprint before any code is written.

Deliverables:
1. `docs/architecture.md` — high-level architecture diagram (as a Mermaid diagram in Markdown)
   showing frontend, backend, database, agent layer, and external APIs.
2. `docs/db-schema.md` — initial ER diagram (Mermaid) and table definitions for: users, projects
   (research workspaces), documents, document_chunks (with vector column), agent_traces, reports,
   conversations, messages.
3. `docs/agents.md` — list of the 7 core agents (Supervisor, Retrieval, Summarizer,
   Fact-Checker/Citation, Synthesis/Report-Writer, Memory, Critic/Reviewer), each with: purpose,
   inputs, outputs, which LLM tier it uses, and which external tools/APIs it calls.
4. `docs/api-contract.md` — REST endpoint list (method, path, purpose) for auth, projects,
   documents, chat/agent-run, and reports. Use consistent JSON envelope conventions.
5. Initialize the GitHub repository with the folder structure from the master prompt, a root
   README.md (project description, setup instructions placeholder), and a .gitignore for
   Python + Node.

Acceptance criteria: All 4 docs exist and are internally consistent (table names in db-schema.md
match references in api-contract.md and agents.md). Repo builds an empty Next.js app and an empty
FastAPI app that both start successfully.
```

---

## Phase 1 — Foundation

```
PHASE 1: Foundation

Goal: A user can register, log in, and create a research workspace ("project").

Backend:
- FastAPI app with routers for /auth (register, login, refresh, me) and /projects (CRUD).
- JWT auth with password hashing (bcrypt). Access + refresh token flow.
- SQLAlchemy models + Alembic migration for: users, projects.
- PostgreSQL via Docker Compose, with the pgvector extension enabled in the init migration.

Frontend:
- Next.js app with Tailwind + shadcn/ui installed.
- Pages: /login, /register, /dashboard (list + create projects), /projects/[id] (empty workspace
  shell for now).
- Auth state management (e.g., a simple auth context + httpOnly cookie or token storage) and
  route protection for authenticated pages.

Infra:
- docker-compose.yml bringing up: postgres, redis, backend, frontend.
- .env.example with all required variables documented.

Acceptance criteria: `docker compose up` starts all services. A new user can register, log in,
create a project, see it on the dashboard, and open its (currently empty) workspace page. Include
at least 3 backend unit tests (registration, login, project creation) and one frontend smoke test.
```

---

## Phase 2 — Premium UI/UX Pass

```
PHASE 2: UI/UX Pass

Goal: Bring the shell built in Phase 1 to a polished, portfolio-quality standard, and scaffold the
remaining page layouts (even if their functionality isn't built yet).

Scope:
- Landing page (marketing-style, explains what Aegis Research OS does).
- Dashboard: project cards, empty states, create-project modal.
- Workspace shell with a persistent layout: left nav (Chat, Documents, Knowledge Graph [stretch,
  show as "coming soon"], Reports, Settings), main content area.
- Chat UI shell: message list + input, ready to be wired to the agent pipeline in Phase 5.
- Dark mode toggle (persisted preference).
- Loading skeletons for async content, toast notifications for errors/success.
- Responsive layout down to mobile width.

Do not fabricate backend functionality — where a feature isn't built yet (knowledge graph,
reports), show a clearly-labeled placeholder/empty state rather than fake data.

Acceptance criteria: Every screen listed above renders correctly at desktop and mobile widths,
dark/light mode both look intentional (not just inverted colors), and there is no layout shift or
broken state when data is empty vs loading vs populated.
```

---

## Phase 3 — Document Intelligence

```
PHASE 3: Document Intelligence

Goal: A user can upload PDF/DOCX documents into a project and have them processed into searchable
chunks with embeddings.

Backend:
- POST /projects/{id}/documents (multipart upload) — accepts PDF and DOCX.
- Text extraction: PDF via pypdf/pdfplumber, DOCX via python-docx. Include basic OCR fallback for
  scanned PDFs (e.g., pytesseract) — flag clearly if OCR quality is low rather than silently
  producing garbage text.
- Metadata extraction: title, authors (best-effort), page count, upload date.
- Chunking: token-aware chunking (~500-800 tokens per chunk with overlap), preserving page/section
  reference for later citation.
- Embeddings: use a sentence-transformers model (e.g., all-MiniLM-L6-v2 or a stronger multilingual
  model) to embed each chunk; store vectors in the pgvector column on document_chunks.
- Background processing (FastAPI BackgroundTasks) so upload returns immediately and processing
  status is pollable (GET /documents/{id} returns status: pending/processing/ready/failed).

Frontend:
- Documents tab in the workspace: drag-and-drop upload, list of documents with processing status,
  ability to view extracted metadata and delete a document.

Acceptance criteria: Uploading a real multi-page PDF results in chunks with embeddings visible in
the database, status transitions correctly through the pipeline, and a failed extraction (e.g.
corrupt file) is handled gracefully with a clear error state, not a crash.
```

---

## Phase 4 — Hybrid RAG

```
PHASE 4: Hybrid Retrieval-Augmented Generation

Goal: Given a natural-language question, return an accurate, cited answer grounded in a project's
uploaded documents.

Backend:
- Semantic search: cosine similarity search over pgvector embeddings, scoped to the project.
- Keyword search: PostgreSQL full-text search (tsvector/tsquery) over chunk text.
- Hybrid fusion: combine semantic + keyword results via reciprocal rank fusion.
- Optional re-ranking step using a cross-encoder model over the fused top-K before passing to the
  LLM.
- Metadata filtering: allow filtering by document, date range, or section.
- Answer generation: pass top-N chunks as context to the LLM (via the LLMProvider abstraction,
  "strong" tier), require the model to cite chunk/document sources inline (e.g., [Doc 2, p.4]),
  and return both the answer text and a structured list of source chunks used.
- POST /projects/{id}/query endpoint implementing the above, plus persisting the Q&A as a
  conversation message.

Frontend:
- Wire the Chat UI shell (from Phase 2) to this endpoint: user asks a question, sees a streaming
  or at-least-progressive answer, with citations rendered as clickable references that open the
  source chunk/document.

Acceptance criteria: Build the small gold-standard test set described in the improvements doc
(5-10 Q&A pairs against a known test document set). Report retrieval precision and confirm that
generated answers cite only chunks that were actually retrieved (no hallucinated citations).
```

---

## Phase 5 — Multi-Agent System

```
PHASE 5: Multi-Agent System

Goal: Replace the single-shot RAG query from Phase 4 with a LangGraph-orchestrated multi-agent
pipeline for complex research requests (not just single-question lookups).

Build these 7 core agents as LangGraph nodes:
1. Supervisor/Planner — decomposes a research request into subtasks and routes to the right agents.
2. Retrieval Agent — performs hybrid search from Phase 4, plus external calls to arXiv, Semantic
   Scholar, CORE, and CrossRef APIs when the request needs sources beyond the uploaded documents.
3. Summarizer Agent — condenses retrieved material per subtask ("fast" tier).
4. Fact-Checker/Citation Agent — verifies claims against retrieved sources and normalizes citations.
5. Synthesis/Report-Writer Agent — combines summarized, fact-checked material into a coherent
   answer ("strong" tier).
6. Memory Agent — maintains project-level long-term context (past queries, established facts)
   so repeated questions in a project build on prior context rather than starting cold.
7. Critic/Reviewer Agent — reviews the synthesized output for coherence, unsupported claims, and
   completeness before it's returned to the user; can send the task back to earlier agents once.

Requirements:
- Every agent call goes through the LLMProvider abstraction with an explicit model_tier.
- Every agent invocation is logged to agent_traces (agent name, input summary, output summary,
  tokens, latency, cost estimate) and exposed via GET /projects/{id}/traces/{run_id}.
- Frontend: add a collapsible "Reasoning Trace" panel in the Chat UI showing the live sequence of
  agent steps for the current run (poll or stream from the traces endpoint).
- Redis caching of any deterministic sub-step (e.g., repeated external API calls for the same
  query) to control cost.

Acceptance criteria: A multi-part research question (e.g., "compare approach A and B and identify
open gaps") visibly triggers multiple agents in the trace panel, produces a synthesized answer with
citations from both the uploaded documents and external academic APIs, and the Critic agent
demonstrably catches and flags at least one deliberately-injected unsupported claim in a test case.
```

---

## Phase 6 — Research Intelligence

```
PHASE 6: Research Intelligence Features

Goal: Move from "answering questions" to "producing research artifacts."

Features (build on the Phase 5 agent pipeline):
- Literature Review generation: given a topic/project, produce a structured literature review
  (introduction, thematic sections, synthesis, gaps, references) as Markdown.
- Research Gap Detection: identify and list explicit gaps/contradictions found across retrieved
  sources, each with supporting citations.
- Paper/Source Comparison: given 2+ documents or sources, produce a structured comparison
  (methodology, findings, limitations) as a table.
- Survey Generation: a longer-form multi-section survey combining literature review + comparison
  + gap analysis for a full topic.
- (If time allows) Trend Analysis and Novel Hypothesis Generation as additional agent-driven
  outputs — treat these as stretch within this phase, not blocking.

Frontend:
- A "Generate" panel in the workspace where the user picks an artifact type (Lit Review / Gap
  Analysis / Comparison / Survey), sees generation progress via the trace panel, and views the
  resulting Markdown artifact with proper formatting and clickable citations.

Acceptance criteria: Generating a literature review for a project with 5+ uploaded documents
produces a coherent, properly-cited Markdown document in under a defined time budget (e.g., 2
minutes), with no citation pointing to a source that wasn't actually retrieved.

--- MVP CHECKPOINT ---
At this point the core product is feature-complete. Before proceeding to any stretch phase (7-10),
do a full pass: fix bugs, add missing tests, and make sure `docker compose up` + a fresh signup +
upload + query + generate-report flow works end-to-end without manual intervention. This is your
demoable MVP.
```

---

## Phase 7 — Knowledge Graph (Stretch)

```
PHASE 7: Knowledge Graph (STRETCH — only start after the MVP checkpoint is solid)

Goal: Visual exploration of relationships between papers, authors, topics, and institutions
referenced across a project's documents and retrieved sources.

Approach: Model the graph relationally first (nodes/edges tables in PostgreSQL) rather than
introducing Neo4j, unless you have already validated Neo4j setup and have time budget for the
extra infra. Extract entities (authors, topics, institutions) during document processing and from
agent retrieval results; store relationships (co-authorship, citation, topic-membership).

Frontend:
- Interactive graph visualization (e.g., react-flow or cytoscape.js) in a new "Knowledge Graph"
  tab, with filtering by node type and click-to-inspect.

Acceptance criteria: For a project with 5+ documents, the graph renders a non-trivial network
(at least authors + topics + citation edges) and clicking a node shows its details and links back
to source documents.
```

---

## Phase 8 — Analytics & Data Science (Stretch)

```
PHASE 8: Analytics & Data Science (STRETCH)

Goal: Allow users to upload a CSV dataset and get AI-assisted statistical analysis and charts.

Backend:
- CSV upload endpoint, basic profiling (column types, summary stats via pandas).
- A sandboxed Python execution step for AI-generated analysis code (must be sandboxed/resource
  limited — do not execute arbitrary code with full host access).
- Chart generation (e.g., via matplotlib/plotly) rendered back to the frontend as images or
  interactive chart configs.

Frontend:
- Analytics tab: upload CSV, see auto-generated profiling summary, ask natural-language questions
  about the data, view resulting charts and a plain-language explanation.

Acceptance criteria: Uploading a sample CSV and asking "what's the trend in column X over time"
produces a correct chart and a correct plain-language summary, and malicious/error-prone code
(e.g., infinite loop, file system access attempt) is safely contained or rejected.
```

---

## Phase 9 — Report Generation & Export

```
PHASE 9: Report Generation & Export

Goal: Turn any generated artifact (literature review, survey, comparison, gap analysis) into
polished, exportable documents.

Backend:
- Export pipeline: Markdown (source of truth) → PDF, DOCX, and LaTeX.
  - PDF: via a Markdown-to-PDF pipeline (e.g., WeasyPrint or a headless-browser print-to-PDF).
  - DOCX: via python-docx, mapping Markdown structure (headings, lists, tables) to Word styles.
  - LaTeX: template-based conversion (pandoc is acceptable here) producing a compilable .tex file.
- Executive summary generator: given a full report, produce a condensed 1-page summary.

Frontend:
- "Export" button on any generated artifact with format selection and download.
- A Reports tab listing all previously generated reports per project with re-export options.

Acceptance criteria: Every export format opens correctly in its respective viewer (Adobe Reader,
MS Word, a LaTeX compiler) with headings, citations, and tables preserved and readable.
```

---

## Phase 10 — Enterprise Features (Stretch)

```
PHASE 10: Enterprise Features (STRETCH — only if time remains after Phases 7-9)

Goal: Multi-user collaboration within a project.

Features:
- Team/organization model: invite users to a project with roles (owner/editor/viewer).
- Activity history: audit log of who did what (uploads, queries, report generation) per project.
- Notifications: in-app notification when a long-running generation (e.g., survey) completes.
- Basic cost/API-usage dashboard per project (tokens used, estimated cost, query count), built
  from the agent_traces data already being logged since Phase 5.

Acceptance criteria: A second invited user can log in, see the shared project, and their actions
appear correctly in the activity log with correct role-based permission enforcement (e.g., a
viewer cannot upload or delete documents).
```

---

## Phase 11 — Testing, Security & Deployment

```
PHASE 11: Testing, Security Hardening & Deployment

Goal: Production-ready, secure, and deployed application, plus final documentation.

Testing:
- Backend: raise unit test coverage on core services (auth, retrieval, agent orchestration,
  export) to a meaningful level; add integration tests for the full upload → query → report flow.
- Frontend: add tests for critical flows (auth, chat interaction, document upload).
- Load-test the query endpoint with a realistic concurrent-user scenario and record results for
  the project report.

Security hardening:
- Input validation and file-type/size limits on uploads.
- Rate limiting on auth and query endpoints (Redis-backed).
- Secrets management via environment variables only, never committed; confirm .env is gitignored.
- Basic sandboxing review of the Phase 8 code-execution feature (if built).
- Dependency vulnerability scan (e.g., pip-audit, npm audit) with issues resolved or documented.

Deployment:
- Finalize docker-compose.yml for a single-VM deployment; document the steps to deploy to a
  platform such as Railway, Render, or a university-provided VM.
- Add basic monitoring/logging (structured logs, a simple health-check endpoint per service).
- Tag a v1.0 release in the repo.

Documentation:
- Finalize README.md with setup, architecture overview, and screenshots.
- Compile PHASE_LOG.md entries into `docs/build-history.md`.
- Produce the final project report using `05_project_report_outline.md` as the structure.

Acceptance criteria: A fresh clone of the repo, following only the README, results in a fully
running application via `docker compose up` with no undocumented manual steps.
```
