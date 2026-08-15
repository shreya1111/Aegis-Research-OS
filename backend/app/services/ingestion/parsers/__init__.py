"""Format-specific text extraction (design §8.2): PDF and DOCX parsers.

Each parser returns an :class:`app.services.ingestion.types.ExtractedDocument`
so the rest of the pipeline (metadata, chunking, embedding) is format-agnostic.
"""
