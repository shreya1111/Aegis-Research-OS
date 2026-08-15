# Aegis Research OS — Plan Analysis & Improvements

## 1. Overall Assessment

The original roadmap is impressively broad and reads like a legitimate startup spec — which is exactly the problem for a **single-student B.Tech major project**. As written, it is roughly a 3–5 engineer, 6-month effort compressed into "12–14 weeks if you work consistently." Left unchanged, this plan has a high risk of ending in a half-finished, unpolished product — which scores worse in evaluation than a smaller, fully working, well-demoed system.

The improvements below keep the ambition (it's a great portfolio idea) but make it **shippable by one person**, add the pieces the original plan is missing, and turn it into an execution-ready prompt pack.

## 2. Key Gaps in the Original Plan

| Gap | Why it matters | Fix |
|---|---|---|
| No MVP / cut-line defined | 15 agents + knowledge graph + enterprise features is not an MVP, it's a v3.0 | Defined a strict MVP (Phases 0–6) and marked 7–10 as "stretch" |
| No evaluation plan | Academic evaluators grade correctness, not vibes | Added a Testing & Evaluation phase with rubrics, test data, demo script |
| No cost/quota plan for LLM calls | 15 agents calling LLMs per query will blow through API budgets fast | Added an LLM cost-control section (caching, model tiering, token budgets) |
| Vague "15 agents" | Many of these overlap (Fact Checker/Critic/Reviewer are near-duplicates) | Consolidated to 7 core agents for MVP, rest are optional add-ons |
| No data source strategy | "Academic Search agent" needs actual APIs (arXiv, Semantic Scholar, CORE, PubMed) | Named concrete free APIs per agent |
| No security/privacy pass | User uploads + multi-tenant + API keys need basic hardening | Added to Phase 11 |
| Neo4j + ChromaDB + Redis + Postgres + Celery all at once | 5 infra services for a solo dev to manage is high operational overhead | Recommended Postgres+pgvector to replace ChromaDB, and deferring Neo4j to stretch phase |
| No explicit LLM abstraction spec | "Create an abstraction layer" is mentioned but never defined | Added a concrete interface spec in the master prompt |
| Report/thesis alignment missing | A major project needs a report, not just code | Added a "Documentation & Report" deliverable list per phase |

## 3. Structural Improvements

### 3.1 MVP-first, stretch-second
- **Core (must-ship):** Phases 0–6 → Auth, document upload, hybrid RAG, 7-agent research pipeline, literature review generation, report export.
- **Stretch (only if time remains):** Phases 7–10 → Knowledge graph, dataset analytics, enterprise multi-tenant features.
- **Always-on:** Testing, docs, deployment — done incrementally, not saved for the end.

### 3.2 Infra simplification
- Replace **ChromaDB** with **pgvector inside PostgreSQL** — one database instead of two, still supports hybrid semantic + metadata search.
- Replace **Celery** with **FastAPI BackgroundTasks / arq** for the MVP — introduce Celery only if you reach the stretch phases and need real task queues.
- Defer **Neo4j** to the stretch phase; model the graph relationally until then.
- Keep **Redis** — cheap, useful for caching + rate limiting.

Net effect: MVP infra = PostgreSQL (with pgvector) + Redis + FastAPI + Next.js. Four moving parts instead of eight.

### 3.3 Agent consolidation (15 → 7 core + 4 optional)
**Core agents (MVP):**
1. Supervisor/Planner (merged — one orchestrator agent)
2. Retrieval Agent (merges Academic Search + Web Search + Reader)
3. Summarizer Agent
4. Fact-Checker/Citation Agent (merged)
5. Synthesis/Report-Writer Agent
6. Memory Agent (session + long-term context store)
7. Critic/Reviewer Agent (merged — final quality pass)

**Optional (stretch):**
8. Dataset/Code Search Agent
9. Debate Agent
10. Trend/Gap-Analysis Agent
11. Hypothesis-Generation Agent

### 3.4 Concrete data sources per agent
- Academic search → **arXiv API**, **Semantic Scholar API**, **CORE API**, **CrossRef API** (all free, no key or free-tier key)
- Web search → **Tavily API** or **SerpAPI** free tier (or Bing Search API)
- Datasets → **Kaggle API**, **Hugging Face Datasets API**

### 3.5 LLM cost & reliability controls
- Tiered model routing: cheap/fast model for retrieval-ranking and summarization, stronger model only for final synthesis/report writing.
- Response caching (Redis) keyed by query+doc hash to avoid recomputation.
- Token budgets per agent call, enforced in code, logged for the report's "cost analysis" section.
- Streaming responses to the frontend so long agent chains feel responsive.

### 3.6 Evaluation & demo readiness
- Build a small **gold-standard test set**: 5–10 research questions with known good answers/sources, used to demo hybrid RAG accuracy and agent quality in your viva/defense.
- Keep a **agent trace log** (which agent did what, in order) visible in the UI — great for both debugging and demoing "multi-agent" behavior to evaluators.
- Track and report: retrieval precision\@k, citation accuracy, latency per query, cost per query.

### 3.7 Revised, realistic timeline (solo developer)

| Phase | Original | Revised | Notes |
|---|---|---|---|
| 0 – Planning | 1 wk | 1 wk | unchanged, non-negotiable |
| 1 – Foundation | 2 wks (shared) | 1.5 wks | simplified infra saves time |
| 2 – UI/UX | (shared) | 1 wk | build alongside, not a separate block |
| 3 – Document Intelligence | 3 wks (shared) | 1.5 wks | |
| 4 – Hybrid RAG | (shared) | 1.5 wks | |
| 5 – Multi-Agent System | 4 wks (shared) | 2.5 wks | 7 agents, not 15 |
| 6 – Research Intelligence | (shared) | 1.5 wks | literature review + survey generation only |
| **MVP checkpoint** | — | **~10.5 weeks** | fully working, demoable product |
| 7 – Knowledge Graph (stretch) | 2 wks | 1.5 wks | optional |
| 8 – Analytics (stretch) | (shared) | 1 wk | optional |
| 9 – Reports polish | 2 wks (shared) | 1 wk | multi-format export |
| 10 – Enterprise (stretch) | (shared) | 1 wk | optional, only if time remains |
| 11 – Testing/Deploy | 2 wks | 1.5 wks, done incrementally | |

**Realistic total for a strong MVP: ~10–11 weeks. Full stretch scope: ~16 weeks.**

## 4. What This Deliverable Contains

1. `01_analysis_and_improvements.md` — this file
2. `02_master_prompt.md` — the single prompt to hand to an AI coding agent (e.g., Claude Code) to bootstrap and drive the whole build
3. `03_phase_prompts.md` — a ready-to-use, copy-pasteable prompt for every phase (0–11), each scoped to be run independently
4. `04_architecture_and_specs.md` — system architecture, DB schema starting point, API contract conventions, and the LLM provider abstraction interface
5. `05_project_report_outline.md` — a B.Tech major-project report/thesis outline mapped to your phases, so documentation isn't an afterthought
