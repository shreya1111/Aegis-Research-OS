"""Unit tests for graph service (Phase 7)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from app.db.models.graph_edge import EdgeType
from app.db.models.graph_node import NodeType
from app.services.entity_extraction_service import (
    EntityExtractionResult,
    EntityExtractionService,
    ExtractedEntity,
    ExtractedRelationship,
)
from app.services.graph_service import GraphService
from app.services.ingestion.types import ExtractedDocument, ExtractedPage
from app.services.retrieval.types import RetrievedChunk


@pytest.mark.unit
async def test_process_document_entities() -> None:
    """Test processing entities from a document."""
    # Mock dependencies
    mock_graph_repo = AsyncMock()
    mock_extraction_service = Mock(spec=EntityExtractionService)
    
    service = GraphService(
        graph_repository=mock_graph_repo,
        entity_extraction_service=mock_extraction_service,
    )
    
    # Create test document
    pages = [ExtractedPage(page_number=1, text="Test content")]
    document = ExtractedDocument(
        title="Test Paper",
        pages=pages,
        authors=["John Smith"],
    )
    
    # Mock extraction results
    author_entity = ExtractedEntity("John Smith", NodeType.AUTHOR)
    topic_entity = ExtractedEntity("Machine Learning", NodeType.TOPIC)
    relationship = ExtractedRelationship(
        source=author_entity,
        target=topic_entity,
        relationship_type=EdgeType.TOPIC_MEMBERSHIP,
    )
    
    extraction_result = EntityExtractionResult()
    extraction_result.entities.add(author_entity)
    extraction_result.entities.add(topic_entity)
    extraction_result.relationships.append(relationship)
    
    mock_extraction_service.extract_from_document.return_value = extraction_result
    mock_extraction_service.deduplicate_entities.return_value = [author_entity, topic_entity]
    
    # Mock repository responses
    mock_author_node = Mock()
    mock_author_node.id = uuid.uuid4()
    mock_topic_node = Mock()
    mock_topic_node.id = uuid.uuid4()
    
    mock_graph_repo.get_or_create_node.side_effect = [mock_author_node, mock_topic_node]
    mock_graph_repo.get_or_create_edge.return_value = Mock()
    
    project_id = uuid.uuid4()
    
    # Execute
    await service.process_document_entities(project_id, document)
    
    # Verify calls
    mock_extraction_service.extract_from_document.assert_called_once_with(document)
    assert mock_graph_repo.get_or_create_node.call_count == 2
    mock_graph_repo.get_or_create_edge.assert_called_once()


@pytest.mark.unit
async def test_process_retrieval_entities() -> None:
    """Test processing entities from retrieval results."""
    mock_graph_repo = AsyncMock()
    mock_extraction_service = Mock(spec=EntityExtractionService)
    
    service = GraphService(
        graph_repository=mock_graph_repo,
        entity_extraction_service=mock_extraction_service,
    )
    
    # Create test chunks
    chunks = [
        RetrievedChunk(
            chunk_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            document_filename="research.pdf",
            content="Research by Dr. Smith",
            source_ref={"title": "AI Paper"},
            rank=1,
        )
    ]
    
    # Mock extraction results
    author_entity = ExtractedEntity("Dr. Smith", NodeType.AUTHOR)
    extraction_result = EntityExtractionResult()
    extraction_result.entities.add(author_entity)
    
    mock_extraction_service.extract_from_retrieved_chunks.return_value = extraction_result
    mock_extraction_service.deduplicate_entities.return_value = [author_entity]
    
    mock_graph_repo.get_or_create_node.return_value = Mock()
    
    project_id = uuid.uuid4()
    
    # Execute
    await service.process_retrieval_entities(project_id, chunks)
    
    # Verify calls
    mock_extraction_service.extract_from_retrieved_chunks.assert_called_once_with(chunks)
    mock_graph_repo.get_or_create_node.assert_called_once()


@pytest.mark.unit
async def test_get_graph_data() -> None:
    """Test getting formatted graph data."""
    mock_graph_repo = AsyncMock()
    mock_extraction_service = Mock(spec=EntityExtractionService)
    
    service = GraphService(
        graph_repository=mock_graph_repo,
        entity_extraction_service=mock_extraction_service,
    )
    
    # Mock nodes and edges
    mock_node = Mock()
    mock_node.id = uuid.uuid4()
    mock_node.name = "John Smith"
    mock_node.node_type = NodeType.AUTHOR
    mock_node.metadata_ = {"source": "test"}
    mock_node.created_at.isoformat.return_value = "2023-01-01T00:00:00"
    
    mock_edge = Mock()
    mock_edge.id = uuid.uuid4()
    mock_edge.source_node_id = mock_node.id
    mock_edge.target_node_id = uuid.uuid4()
    mock_edge.edge_type = EdgeType.CO_AUTHOR
    mock_edge.weight = 1.5
    mock_edge.metadata_ = {"document": "test.pdf"}
    mock_edge.created_at.isoformat.return_value = "2023-01-01T00:00:00"
    
    mock_graph_repo.get_nodes_for_project.return_value = [mock_node]
    mock_graph_repo.get_edges_for_project.return_value = [mock_edge]
    
    project_id = uuid.uuid4()
    
    # Execute
    result = await service.get_graph_data(project_id)
    
    # Verify structure
    assert "nodes" in result
    assert "edges" in result
    assert len(result["nodes"]) == 1
    assert len(result["edges"]) == 1
    
    node_data = result["nodes"][0]
    assert node_data["id"] == str(mock_node.id)
    assert node_data["data"]["label"] == "John Smith"
    assert node_data["data"]["nodeType"] == NodeType.AUTHOR.value
    
    edge_data = result["edges"][0]
    assert edge_data["id"] == str(mock_edge.id)
    assert edge_data["source"] == str(mock_edge.source_node_id)
    assert edge_data["data"]["edgeType"] == EdgeType.CO_AUTHOR.value


@pytest.mark.unit
async def test_get_node_details() -> None:
    """Test getting node details with neighbors."""
    mock_graph_repo = AsyncMock()
    mock_extraction_service = Mock(spec=EntityExtractionService)
    
    service = GraphService(
        graph_repository=mock_graph_repo,
        entity_extraction_service=mock_extraction_service,
    )
    
    node_id = uuid.uuid4()
    project_id = uuid.uuid4()
    
    # Mock node
    mock_node = Mock()
    mock_node.id = node_id
    mock_node.name = "John Smith"
    mock_node.node_type = NodeType.AUTHOR
    mock_node.metadata_ = {"affiliation": "MIT"}
    mock_node.created_at.isoformat.return_value = "2023-01-01T00:00:00"
    
    # Mock neighbor
    mock_neighbor = Mock()
    mock_neighbor.id = uuid.uuid4()
    mock_neighbor.name = "AI"
    mock_neighbor.node_type = NodeType.TOPIC
    
    # Mock edge
    mock_edge = Mock()
    mock_edge.id = uuid.uuid4()
    mock_edge.edge_type = EdgeType.TOPIC_MEMBERSHIP
    mock_edge.weight = 1.0
    mock_edge.source_node_id = node_id
    mock_edge.target_node_id = mock_neighbor.id
    mock_edge.metadata_ = {}
    
    mock_graph_repo.get_node_by_id.return_value = mock_node
    mock_graph_repo.get_node_neighbors.return_value = ([mock_neighbor], [mock_edge])
    
    # Execute
    result = await service.get_node_details(project_id, node_id)
    
    # Verify structure
    assert result is not None
    assert "node" in result
    assert "neighbors" in result
    assert "connections" in result
    
    assert result["node"]["name"] == "John Smith"
    assert len(result["neighbors"]) == 1
    assert len(result["connections"]) == 1


@pytest.mark.unit
async def test_get_node_details_not_found() -> None:
    """Test getting details for non-existent node."""
    mock_graph_repo = AsyncMock()
    mock_extraction_service = Mock(spec=EntityExtractionService)
    
    service = GraphService(
        graph_repository=mock_graph_repo,
        entity_extraction_service=mock_extraction_service,
    )
    
    node_id = uuid.uuid4()
    project_id = uuid.uuid4()
    
    mock_graph_repo.get_node_by_id.return_value = None
    
    # Execute
    result = await service.get_node_details(project_id, node_id)
    
    # Should return None for non-existent node
    assert result is None


@pytest.mark.unit
async def test_search_nodes() -> None:
    """Test node search functionality."""
    mock_graph_repo = AsyncMock()
    mock_extraction_service = Mock(spec=EntityExtractionService)
    
    service = GraphService(
        graph_repository=mock_graph_repo,
        entity_extraction_service=mock_extraction_service,
    )
    
    project_id = uuid.uuid4()
    query = "smith"
    
    # Mock search results
    mock_node = Mock()
    mock_node.id = uuid.uuid4()
    mock_node.name = "John Smith"
    mock_node.node_type = NodeType.AUTHOR
    mock_node.metadata_ = {}
    
    mock_graph_repo.search_nodes.return_value = [mock_node]
    
    # Execute
    results = await service.search_nodes(project_id, query)
    
    # Verify
    assert len(results) == 1
    assert results[0]["name"] == "John Smith"
    assert results[0]["type"] == NodeType.AUTHOR.value


@pytest.mark.unit
async def test_create_manual_relationship() -> None:
    """Test creating manual relationships."""
    mock_graph_repo = AsyncMock()
    mock_extraction_service = Mock(spec=EntityExtractionService)
    
    service = GraphService(
        graph_repository=mock_graph_repo,
        entity_extraction_service=mock_extraction_service,
    )
    
    project_id = uuid.uuid4()
    source_id = uuid.uuid4()
    target_id = uuid.uuid4()
    
    mock_edge = Mock()
    mock_graph_repo.get_or_create_edge.return_value = mock_edge
    
    # Execute
    result = await service.create_manual_relationship(
        project_id=project_id,
        source_node_id=source_id,
        target_node_id=target_id,
        relationship_type=EdgeType.CO_AUTHOR,
        weight=2.0,
        metadata={"test": "value"},
    )
    
    # Verify
    assert result == mock_edge
    mock_graph_repo.get_or_create_edge.assert_called_once_with(
        project_id=project_id,
        source_node_id=source_id,
        target_node_id=target_id,
        edge_type=EdgeType.CO_AUTHOR,
        weight=2.0,
        metadata={"test": "value"},
    )


@pytest.mark.unit
async def test_exception_handling_in_process_document() -> None:
    """Test exception handling in document processing."""
    mock_graph_repo = AsyncMock()
    mock_extraction_service = Mock(spec=EntityExtractionService)
    
    service = GraphService(
        graph_repository=mock_graph_repo,
        entity_extraction_service=mock_extraction_service,
    )
    
    # Mock extraction service to raise exception
    mock_extraction_service.extract_from_document.side_effect = Exception("Test error")
    
    pages = [ExtractedPage(page_number=1, text="Test")]
    document = ExtractedDocument(title="Test", pages=pages)
    project_id = uuid.uuid4()
    
    # Should re-raise the exception
    with pytest.raises(Exception, match="Test error"):
        await service.process_document_entities(project_id, document)