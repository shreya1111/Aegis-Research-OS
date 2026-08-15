"""Aggregates every external connector behind one cached interface (design
§6.4 "ExternalSourceService", §4.7, §8.6).

The Retrieval agent's only route to external evidence. Every provider is
queried in parallel and every result routes through the shared Redis cache
before falling through to the network (design §6.8).
"""

from __future__ import annotations

import asyncio

from app.services.external_sources.arxiv import search_arxiv
from app.services.external_sources.cache import ExternalSourceCache, build_cache_key
from app.services.external_sources.core import search_core
from app.services.external_sources.crossref import search_crossref
from app.services.external_sources.semantic_scholar import search_semantic_scholar
from app.services.retrieval.types import ExternalSource


class ExternalSourceService:
    """Fan-out search across arXiv, Semantic Scholar, CORE, and CrossRef."""

    def __init__(
        self,
        *,
        cache: ExternalSourceCache,
        timeout_seconds: float,
        max_results: int,
        semantic_scholar_api_key: str = "",
        core_api_key: str = "",
    ) -> None:
        self._cache = cache
        self._timeout_seconds = timeout_seconds
        self._max_results = max_results
        self._semantic_scholar_api_key = semantic_scholar_api_key
        self._core_api_key = core_api_key

    async def search_all(self, query: str) -> list[ExternalSource]:
        """Query every provider concurrently and merge normalised results.

        Each provider's own cache entry is keyed independently so a hit on
        one provider does not require a hit on all (design §6.8 key
        taxonomy: ``ext:{provider}:{sha256(normalised_query)}``).
        """
        providers = ("arxiv", "semantic_scholar", "core", "crossref")
        results = await asyncio.gather(
            *(self._search_one(provider, query) for provider in providers)
        )
        merged: list[ExternalSource] = []
        for provider_results in results:
            merged.extend(provider_results)
        return merged

    async def _search_one(self, provider: str, query: str) -> list[ExternalSource]:
        key = build_cache_key(provider, query)
        cached = await self._cache.get(key)
        if cached is not None:
            return cached

        sources = await self._call_provider(provider, query)
        await self._cache.set(key, sources)
        return sources

    async def _call_provider(self, provider: str, query: str) -> list[ExternalSource]:
        if provider == "arxiv":
            return await search_arxiv(
                query, max_results=self._max_results, timeout_seconds=self._timeout_seconds
            )
        if provider == "semantic_scholar":
            return await search_semantic_scholar(
                query,
                max_results=self._max_results,
                timeout_seconds=self._timeout_seconds,
                api_key=self._semantic_scholar_api_key,
            )
        if provider == "core":
            return await search_core(
                query,
                max_results=self._max_results,
                timeout_seconds=self._timeout_seconds,
                api_key=self._core_api_key,
            )
        if provider == "crossref":
            return await search_crossref(
                query, max_results=self._max_results, timeout_seconds=self._timeout_seconds
            )
        return []
