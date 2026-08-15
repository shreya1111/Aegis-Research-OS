"""Typed application settings.

This module is the **only** place environment variables are read. Every other
module receives configuration through :func:`get_settings` so that configuration
is injectable and testable.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["development", "staging", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

#: Placeholder secret shipped only so local development works without an
#: explicit .env. Never a real credential; production startup rejects it.
_DEFAULT_JWT_SECRET = "insecure-development-secret-change-me"  # noqa: S105


def _split_csv(value: object) -> object:
    """Allow list-valued settings to be supplied as comma-separated strings.

    Environment variables are always strings, so ``CORS_ORIGINS`` arrives as
    ``"http://a,http://b"``. Lists are passed through untouched so that
    programmatic construction in tests keeps working.
    """
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


#: ``NoDecode`` opts this field out of pydantic-settings' default JSON decoding
#: for complex-typed environment variables, so ``_split_csv`` sees the raw
#: comma-separated string documented in ``.env.example`` rather than a value
#: pydantic-settings already failed to parse as JSON.
CsvList = Annotated[list[str], NoDecode, BeforeValidator(_split_csv)]


class Settings(BaseSettings):
    """Runtime configuration, validated once at process start."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # -- Application ------------------------------------------------------
    project_name: str = "Aegis Research OS"
    version: str = "0.1.0"
    environment: Environment = "development"
    log_level: LogLevel = "INFO"
    api_v1_prefix: str = "/api/v1"

    # -- HTTP -------------------------------------------------------------
    cors_origins: CsvList = Field(default_factory=lambda: ["http://localhost:3000"])

    # -- Infrastructure ---------------------------------------------------
    postgres_url: PostgresDsn = Field(
        default=PostgresDsn("postgresql+asyncpg://aegis:aegis@localhost:5432/aegis"),
    )
    redis_url: RedisDsn = Field(default=RedisDsn("redis://localhost:6379/0"))

    # -- Authentication (design §9.1, §9.2) --------------------------------
    #: Symmetric signing secret. Must be overridden outside development —
    #: enforced by validation below rather than left to operator discipline.
    jwt_secret: str = Field(default=_DEFAULT_JWT_SECRET, min_length=16)
    jwt_access_token_ttl_minutes: int = Field(default=15, gt=0)
    jwt_refresh_token_ttl_days: int = Field(default=30, gt=0)
    #: Minimum acceptable plaintext password length (design NFR, §9.1).
    password_min_length: int = Field(default=10, ge=8)

    # -- Rate limiting (design §9.6) ---------------------------------------
    rate_limit_login_per_minute: int = Field(default=5, gt=0)
    rate_limit_register_per_minute: int = Field(default=5, gt=0)
    #: The highest-value limit in the system (design §9.6): bounds LLM cost
    #: exhaustion on the query endpoint.
    rate_limit_query_per_minute: int = Field(default=20, gt=0)

    # -- Document ingestion (design §8.1, §9.5, Phase 3) -------------------
    #: Configurable per design §8.1 ("configurable maximum size (default: 100 MB)").
    max_upload_bytes: int = Field(default=100 * 1024 * 1024, gt=0)
    #: MIME types accepted by the upload allow-list (design §9.5, FR-C1).
    allowed_upload_mime_types: CsvList = Field(
        default_factory=lambda: [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]
    )
    #: Documents beyond this page count are rejected before processing begins
    #: (design §8.1: "Large documents (> 50 MB or > 100 pages)...").
    max_upload_pages: int = Field(default=500, gt=0)

    # -- Embeddings (design §4.3) -------------------------------------------
    #: Sentence-transformers model id. Stored per-chunk for drift detection —
    #: changing this invalidates all existing vectors (design §4.3).
    embedding_model: str = Field(default="all-MiniLM-L6-v2", min_length=1)
    #: Vector column dimensionality, fixed by ``embedding_model`` (design §4.3).
    #: Not derived at runtime so the pgvector column type is a static migration.
    embedding_dimensions: int = Field(default=384, gt=0)
    embedding_batch_size: int = Field(default=32, gt=0)

    # -- Chunking (design §8.3) ---------------------------------------------
    chunk_tokens: int = Field(default=700, gt=0)
    chunk_overlap_tokens: int = Field(default=100, ge=0)

    # -- OCR (design §8.2, "the OCR honesty rule") ---------------------------
    ocr_enabled: bool = Field(default=True)
    #: Below this mean per-word confidence (0-100, Tesseract's native scale),
    #: the document is flagged low-confidence rather than silently ingested.
    ocr_confidence_threshold: float = Field(default=60.0, ge=0.0, le=100.0)
    #: A page is treated as "scanned" (needs OCR) when its extractable text is
    #: shorter than this many characters (design §8.2 detection heuristic).
    ocr_trigger_char_threshold: int = Field(default=20, ge=0)

    # -- LLM provider layer (design §4.1) ------------------------------------
    #: Selects the concrete `LLMProvider` implementation. Switching providers
    #: never touches agent or business logic (design §4.1).
    llm_provider: Literal["openai", "gemini", "sambanova"] = Field(default="openai")
    llm_api_key: str = Field(default="")
    #: Real model name per tier, per provider. `fast` backs high-volume,
    #: low-judgement agents; `strong` backs planning/composition/review
    #: (design §4.1 tier policy table).
    llm_model_fast: str = Field(default="gpt-4o-mini")
    llm_model_strong: str = Field(default="gpt-4o")
    llm_base_url: str = Field(default="https://api.openai.com/v1")
    llm_request_timeout_seconds: float = Field(default=60.0, gt=0)
    llm_max_retries: int = Field(default=3, ge=0)
    #: Circuit breaker: consecutive failures before a provider is tripped
    #: open, and how long it stays open before a retry is allowed again
    #: (design §4.1 "circuit breaker pattern").
    llm_circuit_breaker_failure_threshold: int = Field(default=5, gt=0)
    llm_circuit_breaker_reset_seconds: float = Field(default=30.0, gt=0)
    #: Estimated cost per 1K tokens (USD), used only for the reportable cost
    #: metric in `agent_traces` — not billed anywhere.
    llm_cost_per_1k_input_tokens: float = Field(default=0.00015, ge=0)
    llm_cost_per_1k_output_tokens: float = Field(default=0.0006, ge=0)

    # -- Retrieval / hybrid search (design §4.2, §8.6, §8.7) -----------------
    retrieval_top_k: int = Field(default=40, gt=0)
    retrieval_top_n: int = Field(default=8, gt=0)
    #: RRF constant `k` in `score = Σ 1/(k + rank_i)` (design §8.6).
    retrieval_rrf_k: int = Field(default=60, gt=0)
    #: Cross-encoder re-ranking is the most expensive retrieval step
    #: (design §8.7); toggleable so its precision/latency trade-off is
    #: measurable.
    retrieval_rerank_enabled: bool = Field(default=False)
    retrieval_rerank_model: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    #: Citation validation retries at most this many times before the answer
    #: is accepted with a warning flag (design §4.2, the "3 attempts" cap).
    citation_max_regeneration_attempts: int = Field(default=3, ge=0)

    # -- External academic sources (design §4.6, §8.6) -----------------------
    #: Optional; a dead/unconfigured provider fails soft (empty result +
    #: trace warning), never fatal to the run (design §4.7 "fail soft").
    semantic_scholar_api_key: str = Field(default="")
    core_api_key: str = Field(default="")
    web_search_api_key: str = Field(default="")
    external_source_timeout_seconds: float = Field(default=15.0, gt=0)
    external_source_cache_ttl_seconds: int = Field(default=6 * 60 * 60, gt=0)
    external_source_max_results: int = Field(default=5, gt=0)

    # -- Agent orchestration (design §4.6) -----------------------------------
    #: The Critic's retry edges fire at most once per run (design §4.6 rule 2:
    #: "bounded loops... the cap lives in the state, not in a prompt").
    agent_max_retries: int = Field(default=1, ge=0)
    agent_run_status_ttl_seconds: int = Field(default=60 * 60, gt=0)
    #: Per-request cap on subtasks the Supervisor may create, bounding worst
    #: case cost for a single query.
    agent_max_subtasks: int = Field(default=6, gt=0)

    # -- LLM response cache (design §6.8) ------------------------------------
    llm_cache_ttl_seconds: int = Field(default=6 * 60 * 60, gt=0)

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalise_log_level(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value

    def model_post_init(self, __context: object) -> None:
        if self.is_production and self.jwt_secret == _DEFAULT_JWT_SECRET:
            raise ValueError("JWT_SECRET must be set to a non-default value in production.")
        if self.chunk_overlap_tokens >= self.chunk_tokens:
            raise ValueError("CHUNK_OVERLAP_TOKENS must be smaller than CHUNK_TOKENS.")

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def docs_enabled(self) -> bool:
        """Interactive API docs are never exposed in production (design §9.4)."""
        return not self.is_production


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton.

    Cached so that validation happens exactly once. Tests clear the cache via
    ``get_settings.cache_clear()`` when they need a different configuration.
    """
    return Settings()
