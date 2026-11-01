"""Unit tests for graph repository (Phase 7)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.graph_edge import EdgeType, GraphEdge
from app.db.models.graph_node import GraphNode, NodeType
from app.db.repositories.graph_repository import GraphRepository


@pytest.mark.unit
async def test_create_node() -> None:
    """Test creating a graph node."""
    session = AsyncMock(spec=AsyncSession)
    repo = GraphRepository(session)
    
    project_id = uuid.uuid4()
    
    # Mock the node creation
    expected_node = GraphNode(
        id=uuid.uuid4(),
        project_id=project_id,
        node_type=NodeType.AUTHOR,
        name="John Smith",
        metadata_={"source": "test"},
    )
    
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    
    await repo.create_node(
        project_id=project_id,
        node_type=NodeType.AUTHOR,
        name="John Smith",
        metadata={"source": "test"},
    )
    
    # Verify session operations were called
    session.add.assert_called_once()
    session.commit.assert_called_once()
    session.refresh.assert_called_once()


@pytest.mark.unit
async def test_create_edge() -> None:
    """Test creating a graph edge."""
    session = AsyncMock(spec=AsyncSession)
    repo = GraphRepository(session)
    
    project_id = uuid.uuid4()
    source_id = uuid.uuid4()
    target_id = uuid.uuid4()
    
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    
    await repo.create_edge(
        project_id=project_id,
        source_node_id=source_id,
        target_node_id=target_id,
        edge_type=EdgeType.CO_AUTHOR,
        weight=1.5,
        metadata={"document": "test.pdf"},
    )
    
    # Verify session operations were called
    session.add.assert_called_once()
    session.commit.assert_called_once()
    session.refresh.assert_called_once()


@pytest.mark.unit 
async def test_get_nodes_for_project() -> None:
    """Test retrieving nodes for a project."""
    session = AsyncMock(spec=AsyncSession)
    repo = GraphRepository(session)
    
    project_id = uuid.uuid4()
    
    # Mock nodes
    mock_nodes = [
        GraphNode(
            id=uuid.uuid4(),
            project_id=project_id,
            node_type=NodeType.AUTHOR,
            name="John Smith",
            metadata_={},
        ),
        GraphNode(
            id=uuid.uuid4(),
            project_id=project_id,
            node_type=NodeType.TOPIC,
            name="Machine Learning",
            metadata_={},
        ),
    ]
    
    # Mock query execution
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_nodes
    session.execute.return_value = mock_result
    
    nodes = await repo.get_nodes_for_project(project_id)
    
    assert len(nodes) == 2
    session.execute.assert_called_once()


@pytest.mark.unit
async def test_get_nodes_for_project_with_type_filter() -> None:
    """Test retrieving nodes with type filter."""
    session = AsyncMock(spec=AsyncSession)
    repo = GraphRepository(session)
    
    project_id = uuid.uuid4()
    
    # Mock only author nodes
    mock_nodes = [
        GraphNode(
            id=uuid.uuid4(),
            project_id=project_id,
            node_type=NodeType.AUTHOR,
            name="John Smith",
            metadata_={},
        ),
    ]
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_nodes
    session.execute.return_value = mock_result
    
    nodes = await repo.get_nodes_for_project(project_id, node_type=NodeType.AUTHOR)
    
    assert len(nodes) == 1
    assert nodes[0].node_type == NodeType.AUTHOR
    session.execute.assert_called_once()


@pytest.mark.unit
async def test_search_nodes() -> None:
    """Test node search functionality."""
    session = AsyncMock(spec=AsyncSession)
    repo = GraphRepository(session)
    
    project_id = uuid.uuid4()
    query = "smith"
    
    mock_nodes = [
        GraphNode(
            id=uuid.uuid4(),
            project_id=project_id,
            node_type=NodeType.AUTHOR,
            name="John Smith",
            metadata_={},
        ),
        GraphNode(
            id=uuid.uuid4(),
            project_id=project_id,
            node_type=NodeType.AUTHOR,
            name="Jane Smith",
            metadata_={},
        ),
    ]
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_nodes
    session.execute.return_value = mock_result
    
    nodes = await repo.search_nodes(project_id, query)
    
    assert len(nodes) == 2
    session.execute.assert_called_once()


@pytest.mark.unit
async def test_get_graph_stats() -> None:
    """Test graph statistics retrieval."""
    session = AsyncMock(spec=AsyncSession)
    repo = GraphRepository(session)
    
    project_id = uuid.uuid4()
    
    # Mock node counts by type
    node_counts = [(NodeType.AUTHOR, 5), (NodeType.TOPIC, 3), (NodeType.INSTITUTION, 2)]
    edge_counts = [(EdgeType.CO_AUTHOR, 4), (EdgeType.TOPIC_MEMBERSHIP, 8)]
    
    # Mock two separate query executions
    mock_node_result = MagicMock()
    mock_node_result.all.return_value = node_counts
    mock_edge_result = MagicMock()
    mock_edge_result.all.return_value = edge_counts
    
    session.execute.side_effect = [mock_node_result, mock_edge_result]
    
    stats = await repo.get_graph_stats(project_id)
    
    assert stats["total_nodes"] == 10  # 5 + 3 + 2
    assert stats["total_edges"] == 12  # 4 + 8
    assert stats["nodes_by_type"][NodeType.AUTHOR] == 5
    assert stats["nodes_by_type"][NodeType.TOPIC] == 3
    assert stats["edges_by_type"][EdgeType.CO_AUTHOR] == 4


@pytest.mark.unit
async def test_get_node_neighbors() -> None:
    """Test retrieving node neighbors and connections."""
    session = AsyncMock(spec=AsyncSession)
    repo = GraphRepository(session)
    
    node_id = uuid.uuid4()
    project_id = uuid.uuid4()
    neighbor_id = uuid.uuid4()
    
    # Mock neighbor node
    neighbor_node = GraphNode(
        id=neighbor_id,
        project_id=project_id,
        node_type=NodeType.TOPIC,
        name="AI",
        metadata_={},
    )
    
    # Mock edge connecting to neighbor
    mock_edge = GraphEdge(
        id=uuid.uuid4(),
        project_id=project_id,
        source_node_id=node_id,
        target_node_id=neighbor_id,
        edge_type=EdgeType.TOPIC_MEMBERSHIP,
        weight=1.0,
        metadata_={},
    )
    mock_edge.target_node = neighbor_node
    
    # Mock query results - outgoing and incoming edges
    mock_outgoing_result = MagicMock()
    mock_outgoing_result.scalars.return_value.all.return_value = [mock_edge]
    mock_incoming_result = MagicMock()
    mock_incoming_result.scalars.return_value.all.return_value = []
    
    session.execute.side_effect = [mock_outgoing_result, mock_incoming_result]
    
    neighbors, edges = await repo.get_node_neighbors(node_id, project_id)
    
    assert len(neighbors) == 1
    assert neighbors[0].name == "AI"
    assert len(edges) == 1
    assert edges[0].edge_type == EdgeType.TOPIC_MEMBERSHIP


@pytest.mark.unit
async def test_delete_node() -> None:
    """Test node deletion."""
    session = AsyncMock(spec=AsyncSession)
    repo = GraphRepository(session)
    
    node_id = uuid.uuid4()
    project_id = uuid.uuid4()
    
    # Mock finding the node
    mock_node = GraphNode(
        id=node_id,
        project_id=project_id,
        node_type=NodeType.AUTHOR,
        name="John Smith",
        metadata_={},
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_node
    session.execute.return_value = mock_result
    
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    
    success = await repo.delete_node(node_id, project_id)
    
    assert success is True
    session.delete.assert_called_once_with(mock_node)
    session.commit.assert_called_once()


@pytest.mark.unit
async def test_delete_nonexistent_node() -> None:
    """Test deleting a node that doesn't exist."""
    session = AsyncMock(spec=AsyncSession)
    repo = GraphRepository(session)
    
    node_id = uuid.uuid4()
    project_id = uuid.uuid4()
    
    # Mock node not found
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result
    
    success = await repo.delete_node(node_id, project_id)
    
    assert success is False
    session.delete.assert_not_called()
    session.commit.assert_not_called()