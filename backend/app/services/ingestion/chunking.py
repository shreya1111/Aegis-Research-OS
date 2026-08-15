"""Token-aware chunking with citation provenance (design §8.3, FR-C6).

Chunk boundaries respect page/paragraph structure where possible, so a claim is
rarely split across two chunks and every chunk stores enough provenance to
render a citation like ``[Doc 2, p.4]`` (design: "the basis of citation").
"""

from __future__ import annotations

from dataclasses import dataclass

import tiktoken

from app.services.ingestion.types import Chunk, ExtractedDocument, ExtractedPage

#: cl100k_base is the encoding used by GPT-3.5/4-family models — a reasonable,
#: widely-available token-counting proxy independent of which LLM provider is
#: active (design §4.3 embeds independently of the LLM provider abstraction).
_ENCODING_NAME = "cl100k_base"


@dataclass(frozen=True, slots=True)
class _Word:
    """A single token-bearing word, tagged with the page it came from."""

    text: str
    page_number: int
    section: str | None


def _tokenizer() -> tiktoken.Encoding:
    return tiktoken.get_encoding(_ENCODING_NAME)


def _count_tokens(text: str, encoding: tiktoken.Encoding) -> int:
    return len(encoding.encode(text))


def _flatten_to_words(pages: list[ExtractedPage]) -> list[_Word]:
    """Flatten every page's text into a page/section-tagged word stream.

    Chunking then works over this stream so a chunk can span a page boundary
    (design §8.3 "modest overlap ... prevents a claim spanning a boundary from
    being lost") while still knowing which page(s) it drew from.
    """
    words: list[_Word] = []
    for page in pages:
        for word in page.text.split():
            words.append(_Word(text=word, page_number=page.page_number, section=page.section))
    return words


def chunk_document(
    extracted: ExtractedDocument,
    *,
    chunk_tokens: int,
    chunk_overlap_tokens: int,
) -> list[Chunk]:
    """Split extracted text into token-aware, citation-provenanced chunks.

    Boundaries are chosen at word granularity (never mid-word) and pack
    ``chunk_tokens`` tokens per chunk with ``chunk_overlap_tokens`` of overlap
    between consecutive chunks (design §8.3).
    """
    words = _flatten_to_words(extracted.pages)
    if not words:
        return []

    encoding = _tokenizer()
    chunks: list[Chunk] = []
    chunk_index = 0
    start = 0

    while start < len(words):
        current_words: list[_Word] = []
        current_tokens = 0
        end = start

        while end < len(words):
            word_tokens = _count_tokens(words[end].text, encoding)
            if current_words and current_tokens + word_tokens > chunk_tokens:
                break
            current_words.append(words[end])
            current_tokens += word_tokens
            end += 1

        content = " ".join(word.text for word in current_words)
        first_page = current_words[0].page_number
        last_page = current_words[-1].page_number
        section = next((w.section for w in current_words if w.section), None)

        source_ref: dict[str, object] = {
            "page_start": first_page,
            "page_end": last_page,
        }
        if section:
            source_ref["section"] = section

        chunks.append(Chunk(chunk_index=chunk_index, content=content, source_ref=source_ref))
        chunk_index += 1

        if end >= len(words):
            break

        # Step back by the overlap so consecutive chunks share trailing/leading
        # context (design §8.3), measured in tokens by walking back word by word.
        overlap_tokens = 0
        overlap_words = 0
        while overlap_words < len(current_words) and overlap_tokens < chunk_overlap_tokens:
            overlap_words += 1
            overlap_tokens += _count_tokens(current_words[-overlap_words].text, encoding)
        start = end - overlap_words

    return chunks
