"""Tool registry (design §4.7).

Each tool is a typed async function with a Pydantic input schema. Agents call
these directly with validated arguments — the model never receives raw
provider JSON, and no tool executes on an unvalidated argument (design §4.7,
§9.5: "Tool arguments produced by the model are Pydantic-validated before
execution").
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.services.external_sources.crossref import lookup_by_doi
from app.services.external_sources.external_source_service import ExternalSourceService
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.retrieval.types import ExternalSource, RetrievalFilters, RetrievedChunk


class HybridSearchInput(BaseModel):
    """Input schema for the ``hybrid_search`` tool (design §4.7 table)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(min_length=1)
    project_id: UUID
    top_n: int = Field(default=8, gt=0)
    document_ids: list[UUID] | None = None


async def hybrid_search(
    input_data: HybridSearchInput, *, retrieval_service: RetrievalService
) -> list[RetrievedChunk]:
    """Ranked chunks with ``source_ref`` (design §4.7). Not cached — cheap and
    local (design §4.7 table)."""
    filters = RetrievalFilters(document_ids=input_data.document_ids)
    return await retrieval_service.hybrid_search(
        project_id=input_data.project_id,
        query=input_data.query,
        filters=filters,
        top_n=input_data.top_n,
    )


class ExternalSearchInput(BaseModel):
    """Shared input schema for the external academic search tools."""

    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(min_length=1)
    max_results: int = Field(default=5, gt=0)


async def external_search(
    input_data: ExternalSearchInput, *, external_source_service: ExternalSourceService
) -> list[ExternalSource]:
    """Normalised ``ExternalSource[]`` from arXiv, Semantic Scholar, CORE, and
    CrossRef combined (design §4.7 table: cached in Redis, keyed on the
    normalised query)."""
    return await external_source_service.search_all(input_data.query)


class CrossrefLookupInput(BaseModel):
    """Input schema for the ``crossref_lookup`` tool (design §4.7 table)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    doi: str = Field(min_length=1)


async def crossref_lookup(
    input_data: CrossrefLookupInput, *, timeout_seconds: float
) -> ExternalSource | None:
    """Canonical citation metadata for an exact DOI (design §4.7 table)."""
    return await lookup_by_doi(input_data.doi, timeout_seconds=timeout_seconds)
