"""CORE connector (design §4.7, §8.6).

CORE requires an API key; if none is configured, this connector fails soft
immediately rather than making a call known to be rejected — the same
observable outcome as any other dead provider (design §4.7).
"""

from __future__ import annotations

import httpx

from app.core.logging import get_logger
from app.services.retrieval.types import ExternalSource

logger = get_logger(__name__)

_BASE_URL = "https://api.core.ac.uk/v3/search/works"


async def search_core(
    query: str, *, max_results: int, timeout_seconds: float, api_key: str
) -> list[ExternalSource]:
    """Query CORE; fails soft to an empty result when unconfigured or on error."""
    if not api_key:
        return []

    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"q": query, "limit": max_results}

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(_BASE_URL, json=payload, headers=headers)
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError):
        logger.warning(
            "external_source.core.failed", extra={"event": "external_source.core.failed"}
        )
        return []

    sources: list[ExternalSource] = []
    for result in body.get("results", []):
        year_published = result.get("yearPublished")
        authors = [author.get("name", "") for author in result.get("authors", []) or []]
        sources.append(
            ExternalSource(
                title=result.get("title") or "",
                authors=authors,
                year=int(year_published) if year_published else None,
                venue=result.get("publisher"),
                identifier=result.get("doi"),
                url=result.get("downloadUrl") or result.get("sourceFulltextUrls", [None])[0],
                abstract=result.get("abstract"),
                provider="CORE",
            )
        )
    return sources
