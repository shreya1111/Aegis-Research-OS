"""CrossRef connector (design §4.7, §8.6).

Used both as a general search source and, more specifically, by
``crossref_lookup`` (design §4.7 tools table) to canonicalise a citation when
a DOI or exact title is available. No API key is required.
"""

from __future__ import annotations

import httpx

from app.core.logging import get_logger
from app.services.retrieval.types import ExternalSource

logger = get_logger(__name__)

_BASE_URL = "https://api.crossref.org/works"


def _as_str_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _parse_work(work: dict[str, object]) -> ExternalSource:
    author_entries = work.get("author")
    authors: list[str] = []
    if isinstance(author_entries, list):
        for entry in author_entries:
            if not isinstance(entry, dict):
                continue
            given = _as_str_or_none(entry.get("given"))
            family = _as_str_or_none(entry.get("family"))
            name = " ".join(part for part in (given, family) if part)
            if name:
                authors.append(name)

    titles = work.get("title")
    title = titles[0] if isinstance(titles, list) and titles and isinstance(titles[0], str) else ""

    published = work.get("published-print")
    if not isinstance(published, dict):
        published = work.get("published-online")
    date_parts = (
        published.get("date-parts") if isinstance(published, dict) else None
    )
    year: int | None = None
    if isinstance(date_parts, list) and date_parts and isinstance(date_parts[0], list):
        first_part = date_parts[0]
        if first_part and isinstance(first_part[0], int):
            year = first_part[0]

    container_titles = work.get("container-title")
    venue: str | None = None
    if isinstance(container_titles, list) and container_titles:
        first_venue = container_titles[0]
        if isinstance(first_venue, str):
            venue = first_venue

    return ExternalSource(
        title=str(title),
        authors=authors,
        year=year,
        venue=venue,
        identifier=_as_str_or_none(work.get("DOI")),
        url=_as_str_or_none(work.get("URL")),
        abstract=_as_str_or_none(work.get("abstract")),
        provider="CrossRef",
    )


async def search_crossref(
    query: str, *, max_results: int, timeout_seconds: float
) -> list[ExternalSource]:
    """General bibliographic search; fails soft to an empty result."""
    params = {"query.bibliographic": query, "rows": str(max_results)}
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(_BASE_URL, params=params)
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError):
        logger.warning(
            "external_source.crossref.failed", extra={"event": "external_source.crossref.failed"}
        )
        return []

    items = body.get("message", {}).get("items", [])
    return [_parse_work(item) for item in items]


async def lookup_by_doi(doi: str, *, timeout_seconds: float) -> ExternalSource | None:
    """Canonicalise a citation from an exact DOI (design §4.7 ``crossref_lookup``)."""
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(f"{_BASE_URL}/{doi}")
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    work = body.get("message")
    if not work:
        return None
    return _parse_work(work)
