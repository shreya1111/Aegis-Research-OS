"""Semantic Scholar connector (design §4.7, §8.6).

An API key is optional (higher rate limits with one); its absence is not an
error — it just means the anonymous rate limit applies (design §4.7 "fail
soft").
"""

from __future__ import annotations

import httpx

from app.core.logging import get_logger
from app.services.retrieval.types import ExternalSource

logger = get_logger(__name__)

_BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_FIELDS = "title,authors,year,venue,externalIds,abstract,url"


async def search_semantic_scholar(
    query: str, *, max_results: int, timeout_seconds: float, api_key: str = ""
) -> list[ExternalSource]:
    """Query Semantic Scholar; fails soft to an empty result on any error."""
    params = {"query": query, "limit": str(max_results), "fields": _FIELDS}
    headers = {"x-api-key": api_key} if api_key else {}

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(_BASE_URL, params=params, headers=headers)
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError):
        logger.warning(
            "external_source.semantic_scholar.failed",
            extra={"event": "external_source.semantic_scholar.failed"},
        )
        return []

    sources: list[ExternalSource] = []
    for paper in body.get("data", []):
        external_ids = paper.get("externalIds") or {}
        sources.append(
            ExternalSource(
                title=paper.get("title") or "",
                authors=[author.get("name", "") for author in paper.get("authors", []) or []],
                year=paper.get("year"),
                venue=paper.get("venue") or None,
                identifier=external_ids.get("DOI"),
                url=paper.get("url"),
                abstract=paper.get("abstract"),
                provider="Semantic Scholar",
            )
        )
    return sources
