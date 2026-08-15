"""Unit tests for citation-map construction and validation (design §8.8)."""

from __future__ import annotations

import uuid

import pytest

from app.services.retrieval.citation import (
    build_citation_map,
    extract_markers,
    to_message_citations,
    validate_citations,
)
from app.services.retrieval.types import ExternalSource, RetrievedChunk


def _chunk(page_start: int = 1, page_end: int = 1) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_filename="paper.pdf",
        content="the chunk content",
        source_ref={"page_start": page_start, "page_end": page_end},
        rank=1,
    )


def _external_source() -> ExternalSource:
    return ExternalSource(
        title="A Study",
        authors=["A. Author"],
        year=2024,
        venue="Journal",
        identifier="10.1/xyz",
        url="https://example.com",
        abstract="abstract text",
        provider="arXiv",
    )


@pytest.mark.unit
def test_build_citation_map_assigns_a_page_marker_per_chunk() -> None:
    chunk = _chunk(page_start=4, page_end=4)

    citation_map = build_citation_map([chunk])

    assert "Doc 1, p.4" in citation_map.entries
    assert citation_map.entries["Doc 1, p.4"].chunk is chunk


@pytest.mark.unit
def test_build_citation_map_assigns_a_page_range_marker() -> None:
    chunk = _chunk(page_start=4, page_end=6)

    citation_map = build_citation_map([chunk])

    assert "Doc 1, pp.4-6" in citation_map.entries


@pytest.mark.unit
def test_external_sources_get_a_provider_labelled_marker_never_confused_with_a_doc() -> None:
    """Design §8.6: "an external source is never presented as if it came from
    the user's corpus"."""
    source = _external_source()

    citation_map = build_citation_map([], [source])

    assert "arXiv 1" in citation_map.entries
    assert citation_map.entries["arXiv 1"].external_source is source


@pytest.mark.unit
def test_extract_markers_finds_every_bracketed_marker() -> None:
    text = "Claim one [Doc 1, p.2]. Claim two [arXiv 1]."

    markers = extract_markers(text)

    assert markers == ["Doc 1, p.2", "arXiv 1"]


@pytest.mark.unit
def test_validate_citations_passes_when_every_marker_resolves() -> None:
    chunk = _chunk()
    citation_map = build_citation_map([chunk])
    text = "This is supported [Doc 1, p.1]."

    all_valid, unresolved = validate_citations(text, citation_map)

    assert all_valid is True
    assert unresolved == []


@pytest.mark.unit
def test_validate_citations_flags_an_unresolvable_marker() -> None:
    """The core enforcement point (design §8.8 step 4): a citation to a chunk
    never actually retrieved must not be presented as fact."""
    citation_map = build_citation_map([_chunk()])
    text = "This cites a source that was never retrieved [Doc 99, p.1]."

    all_valid, unresolved = validate_citations(text, citation_map)

    assert all_valid is False
    assert unresolved == ["Doc 99, p.1"]


@pytest.mark.unit
def test_to_message_citations_only_includes_resolved_markers_in_emission_order() -> None:
    chunk = _chunk()
    citation_map = build_citation_map([chunk])
    text = "First [Doc 1, p.1] then a fabricated one [Doc 5, p.9]."

    citations = to_message_citations(text, citation_map)

    assert len(citations) == 1
    assert citations[0]["marker"] == "Doc 1, p.1"
    assert citations[0]["chunk_id"] == str(chunk.chunk_id)
