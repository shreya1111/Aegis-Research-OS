"""Citation generation as a data-integrity problem (design §8.8).

Context assembly assigns a stable marker to each supplied chunk; the system
prompt requires the model to cite only those markers; emitted markers are
parsed and validated against the map. Every citation the model emits is
resolved against the set of chunk ids actually retrieved for that run — an
unresolvable citation is never presented as fact (design §4.2, §8.8).
"""

from __future__ import annotations

import re

from app.services.retrieval.types import (
    CitationMap,
    CitationMapEntry,
    ExternalSource,
    RetrievedChunk,
)

#: Markers look like `[Doc 2, p.4]` or `[S1]` — captured as `[...]` blocks so
#: parsing does not depend on a fixed internal format.
_MARKER_PATTERN = re.compile(r"\[([^\[\]]+)\]")


def build_citation_map(
    chunks: list[RetrievedChunk], external_sources: list[ExternalSource] | None = None
) -> CitationMap:
    """Assign one marker per chunk/source (design §8.8 step 1).

    Chunk markers use the document filename and page range so the model's
    citations are self-describing (`[Doc 2, p.4]`); external sources get a
    provider-labelled marker so they are never mistaken for the user's own
    corpus (design §8.6: "an external source is never presented as if it came
    from the user's corpus").
    """
    entries: dict[str, CitationMapEntry] = {}
    for index, chunk in enumerate(chunks, start=1):
        page_start = chunk.source_ref.get("page_start")
        page_end = chunk.source_ref.get("page_end")
        if page_start is not None:
            page_label = (
                f"p.{page_start}" if page_start == page_end else f"pp.{page_start}-{page_end}"
            )
            marker = f"Doc {index}, {page_label}"
        else:
            marker = f"Doc {index}"
        entries[marker] = CitationMapEntry(marker=marker, chunk=chunk)

    for index, source in enumerate(external_sources or [], start=1):
        marker = f"{source.provider} {index}"
        entries[marker] = CitationMapEntry(marker=marker, external_source=source)

    return CitationMap(entries=entries)


def extract_markers(text: str) -> list[str]:
    """Parse every `[...]`-bracketed marker the model emitted (design §8.8 step 3)."""
    return _MARKER_PATTERN.findall(text)


def validate_citations(text: str, citation_map: CitationMap) -> tuple[bool, list[str]]:
    """Check every emitted marker resolves within the map (design §8.8 step 4,
    the "100%-citation-validity" enforcement point).

    Returns ``(all_valid, unresolved_markers)``.
    """
    unresolved = [
        marker for marker in extract_markers(text) if citation_map.resolve(marker) is None
    ]
    return (len(unresolved) == 0, unresolved)


def to_message_citations(text: str, citation_map: CitationMap) -> list[dict[str, object]]:
    """Build the ``messages.citations`` payload (design §7.2) from every
    marker that resolved successfully, preserving emission order."""
    citations: list[dict[str, object]] = []
    for marker in extract_markers(text):
        entry = citation_map.resolve(marker)
        if entry is None:
            continue
        record: dict[str, object] = {"marker": marker}
        if entry.chunk is not None:
            record["chunk_id"] = str(entry.chunk.chunk_id)
            record["document_id"] = str(entry.chunk.document_id)
            record["page"] = entry.chunk.source_ref.get("page_start")
        elif entry.external_source is not None:
            record["external_source"] = {
                "title": entry.external_source.title,
                "url": entry.external_source.url,
                "provider": entry.external_source.provider,
            }
        citations.append(record)
    return citations
