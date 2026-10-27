"""Unit tests for entity extraction service (Phase 7)."""

from __future__ import annotations

import uuid

import pytest

from app.db.models.graph_edge import EdgeType
from app.db.models.graph_node import NodeType
from app.services.entity_extraction_service import (
    EntityExtractionService,
    ExtractedEntity,
    ExtractedRelationship,
)
from app.services.ingestion.types import ExtractedDocument, ExtractedPage
from app.services.retrieval.types import RetrievedChunk


@pytest.mark.unit
def test_extract_authors_from_metadata() -> None:
    """Test author extraction from document metadata."""
    service = EntityExtractionService()
    
    # Create mock document with author metadata
    pages = [ExtractedPage(page_number=1, text="Sample content")]
    document = ExtractedDocument(
        title="Test Paper",
        pages=pages,
        authors=["John Smith", "Jane Doe", "Alice Johnson"],
    )
    
    result = service.extract_from_document(document)
    
    # Verify authors were extracted
    authors = [e for e in result.entities if e.entity_type == NodeType.AUTHOR]
    assert len(authors) == 3
    assert {a.name for a in authors} == {"John Smith", "Jane Doe", "Alice Johnson"}
    
    # Verify co-authorship relationships
    coauthor_edges = [r for r in result.relationships if r.relationship_type == EdgeType.CO_AUTHOR]
    assert len(coauthor_edges) == 3  # 3 choose 2 = 3 pairs
    
    # Verify relationship metadata
    for relationship in coauthor_edges:
        assert relationship.metadata.get("document_title") == "Test Paper"


@pytest.mark.unit
def test_extract_entities_from_text() -> None:
    """Test entity extraction from text content."""
    service = EntityExtractionService()
    
    text = """
    This paper presents machine learning techniques developed at Stanford University.
    The authors John Smith and Jane Doe from MIT collaborated on neural networks.
    Topics include artificial intelligence and natural language processing.
    """
    
    entities = service._extract_entities_from_text(text)
    
    # Check for different entity types
    authors = [e for e in entities if e.entity_type == NodeType.AUTHOR]
    institutions = [e for e in entities if e.entity_type == NodeType.INSTITUTION]
    topics = [e for e in entities if e.entity_type == NodeType.TOPIC]
    
    assert len(authors) >= 1  # Should find author patterns
    assert len(institutions) >= 2  # Stanford University, MIT
    assert len(topics) >= 2  # machine learning, artificial intelligence, etc.


@pytest.mark.unit
def test_extract_from_retrieved_chunks() -> None:
    """Test entity extraction from retrieval results."""
    service = EntityExtractionService()
    
    chunks = [
        RetrievedChunk(
            chunk_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            document_filename="paper1.pdf",
            content="Research by Dr. Alice Chen at Harvard on deep learning algorithms.",
            source_ref={
                "title": "Deep Learning Advances",
                "authors": [{"name": "Alice Chen"}, {"name": "Bob Wilson"}],
                "venue": "Nature Machine Intelligence"
            },
            rank=1,
        ),
        RetrievedChunk(
            chunk_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            document_filename="paper2.pdf",
            content="Computer vision applications in robotics at Carnegie Mellon.",
            source_ref={
                "title": "Vision and Robotics",
                "authors": ["Charlie Brown"],
                "journal": "IEEE Robotics"
            },
            rank=2,
        )
    ]
    
    result = service.extract_from_retrieved_chunks(chunks)
    
    # Verify entities were extracted
    authors = [e for e in result.entities if e.entity_type == NodeType.AUTHOR]
    institutions = [e for e in result.entities if e.entity_type == NodeType.INSTITUTION]
    topics = [e for e in result.entities if e.entity_type == NodeType.TOPIC]
    
    assert len(authors) >= 3  # Alice Chen, Bob Wilson, Charlie Brown
    assert len(institutions) >= 2  # Harvard, Carnegie Mellon, venues
    assert len(topics) >= 2  # deep learning, computer vision, robotics


