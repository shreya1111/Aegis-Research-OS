# Graph Report - Aegis-Research-OS  (2026-10-30)

## Corpus Check
- 290 files · ~113,580 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 4, .conf 2, .ini 1)

## Summary
- 2858 nodes · 7710 edges · 140 communities (100 shown, 40 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 970 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Entity Extraction & Graph Edges
- LLM Response Cache
- Schema Migrations & Models
- Knowledge Graph Models
- LangGraph Agent Graph
- Project Repository & Scoping
- LLM Circuit Breaker
- Frontend Route Shell
- Auth Pages
- Analytics API
- Knowledge Graph API
- Agent Node Implementations
- Report Model
- Frontend Auth API Client
- Chat Panel & Citations
- Conversation & Message Store
- Graph Visualization UI
- JWT Security & Token Minting
- Typed Settings Config
- Chunk Repository
- Auth Service
- Workspace Shell & Auth Guard
- Auth Endpoints & Rate Limiting
- Redis Cache & Rate Limiter
- PDF Parsing & Ingestion Errors
- Graph API Integration Tests
- Document Repository
- Ingestion Pipeline
- Dashboard & Project Layout
- Production Compose Stack
- Reports API
- Metadata Extraction
- Embedding Service
- Agent Runtime State & Deps
- HTTP Middleware & Correlation
- Token-Aware Chunking
- Citation Map Handling
- Agent Graph Compilation
- Query Endpoint
- External Academic Sources
- Documents API Integration Tests
- Root Layout & Toaster
- TypeScript Config
- Analytics Repository
- Documents API
- Export Service
- Backend Environment Wiring
- Initial Schema Migrations
- Projects API
- Agent Run Status Cache
- Frontend Dependencies
- Development Compose Stack
- Error Hierarchy
- User Repository & Uniqueness
- Auth API Integration Tests
- Envelope & Common Schemas
- Projects API Integration Tests
- Structured JSON Logging
- Document & Chunk Models
- DOCX Parsing
- Reports
- Package
- Memory service
- Exception handlers
- Test query api
- Test envelope
- Agent service mock
- Conftest
- Agents
- Test query routing
- Analytics
- Deps
- Deps (2)
- Health
- Trace
- Test ingestion validation
- Format
- Package (2)
- Deps (3)
- Test fusion
- Analytics service
- Docker compose
- .eslintrc
- Design
- Api contract
- Crossref
- Test app
- Package (3)
- Ci
- Ci (2)
- 03 phase prompts
- Env
- Export service
- .prettierrc
- Ci (3)
- Test ingestion validation (2)
- Docker compose (2)
- Docker compose (3)
- Ci (4)
- Docker compose (4)
- Logging
- Cache
- Docker compose (5)
- Docker compose (6)
- Package (4)
- Ci (5)
- Docker compose (7)
- Deps (4)
- Package (5)
- Ci (6)
- Dev setup
- ComingSoon
- Next.config
- Postcss.config
- Ci (7)
- Docker entrypoint
- Package (6)
- Package (7)
- Package (8)
- Pyproject.toml

## God Nodes (most connected - your core abstractions)
1. `Settings` - 62 edges
2. `cn()` - 53 edges
3. `Message` - 51 edges
4. `ApiResponse` - 51 edges
5. `ok()` - 50 edges
6. `NodeType` - 49 edges
7. `Project` - 46 edges
8. `Button` - 45 edges
9. `GraphService` - 43 edges
10. `Report` - 42 edges

## Surprising Connections (you probably didn't know these)
- `B.Tech Report Outline` --references--> `Architecture at a Glance`  [INFERRED]
  05_project_report_outline.md → docs/architecture.md
- `LangGraph Agent Orchestration` --conceptually_related_to--> `Agent Roster`  [INFERRED]
  design.md → docs/agents.md
- `Project as Tenancy Boundary` --conceptually_related_to--> `Project Scoping Returns 404`  [INFERRED]
  design.md → docs/api-contract.md
- `Agent Roster` --references--> `design.md — System Design Document`  [EXTRACTED]
  docs/agents.md → design.md
- `API Contract` --references--> `design.md — System Design Document`  [EXTRACTED]
  docs/api-contract.md → design.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **The Seven Core Agents** — docs_agents_supervisor, docs_agents_retrieval, docs_agents_summarizer, docs_agents_fact_checker, docs_agents_synthesis, docs_agents_memory, docs_agents_critic [EXTRACTED 1.00]
- **Citation Integrity Chain** — design_citation_validation_gate, backend_app_services_retrieval_citation, docs_agents_fact_checker, design_grounded_never_guessed [INFERRED 0.85]

## Communities (140 total, 40 thin omitted)

### Community 0 - "Entity Extraction & Graph Edges"
Cohesion: 0.05
Nodes (22): EdgeType, EntityExtractionResult, EntityExtractionService, ExtractedEntity, ExtractedRelationship, GraphService, test_deduplicate_entities(), test_extract_authors_from_metadata() (+14 more)

### Community 1 - "LLM Response Cache"
Cohesion: 0.07
Nodes (20): get_llm_provider_dep(), build_cache_key(), LLMResponseCache, CachingLLMProvider, LLMProvider, LLMResponse, Message, _build_provider() (+12 more)

### Community 2 - "Schema Migrations & Models"
Cohesion: 0.10
Nodes (12): Core DB Schema Starter, upgrade(), AgentTrace, AnalyticsAnalysis, AnalyticsDataset, Base, CreatedAtMixin, UUIDPrimaryKeyMixin (+4 more)

### Community 3 - "Knowledge Graph Models"
Cohesion: 0.08
Nodes (13): GraphEdge, GraphNode, NodeType, GraphRepository, test_create_edge(), test_create_node(), test_delete_node(), test_delete_nonexistent_node() (+5 more)

### Community 4 - "LangGraph Agent Graph"
Cohesion: 0.08
Nodes (29): _best_effort_answer(), build_agent_graph(), _continue_or_end(), _guarded(), wrapped(), _route_from_critic(), _route_from_supervisor(), _run_critic() (+21 more)

### Community 5 - "Project Repository & Scoping"
Cohesion: 0.08
Nodes (18): get_project_service(), NotFoundError, ProjectRepository, ProjectService, FakeProjectRepository, repository(), service(), test_create_project_stores_the_owner() (+10 more)

### Community 6 - "LLM Circuit Breaker"
Cohesion: 0.09
Nodes (13): LLMProviderError, CircuitBreaker, _State, FatalProviderError, TransientProviderError, GeminiProvider, HttpChatCompletionsProvider, ToolCall (+5 more)

### Community 7 - "Frontend Route Shell"
Cohesion: 0.07
Nodes (34): dynamic, HomePage(), loadHealth(), hasInFlightDocuments(), LoadState, ProjectDocumentsPage(), ACCEPTED_ATTRIBUTE, ACCEPTED_EXTENSIONS (+26 more)

### Community 8 - "Auth Pages"
Cohesion: 0.12
Nodes (35): LoginPage(), metadata, metadata, RegisterPage(), metadata, ProjectReportsPage(), LoginForm(), handleSubmit() (+27 more)

### Community 9 - "Analytics API"
Cohesion: 0.07
Nodes (15): analyze_dataset(), delete_dataset(), get_analysis(), get_analytics_repo(), get_analytics_service(), get_dataset(), get_storage_dir(), list_analyses() (+7 more)

### Community 10 - "Knowledge Graph API"
Cohesion: 0.07
Nodes (17): create_relationship(), delete_node(), delete_relationship(), get_graph_data(), _get_graph_service(), get_graph_statistics(), get_node_details(), rebuild_graph() (+9 more)

### Community 11 - "Agent Node Implementations"
Cohesion: 0.08
Nodes (17): _parse_subtasks(), retrieval_node(), retrieve_external(), retrieve_internal(), Subtask, CrossrefLookupInput, external_search(), ExternalSearchInput (+9 more)

### Community 12 - "Report Model"
Cohesion: 0.08
Nodes (5): Report, ReportStatus, ReportType, ReportRepository, ReportService

### Community 13 - "Frontend Auth API Client"
Cohesion: 0.09
Nodes (30): fetchCurrentUser(), login(), LoginPayload, logout(), refreshAccessToken(), register(), RegisterPayload, AuthContext (+22 more)

### Community 14 - "Chat Panel & Citations"
Cohesion: 0.08
Nodes (34): metadata, ProjectChatPage(), ChatPanel(), ChatTurn, CitationChip(), CitationChipProps, StreamingMessage(), StreamingMessageProps (+26 more)

### Community 15 - "Conversation & Message Store"
Cohesion: 0.08
Nodes (6): Conversation, MessageRole, ConversationRepository, MessageRepository, AgentService, RagService

### Community 16 - "Graph Visualization UI"
Cohesion: 0.13
Nodes (34): ProjectGraphPage(), CustomEdge(), applyLayoutAlgorithm(), edgeTypes, GraphVisualizationProps, nodeTypes, NodeDetailsSidebarProps, AuthorNode() (+26 more)

### Community 17 - "JWT Security & Token Minting"
Cohesion: 0.13
Nodes (22): AuthenticationError, create_access_token(), create_refresh_token(), decode_token(), _encode(), hash_password(), TokenPayload, TokenType (+14 more)

### Community 18 - "Typed Settings Config"
Cohesion: 0.08
Nodes (15): get_settings(), Settings, _split_csv(), get_db_session(), get_engine(), get_session_factory(), reset_engine_cache(), test_cors_origins_accepts_comma_separated_string() (+7 more)

### Community 19 - "Chunk Repository"
Cohesion: 0.09
Nodes (6): DocumentChunkRepository, DocumentRepository, new_db_session(), IngestionPipeline, run_ingestion(), Chunk

### Community 20 - "Auth Service"
Cohesion: 0.15
Nodes (19): AuthService, FakeUserRepository, redis(), repository(), service(), settings(), test_authenticate_rejects_unknown_email_with_the_same_error(), test_authenticate_rejects_wrong_password() (+11 more)

### Community 21 - "Workspace Shell & Auth Guard"
Cohesion: 0.17
Nodes (28): WorkspaceLayout(), ProjectSettingsPage(), handleDelete(), AuthGuard(), DeleteDocumentDialog(), DeleteDocumentDialogProps, ThemeToggle(), TopBar() (+20 more)

### Community 22 - "Auth Endpoints & Rate Limiting"
Cohesion: 0.11
Nodes (14): _client_identifier(), _enforce_rate_limit(), login(), logout(), me(), refresh(), register(), RateLimitError (+6 more)

### Community 23 - "Redis Cache & Rate Limiter"
Cohesion: 0.12
Nodes (15): get_rate_limiter(), get_redis_client(), get_token_denylist(), RateLimiter, reset_redis_client_cache(), TokenDenylist, redis(), test_denylist_check_fails_open_when_redis_is_unavailable() (+7 more)

### Community 24 - "PDF Parsing & Ingestion Errors"
Cohesion: 0.12
Nodes (7): ExtractionError, _extract_pdf_metadata(), _ocr_page(), parse_pdf(), _digital_pdf_bytes(), _scanned_pdf_bytes(), TestParsePdf

### Community 25 - "Graph API Integration Tests"
Cohesion: 0.10
Nodes (15): test_create_relationship_validation(), test_cross_project_access(), test_delete_nonexistent_node(), test_delete_nonexistent_relationship(), test_get_graph_data_empty(), test_get_graph_stats_empty(), test_get_nonexistent_node_details(), test_graph_data_with_filters() (+7 more)

### Community 26 - "Document Repository"
Cohesion: 0.11
Nodes (3): Document, DocumentService, Layering: api → services → repositories → core

### Community 27 - "Ingestion Pipeline"
Cohesion: 0.16
Nodes (7): _digital_pdf_bytes(), FakeChunkRepository, FakeDocumentRepository, FakeEmbeddingService, _make_document(), settings(), TestIngestionPipeline

### Community 28 - "Dashboard & Project Layout"
Cohesion: 0.10
Nodes (22): DashboardPage(), LoadState, ProjectLayout(), EmptyState(), EmptyStateProps, Skeleton(), PROJECT_NAV_ITEMS, projectNavHref() (+14 more)

### Community 29 - "Production Compose Stack"
Cohesion: 0.06
Nodes (32): command, condition, environment, expose, restart, backend, frontend, API_INTERNAL_URL (+24 more)

### Community 30 - "Reports API"
Cohesion: 0.13
Nodes (9): create_report(), delete_report(), export_report(), generate_summary(), get_report(), _get_report_service(), list_reports(), ReportCreate (+1 more)

### Community 31 - "Metadata Extraction"
Cohesion: 0.14
Nodes (6): build_failure_metadata(), build_metadata(), ExtractedDocument, ExtractedPage, TestBuildFailureMetadata, TestBuildMetadata

### Community 32 - "Embedding Service"
Cohesion: 0.12
Nodes (6): _cached_embedding_service(), EmbeddingService, get_embedding_service(), embedding_service(), test_get_embedding_service_is_cached_by_model_and_batch_size(), TestEmbeddingService

### Community 33 - "Agent Runtime State & Deps"
Cohesion: 0.11
Nodes (5): AgentDeps, AgentTraceRepository, get_compiled_agent_graph(), LangGraph Agent Orchestration, Bounded Critic Retry (max 1)

### Community 34 - "HTTP Middleware & Correlation"
Cohesion: 0.10
Nodes (4): RequestContextMiddleware, SecurityHeadersMiddleware, _build_lifespan(), create_app()

### Community 35 - "Token-Aware Chunking"
Cohesion: 0.14
Nodes (7): chunk_document(), _count_tokens(), _flatten_to_words(), _tokenizer(), _Word, _document(), TestChunkDocument

### Community 36 - "Citation Map Handling"
Cohesion: 0.16
Nodes (15): build_citation_map(), extract_markers(), to_message_citations(), validate_citations(), CitationMap, CitationMapEntry, _chunk(), _external_source() (+7 more)

### Community 37 - "Agent Graph Compilation"
Cohesion: 0.15
Nodes (15): compile_agent_graph(), _base_deps(), _happy_path_complete(), complete(), _initial_state(), _make_chunk(), test_a_failed_node_degrades_the_run_instead_of_raising(), test_a_multi_subtask_request_dispatches_retrieval_per_subtask() (+7 more)

### Community 38 - "Query Endpoint"
Cohesion: 0.12
Nodes (7): run_query(), QueryFilters, QueryRequest, QueryResponse, SourceRead, AgentRunResult, RagAnswer

### Community 39 - "External Academic Sources"
Cohesion: 0.14
Nodes (6): search_arxiv(), ExternalSourceCache, search_core(), ExternalSourceService, search_semantic_scholar(), ExternalSource

### Community 40 - "Documents API Integration Tests"
Cohesion: 0.26
Nodes (9): _auth_headers(), _create_project(), _docx_bytes(), _pdf_bytes(), _register_and_login(), TestDeleteDocument, TestGetDocument, TestListDocuments (+1 more)

### Community 41 - "Root Layout & Toaster"
Cohesion: 0.13
Nodes (21): metadata, RootLayout(), viewport, Toaster(), VARIANT_STYLES, applyThemeClass(), readInitialTheme(), Theme (+13 more)

### Community 42 - "TypeScript Config"
Cohesion: 0.07
Nodes (26): compilerOptions, allowJs, baseUrl, esModuleInterop, forceConsistentCasingInFileNames, incremental, isolatedModules, jsx (+18 more)

### Community 44 - "Documents API"
Cohesion: 0.14
Nodes (7): delete_document(), get_document(), list_documents(), upload_document(), ApiResponse, DocumentMetadata, DocumentRead

### Community 46 - "Backend Environment Wiring"
Cohesion: 0.08
Nodes (25): environment, AGENT_MAX_RETRIES, AGENT_MAX_SUBTASKS, CORE_API_KEY, CORS_ORIGINS, EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, ENVIRONMENT (+17 more)

### Community 47 - "Initial Schema Migrations"
Cohesion: 0.09
Nodes (7): upgrade(), upgrade(), upgrade(), upgrade(), upgrade(), upgrade(), upgrade()

### Community 48 - "Projects API"
Cohesion: 0.14
Nodes (8): create_project(), delete_project(), get_project(), list_projects(), ok(), paginated(), ProjectCreate, ProjectRead

### Community 49 - "Agent Run Status Cache"
Cohesion: 0.18
Nodes (8): AgentRunStatusCache, redis(), test_a_later_status_overwrites_an_earlier_one(), test_get_status_fails_open_when_redis_is_unavailable(), test_get_status_returns_none_before_any_write(), test_set_and_get_status_round_trips(), test_set_status_carries_a_detail_message(), test_set_status_fails_open_when_redis_is_unavailable()

### Community 50 - "Frontend Dependencies"
Cohesion: 0.08
Nodes (24): dependencies, class-variance-authority@0.7.1, clsx@2.1.1, lucide-react@^1.37.0, next@14.2.35, @radix-ui/react-dialog@1.1.23, @radix-ui/react-label@2.1.15, @radix-ui/react-radio-group@^1.4.7 (+16 more)

### Community 51 - "Development Compose Stack"
Cohesion: 0.09
Nodes (22): command, environment, ports, volumes, target, API_INTERNAL_URL, ENVIRONMENT, LOG_LEVEL (+14 more)

### Community 52 - "Error Hierarchy"
Cohesion: 0.13
Nodes (5): AppError, FileTooLargeError, PermissionDeniedError, UnsupportedFileTypeError, ValidationError

### Community 53 - "User Repository & Uniqueness"
Cohesion: 0.13
Nodes (3): ConflictError, User, UserRepository

### Community 54 - "Auth API Integration Tests"
Cohesion: 0.23
Nodes (16): _login(), _register(), test_every_response_carries_a_request_id(), test_login_rejects_wrong_password(), test_login_returns_an_access_and_refresh_token(), test_login_with_unknown_email_matches_the_wrong_password_response(), test_logout_revokes_the_access_token(), test_me_returns_the_authenticated_profile() (+8 more)

### Community 55 - "Envelope & Common Schemas"
Cohesion: 0.13
Nodes (9): Architecture & Specs, API Contract Conventions, LLM Interface Spec, ErrorDetail, HealthStatus, Page, PaginationParams, Uniform Response Envelope (+1 more)

### Community 56 - "Projects API Integration Tests"
Cohesion: 0.32
Nodes (15): _auth_headers(), _register_and_login(), test_create_project_allows_an_omitted_description(), test_create_project_rejects_an_empty_title(), test_create_project_requires_authentication(), test_create_project_returns_the_created_workspace(), test_delete_project_by_another_owner_returns_404_and_does_not_delete(), test_delete_project_removes_it_for_the_owner() (+7 more)

### Community 57 - "Structured JSON Logging"
Cohesion: 0.18
Nodes (7): configure_logging(), JsonFormatter, _record(), test_formatter_emits_single_line_json(), test_formatter_includes_correlation_ids_when_set(), test_formatter_includes_extra_fields(), test_formatter_omits_correlation_ids_when_unset()

### Community 58 - "Document & Chunk Models"
Cohesion: 0.25
Nodes (12): DocumentChunk, DocumentStatus, _build_pipeline(), _create_pending_document(), _docx_bytes(), _multi_page_pdf_bytes(), _seed_project(), test_corrupt_pdf_marks_document_failed() (+4 more)

### Community 59 - "DOCX Parsing"
Cohesion: 0.18
Nodes (5): _is_heading(), parse_docx(), flush(), _build_docx(), TestParseDocx

### Community 60 - "Reports"
Cohesion: 0.18
Nodes (12): formatReportType(), getStatusIcon(), getStatusVariant(), ReportList(), ReportListProps, Skeleton(), ExportFormat, exportReport() (+4 more)

### Community 61 - "Package"
Cohesion: 0.10
Nodes (20): devDependencies, autoprefixer@10.4.20, eslint@8.57.1, jsdom@25.0.1, postcss@8.5.25, prettier-plugin-tailwindcss@0.6.9, @testing-library/dom@10.4.0, @testing-library/react@16.1.0 (+12 more)

### Community 62 - "Memory service"
Cohesion: 0.14
Nodes (4): ProjectMemoryRepository, MemoryService, Three Memory Horizons, Memory Agent

### Community 63 - "Exception handlers"
Cohesion: 0.20
Nodes (5): handle_app_error(), handle_http_exception(), handle_unexpected_error(), handle_validation_error(), register_exception_handlers()

### Community 64 - "Test query api"
Cohesion: 0.30
Nodes (10): _auth_headers(), _create_project(), _override_llm_provider(), _register_and_login(), test_a_multi_part_research_question_is_routed_to_the_agent_graph(), test_a_simple_question_is_answered_via_the_rag_pipeline(), test_agent_run_trace_is_retrievable_after_the_query_completes(), test_query_for_another_users_project_returns_404() (+2 more)

### Community 65 - "Test envelope"
Cohesion: 0.23
Nodes (8): fail(), fail_from(), ErrorCode, test_domain_error_accepts_custom_message_and_private_context(), test_fail_from_uses_exception_code_and_status(), test_fail_produces_error_envelope_with_null_data(), test_ok_wraps_payload_with_no_error(), test_paginated_exposes_items_and_total()

### Community 67 - "Conftest"
Cohesion: 0.18
Nodes (4): app(), client(), db_engine(), settings()

### Community 68 - "Agents"
Cohesion: 0.14
Nodes (11): Plan Analysis & Improvements, fast / strong Model Tier Policy, Agent Tool Registry, Agent Roster, Critic / Reviewer Agent, Fact-Checker / Citation Agent, Retrieval Agent, Summarizer Agent (+3 more)

### Community 69 - "Test query routing"
Cohesion: 0.23
Nodes (7): requires_agent_pipeline(), test_a_comparison_request_routes_to_the_agent_graph(), test_a_long_request_routes_to_the_agent_graph_even_without_a_keyword(), test_a_request_with_multiple_question_marks_routes_to_the_agent_graph(), test_a_simple_factual_question_stays_on_the_fast_path(), test_an_empty_question_stays_on_the_fast_path(), test_research_keywords_route_to_the_agent_graph()

### Community 70 - "Analytics"
Cohesion: 0.24
Nodes (12): hasInFlightDatasets(), LoadState, ProjectAnalyticsPage(), analyzeDataset(), deleteDataset(), getDataset(), listAnalyses(), listDatasets() (+4 more)

### Community 71 - "Deps"
Cohesion: 0.20
Nodes (9): get_agent_trace_repository(), get_bearer_token(), get_conversation_repository(), get_document_chunk_repository(), get_document_repository(), get_message_repository(), get_project_memory_repository(), get_project_repository() (+1 more)

### Community 72 - "Deps (2)"
Cohesion: 0.13
Nodes (7): get_agent_run_status_cache(), get_auth_service(), get_document_service(), get_embedding_service_dep(), get_external_source_cache(), get_external_source_service(), get_retrieval_service()

### Community 74 - "Trace"
Cohesion: 0.20
Nodes (3): get_trace(), TraceRunRead, TraceStepRead

### Community 76 - "Format"
Cohesion: 0.24
Nodes (11): DocumentRow(), DocumentRowProps, MetadataField(), DocumentStatusBadge(), STATUS_STYLES, formatBytes(), formatDate(), formatDistanceToNow() (+3 more)

### Community 77 - "Package (2)"
Cohesion: 0.13
Nodes (14): description, eslint-config-next@14.2.35, @types/react@18.3.14, typescript@5.7.2, engines, node, name, overrides (+6 more)

### Community 78 - "Deps (3)"
Cohesion: 0.19
Nodes (4): get_agent_deps(), get_agent_service(), get_memory_service(), get_rag_service()

### Community 79 - "Test fusion"
Cohesion: 0.30
Nodes (7): fuse_rankings(), _chunk(), test_a_chunk_found_by_both_paths_outranks_one_found_by_only_one(), test_empty_inputs_produce_an_empty_result(), test_fused_rank_is_contiguous_starting_at_one(), test_fusion_respects_top_n(), test_semantic_and_keyword_only_chunks_both_carry_their_source_rank()

### Community 81 - "Docker compose"
Cohesion: 0.17
Nodes (11): name, volumes, model-cache, postgres-data, redis-data, Risks & Mitigations, System Context (4 moving parts), README.md — Aegis Research OS (+3 more)

### Community 82 - ".eslintrc"
Cohesion: 0.17
Nodes (11): extends, ignorePatterns, eslint-config-prettier, overrides, root, rules, eqeqeq, no-console (+3 more)

### Community 83 - "Design"
Cohesion: 0.22
Nodes (9): Master Prompt, design.md — System Design Document, Layering & Import Rules, LLM Circuit Breaker & Failover, Citation Validation Gate, Context Budgeting & Assembly, In-Process Embedding System, Hybrid RAG Pipeline (+1 more)

### Community 84 - "Api contract"
Cohesion: 0.18
Nodes (9): B.Tech Report Outline, API Contract, Closed Error-Code Enum, Rate Limit Matrix, Project Scoping Returns 404, SSE Trace Stream Endpoint, Architecture at a Glance, Database Schema (+1 more)

### Community 85 - "Crossref"
Cohesion: 0.27
Nodes (5): crossref_lookup(), _as_str_or_none(), lookup_by_doi(), _parse_work(), search_crossref()

### Community 86 - "Test app"
Cohesion: 0.38
Nodes (7): test_docs_are_disabled_in_production(), test_docs_are_served_outside_production(), test_health_returns_success_envelope(), test_inbound_request_id_is_preserved(), test_response_carries_request_id_header(), test_security_headers_are_applied(), test_unknown_route_returns_error_envelope()

### Community 87 - "Package (3)"
Cohesion: 0.18
Nodes (11): scripts, build, dev, format, format:check, lint, lint:fix, start (+3 more)

### Community 89 - "Ci"
Cohesion: 0.20
Nodes (10): defaults, name, runs-on, run, defaults, name, runs-on, backend (+2 more)

### Community 90 - "Ci (2)"
Cohesion: 0.20
Nodes (10): with, cache, cache-dependency-path, cache-from, cache-to, context, file, node-version (+2 more)

### Community 91 - "03 phase prompts"
Cohesion: 0.25
Nodes (8): Phase Prompts, Phase 11 — Testing, Security & Deployment, Phase 5 — Multi-Agent System, Phase 7 — Knowledge Graph (Stretch), Phase 9 — Report Generation & Export, Quality Gate Pipeline, gate(), verify.sh script

### Community 92 - "Env"
Cohesion: 0.28
Nodes (3): run_migrations_offline(), run_migrations_online(), _sync_database_url()

### Community 95 - ".prettierrc"
Cohesion: 0.22
Nodes (8): arrowParens, endOfLine, plugins, printWidth, semi, singleQuote, tabWidth, trailingComma

### Community 96 - "Ci (3)"
Cohesion: 0.22
Nodes (8): concurrency, cancel-in-progress, group, env, NODE_VERSION, PYTHON_VERSION, jobs, name

### Community 98 - "Docker compose (2)"
Cohesion: 0.25
Nodes (8): depends_on, restart, volumes, postgres, redis, condition, condition, backend

### Community 99 - "Docker compose (3)"
Cohesion: 0.25
Nodes (8): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, environment, image, restart, volumes, postgres

### Community 100 - "Ci (4)"
Cohesion: 0.43
Nodes (8): steps, steps, steps, steps, name, run, uses, working-directory

### Community 102 - "Docker compose (4)"
Cohesion: 0.43
Nodes (7): interval, retries, start_period, test, timeout, healthcheck, healthcheck

### Community 105 - "Docker compose (5)"
Cohesion: 0.40
Nodes (6): NEXT_PUBLIC_API_URL, build, args, context, dockerfile, build

### Community 106 - "Docker compose (6)"
Cohesion: 0.33
Nodes (6): condition, backend, depends_on, restart, services, frontend

### Community 107 - "Package (4)"
Cohesion: 0.33
Nodes (5): tailwindcss@3.4.16, tailwindcss-animate@1.0.7, config, tailwindcss, tailwindcss-animate

### Community 108 - "Ci (5)"
Cohesion: 0.33
Nodes (6): on, pull_request, push, branches, branches, tags

### Community 109 - "Docker compose (7)"
Cohesion: 0.40
Nodes (5): command, image, restart, volumes, redis

### Community 112 - "Ci (6)"
Cohesion: 0.50
Nodes (4): name, needs, runs-on, images

### Community 113 - "Dev setup"
Cohesion: 0.83
Nodes (3): note(), dev-setup.sh script, step()

### Community 118 - "Ci (7)"
Cohesion: 0.67
Nodes (3): name, runs-on, audit

## Knowledge Gaps
- **5 isolated node(s):** `aegis-research-os-backend`, `next/core-web-vitals`, `eslint-config-prettier`, `Master Prompt`, `B.Tech Report Outline`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1074 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **40 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Hybrid RAG Pipeline` connect `Design` to `Agent Node Implementations`, `Chat Panel & Citations`, `Test fusion`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Are the 35 inferred relationships involving `Settings` (e.g. with `_build_provider()` and `get_llm_provider()`) actually correct?**
  _`Settings` has 35 INFERRED edges - model-reasoned connections that need verification._
- **What connects `aegis-research-os-backend`, `next/core-web-vitals`, `eslint-config-prettier` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Entity Extraction & Graph Edges` be split into smaller, more focused modules?**
  _Cohesion score 0.048539518900343644 - nodes in this community are weakly interconnected._
- **Why does `Uniform Response Envelope` connect `Envelope & Common Schemas` to `Design`, `Frontend Route Shell`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `Message` (e.g. with `build_cache_key()` and `CachingLLMProvider`) actually correct?**
  _`Message` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Should `LLM Response Cache` be split into smaller, more focused modules?**
  _Cohesion score 0.07093253968253968 - nodes in this community are weakly interconnected._