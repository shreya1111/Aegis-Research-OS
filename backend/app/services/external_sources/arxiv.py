"""arXiv connector (design §4.7, §8.6).

arXiv's API returns Atom XML rather than JSON, so this connector parses XML
directly rather than sharing the JSON-decode path the other connectors use.
No API key is required.
"""

from __future__ import annotations

from xml.etree import ElementTree

import httpx

from app.core.logging import get_logger
from app.services.retrieval.types import ExternalSource

logger = get_logger(__name__)

_BASE_URL = "http://export.arxiv.org/api/query"
_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


async def search_arxiv(
    query: str, *, max_results: int, timeout_seconds: float
) -> list[ExternalSource]:
    """Query arXiv; fails soft to an empty result on any error (design §4.7
    "fail soft": a dead external API returns an empty result, never a
    crash)."""
    params = {"search_query": f"all:{query}", "start": "0", "max_results": str(max_results)}
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(_BASE_URL, params=params)
        response.raise_for_status()
    except httpx.HTTPError:
        logger.warning(
            "external_source.arxiv.failed", extra={"event": "external_source.arxiv.failed"}
        )
        return []

    try:
        # arXiv's API is a trusted, fixed endpoint (not user-supplied), so
        # the stdlib parser's XML-attack surface (e.g. billion-laughs) is
        # not a realistic risk here; defusedxml would add a dependency for
        # no practical benefit on this call path.
        root = ElementTree.fromstring(response.text)  # noqa: S314
    except ElementTree.ParseError:
        return []

    sources: list[ExternalSource] = []
    for entry in root.findall("atom:entry", _ATOM_NS):
        title_element = entry.find("atom:title", _ATOM_NS)
        title = (title_element.text or "").strip() if title_element is not None else ""
        if not title:
            continue

        authors = [
            (name_element.text or "").strip()
            for author in entry.findall("atom:author", _ATOM_NS)
            if (name_element := author.find("atom:name", _ATOM_NS)) is not None
        ]
        summary_element = entry.find("atom:summary", _ATOM_NS)
        abstract = (summary_element.text or "").strip() if summary_element is not None else None
        id_element = entry.find("atom:id", _ATOM_NS)
        url = id_element.text.strip() if id_element is not None and id_element.text else None
        published_element = entry.find("atom:published", _ATOM_NS)
        year = None
        if published_element is not None and published_element.text:
            year = int(published_element.text[:4])

        sources.append(
            ExternalSource(
                title=title,
                authors=authors,
                year=year,
                venue="arXiv",
                identifier=url,
                url=url,
                abstract=abstract,
                provider="arXiv",
            )
        )
    return sources
