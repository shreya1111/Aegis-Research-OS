"""Document ingestion pipeline: extract → metadata → chunk → embed → persist.

Owns the ``pending → processing → ready | failed`` lifecycle (design §6.4,
§8.1) and all extraction-failure handling. The public entry point is
:class:`app.services.ingestion.pipeline.IngestionPipeline`.
"""
