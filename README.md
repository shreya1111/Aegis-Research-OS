# Aegis Research OS

Autonomous multi-agent AI research assistant. Create a project workspace, upload your
sources, and ask research-grade questions: a coordinated set of specialised agents
plans the work, retrieves evidence from your documents and the open academic web,
verifies claims against those sources, and composes cited research artifacts you can
export as PDF, DOCX, or LaTeX.

Three commitments shape the system:

- **Grounded, never guessed.** Every claim carries a citation to a chunk that was
  actually retrieved, enforced by a validation gate plus dedicated Fact-Checker and
  Critic agents.
- **Transparent reasoning.** A Reasoning Trace panel shows which agent ran, what it
  produced, and what it cost — in tokens, latency, and dollars.
- **Operationally simple.** Four moving parts: PostgreSQL (with pgvector), Redis,
  FastAPI, Next.js.

## Documentation

| Document | Contents |
| --- | --- |
| [`design.md`](./design.md) | Full system design — the authoritative reference |
| [`docs/architecture.md`](./docs/architecture.md) | Architecture at a glance, layering, delivered state |
| [`docs/db-schema.md`](./docs/db-schema.md) | ER diagram, tables, indexing, multi-tenancy |
| [`docs/agents.md`](./docs/agents.md) | The seven core agents: purpose, I/O, tier, tools |
| [`docs/api-contract.md`](./docs/api-contract.md) | Endpoints, envelope, error codes, rate limits |

## Technology

| Layer | Choice |
| --- | --- |
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.11+, Pydantic v2 |
| Database | PostgreSQL 16 with pgvector — relational data, embeddings, and full-text search |
| Cache | Redis — response cache, external-source cache, rate limiting, run status |
| Orchestration | LangGraph (from Phase 5) |
| Deployment | Docker Compose; single VM or PaaS |

## Prerequisites

- Docker and Docker Compose — the only requirement for running the full stack
- For running a workspace directly: Python 3.11+ and Node.js 20+

## Quick start

```bash
git clone <repository-url>
cd aegis-research-os

# Create .env from the documented contract, then set POSTGRES_PASSWORD
cp deployment/.env.example .env

docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.dev.yml up
```

| Service | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| Backend health | http://localhost:8000/health |
| API docs (non-production only) | http://localhost:8000/docs |

The landing page reports whether the API is reachable, so a successful start is
visible without reading logs.

## Local development without Docker

One script provisions both workspaces and is safe to re-run:

```powershell
# Windows
pwsh ./scripts/dev-setup.ps1
```

```bash
# Linux / macOS
./scripts/dev-setup.sh
```

Then run each workspace directly:

```bash
# Backend — from backend/
.venv/bin/python -m uvicorn app.main:app --reload      # Windows: .venv\Scripts\python.exe

# Frontend — from frontend/
npm run dev
```

## Quality gates

`scripts/verify.ps1` (or `verify.sh`) runs every gate in the same order as CI:

| Workspace | Gates |
| --- | --- |
| Backend | `ruff check`, `ruff format --check`, `mypy app tests`, `pytest` |
| Frontend | `prettier --check`, `eslint`, `tsc --noEmit`, `vitest run`, `next build` |

CI additionally audits dependencies (`pip-audit`, `npm audit`) and builds both Docker
images. LLM providers are always stubbed in tests: the suite is deterministic and
never spends API budget.

Backend integration tests run against a real PostgreSQL instance and need a
dedicated `aegis_test` database (schema is created and dropped per test, so this
database stays empty between runs — it only needs to exist once):

```bash
docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.dev.yml \
  exec postgres psql -U aegis -d aegis -c "CREATE DATABASE aegis_test"
```

## Configuration

`deployment/.env.example` is the configuration contract — every variable documented
with a placeholder, extended by the phase that introduces it. `.env` is gitignored and
must never be committed. Secrets are read only through the typed settings object in
`backend/app/core/config.py`; a missing or malformed value fails at startup rather
than mid-request. Only non-sensitive `NEXT_PUBLIC_`-prefixed values reach the browser.

## Repository layout

```
aegis-research-os/
├── frontend/          Next.js 14 App Router — app/ components/ lib/ types/ tests/
├── backend/           FastAPI — app/{api,agents,core,db,schemas,services,workers}, tests/
├── docs/              Architecture, schema, agent roster, API contract
├── deployment/        Compose files, Dockerfiles, reverse proxy, .env.example
├── scripts/           dev-setup, verify
└── .github/workflows/ CI pipeline
```

## Security notes

- JWT access and refresh tokens, bcrypt password hashing, Redis-backed revocation.
- Project-scoped authorisation resolved as a dependency before any handler body runs;
  unauthorised access returns 404.
- Uniform error envelope: stable codes and safe messages outward, detail to logs only.
- Structured JSON logs correlated by `request_id`; passwords, tokens, keys, and full
  document text are never logged.
- **Known advisory:** the pinned Next.js 14 line has open high-severity advisories
  with no patched 14.x release. The framework major is fixed by the architecture, so
  CI fails on critical findings and reports the remainder rather than suppressing
  them. Resolving them requires a framework major upgrade.

## Licence

MIT.