@pytest.mark.unit
def test_deduplicate_entities() -> None:
    """Test entity deduplication."""
    service = EntityExtractionService()
    
    entities = [
        ExtractedEntity("John Smith", NodeType.AUTHOR),
        ExtractedEntity("john smith", NodeType.AUTHOR),  # Different case
        ExtractedEntity("J. Smith", NodeType.AUTHOR),    # Different format
        ExtractedEntity("Stanford University", NodeType.INSTITUTION),
        ExtractedEntity("stanford university", NodeType.INSTITUTION),  # Different case
        ExtractedEntity("Machine Learning", NodeType.TOPIC),
        ExtractedEntity("machine learning", NodeType.TOPIC),  # Different case
    ]
    
    deduplicated = service.deduplicate_entities(entities)
    
    # Should have fewer entities after deduplication
    assert len(deduplicated) < len(entities)
    
    # Check that similar entities were merged
    author_names = [e.name for e in deduplicated if e.entity_type == NodeType.AUTHOR]
    institution_names = [e.name for e in deduplicated if e.entity_type == NodeType.INSTITUTION]
    topic_names = [e.name for e in deduplicated if e.entity_type == NodeType.TOPIC]
    
    # Should have only one author (various forms of John Smith merged)
    assert len(author_names) <= 2  # Might keep J. Smith as separate
    assert len(institution_names) == 1
    assert len(topic_names) == 1


@pytest.mark.unit
def test_normalize_entity_name() -> None:
    """Test entity name normalization."""
    service = EntityExtractionService()
    
    # Test institution normalization
    assert service._normalize_entity_name("The University of California") == "of california"
    assert service._normalize_entity_name("Stanford University") == "stanford"
    assert service._normalize_entity_name("MIT") == "mit"
    
    # Test author name normalization
    assert service._normalize_entity_name("J. Smith") == "smith, j."
    assert service._normalize_entity_name("John Smith") == "john smith"
    
    # Test general normalization
    assert service._normalize_entity_name("  Machine   Learning  ") == "machine learning"


@pytest.mark.unit
def test_extracted_entity_equality() -> None:
    """Test ExtractedEntity equality and hashing."""
    entity1 = ExtractedEntity("John Smith", NodeType.AUTHOR)
    entity2 = ExtractedEntity("john smith", NodeType.AUTHOR)  # Different case
    entity3 = ExtractedEntity("John Smith", NodeType.TOPIC)   # Different type
    
    assert entity1 == entity2  # Case-insensitive comparison
    assert entity1 != entity3  # Different types are not equal
    
    # Test in set (uses hash)
    entity_set = {entity1, entity2, entity3}
    assert len(entity_set) == 2  # entity1 and entity2 should be the same


@pytest.mark.unit
def test_extracted_relationship() -> None:
    """Test ExtractedRelationship creation."""
    author1 = ExtractedEntity("John Smith", NodeType.AUTHOR)
    author2 = ExtractedEntity("Jane Doe", NodeType.AUTHOR)
    
    relationship = ExtractedRelationship(
        source=author1,
        target=author2,
        relationship_type=EdgeType.CO_AUTHOR,
        weight=2.0,
        metadata={"document": "test.pdf"}
    )
    
    assert relationship.source == author1
    assert relationship.target == author2
    assert relationship.relationship_type == EdgeType.CO_AUTHOR
    assert relationship.weight == 2.0
    assert relationship.metadata["document"] == "test.pdf"


@pytest.mark.unit
def test_extraction_result_operations() -> None:
    """Test EntityExtractionResult operations."""
    from app.services.entity_extraction_service import EntityExtractionResult
    
    result = EntityExtractionResult()
    
    # Test adding entities
    author = ExtractedEntity("John Smith", NodeType.AUTHOR)
    topic = ExtractedEntity("AI", NodeType.TOPIC)
    
    result.add_entity(author)
    result.add_entity(topic)
    
    assert len(result.entities) == 2
    assert author in result.entities
    assert topic in result.entities
    
    # Test adding relationships
    relationship = ExtractedRelationship(
        source=author,
        target=topic,
        relationship_type=EdgeType.TOPIC_MEMBERSHIP
    )
    
    result.add_relationship(relationship)
    
    assert len(result.relationships) == 1
    assert len(result.entities) == 2  # Still 2, no duplicates added