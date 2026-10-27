"""Entity extraction service for knowledge graph construction (Phase 7).

Extracts authors, topics, and institutions from document content and external
API results to populate the knowledge graph with structured entities and relationships.
"""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.models.graph_edge import EdgeType
from app.db.models.graph_node import NodeType
from app.services.ingestion.types import ExtractedDocument
from app.services.retrieval.types import RetrievedChunk

logger = get_logger(__name__)


class ExtractedEntity:
    """A single extracted entity with its type and metadata."""
    
    def __init__(self, name: str, entity_type: NodeType, metadata: dict[str, Any] | None = None):
        self.name = name.strip()
        self.entity_type = entity_type
        self.metadata = metadata or {}
    
    def __hash__(self) -> int:
        return hash((self.name.lower(), self.entity_type))
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ExtractedEntity):
            return False
        return self.name.lower() == other.name.lower() and self.entity_type == other.entity_type


class ExtractedRelationship:
    """A relationship between two entities."""
    
    def __init__(
        self, 
        source: ExtractedEntity, 
        target: ExtractedEntity, 
        relationship_type: EdgeType,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None
    ):
        self.source = source
        self.target = target
        self.relationship_type = relationship_type
        self.weight = weight
        self.metadata = metadata or {}


class EntityExtractionResult:
    """Complete result of entity extraction from a source."""
    
    def __init__(self):
        self.entities: set[ExtractedEntity] = set()
        self.relationships: list[ExtractedRelationship] = []
    
    def add_entity(self, entity: ExtractedEntity) -> None:
        """Add an entity to the extraction result."""
        self.entities.add(entity)
    
    def add_relationship(self, relationship: ExtractedRelationship) -> None:
        """Add a relationship and ensure both entities are in the result."""
        self.entities.add(relationship.source)
        self.entities.add(relationship.target)
        self.relationships.append(relationship)


class EntityExtractionService:
    """Service for extracting entities and relationships from various sources."""

    def __init__(self):
        # Common academic institution indicators
        self._institution_patterns = [
            r'\b(?:University|College|Institute|School|Department)\s+of\s+[\w\s]+',
            r'[\w\s]+\s+(?:University|College|Institute|School|Department)\b',
            r'\b(?:MIT|Stanford|Harvard|Berkeley|Caltech|Oxford|Cambridge)\b',
        ]
        
        # Topic extraction patterns (basic keyword matching)
        self._topic_patterns = [
            r'\b(?:machine learning|artificial intelligence|deep learning|neural network)\b',
            r'\b(?:natural language processing|NLP|computer vision|robotics)\b',
            r'\b(?:data science|big data|analytics|statistics)\b',
            r'\b(?:algorithm|optimization|computational|mathematical)\b',
        ]

    def extract_from_document(self, document: ExtractedDocument) -> EntityExtractionResult:
        """Extract entities and relationships from a processed document."""
        result = EntityExtractionResult()
        
        # Combine all page text for analysis
        full_text = "\n".join(page.text for page in document.pages)
        
        # Extract document metadata entities
        if document.title:
            # Extract authors from metadata if available
            authors = self._extract_authors_from_metadata(document)
            for author in authors:
                result.add_entity(author)
            
            # Create co-authorship relationships
            for i, author1 in enumerate(authors):
                for author2 in authors[i+1:]:
                    relationship = ExtractedRelationship(
                        source=author1,
                        target=author2,
                        relationship_type=EdgeType.CO_AUTHOR,
                        metadata={"document_title": document.title}
                    )
                    result.add_relationship(relationship)
        
        # Extract entities from text content
        text_entities = self._extract_entities_from_text(full_text)
        for entity in text_entities:
            result.add_entity(entity)
        
        # Create topic membership relationships for authors
        authors = [e for e in result.entities if e.entity_type == NodeType.AUTHOR]
        topics = [e for e in result.entities if e.entity_type == NodeType.TOPIC]
        
        for author in authors:
            for topic in topics:
                relationship = ExtractedRelationship(
                    source=author,
                    target=topic,
                    relationship_type=EdgeType.TOPIC_MEMBERSHIP,
                    metadata={"document_title": document.title or "Unknown"}
                )
                result.add_relationship(relationship)
        
        return result

    def extract_from_retrieved_chunks(self, chunks: list[RetrievedChunk]) -> EntityExtractionResult:
        """Extract entities from external search results and citations."""
        result = EntityExtractionResult()
        
        for chunk in chunks:
            # Extract from chunk content
            chunk_entities = self._extract_entities_from_text(chunk.content)
            for entity in chunk_entities:
                result.add_entity(entity)
            
            # Extract from source reference if available
            if chunk.source_ref:
                source_entities = self._extract_from_source_reference(chunk.source_ref)
                for entity in source_entities:
                    result.add_entity(entity)
        
        return result

    def _extract_authors_from_metadata(self, document: ExtractedDocument) -> list[ExtractedEntity]:
        """Extract author entities from document metadata."""
        authors = []
        
        # Check if authors are in metadata (from PDF metadata or external sources)
        if hasattr(document, 'authors') and document.authors:
            for author_name in document.authors:
                if author_name and author_name.strip():
                    author = ExtractedEntity(
                        name=author_name.strip(),
                        entity_type=NodeType.AUTHOR,
                        metadata={"source": "document_metadata"}
                    )
                    authors.append(author)
        
        return authors

    def _extract_entities_from_text(self, text: str) -> list[ExtractedEntity]:
        """Extract entities from text content using pattern matching."""
        entities = []
        
        # Extract institutions
        for pattern in self._institution_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                institution_name = match.group().strip()
                if len(institution_name) > 3:  # Filter very short matches
                    entity = ExtractedEntity(
                        name=institution_name,
                        entity_type=NodeType.INSTITUTION,
                        metadata={"extraction_method": "pattern_matching"}
                    )
                    entities.append(entity)
        
        # Extract topics
        for pattern in self._topic_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                topic_name = match.group().strip()
                entity = ExtractedEntity(
                    name=topic_name,
                    entity_type=NodeType.TOPIC,
                    metadata={"extraction_method": "pattern_matching"}
                )
                entities.append(entity)
        
        # Extract potential author names from text (basic pattern)
        # Look for patterns like "Smith et al." or "John Smith and Jane Doe"
        author_patterns = [
            r'\b[A-Z][a-z]+\s+(?:et\s+al\.?|and\s+[A-Z][a-z]+)',
            r'\b[A-Z]\.\s*[A-Z][a-z]+\b',  # J. Smith format
            r'\b[A-Z][a-z]+,\s*[A-Z]\.\s*[A-Z]?\.\?',  # Smith, J. A. format
        ]
        
        for pattern in author_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                author_name = re.sub(r'\s+(?:et\s+al\.?|and.*)', '', match.group()).strip()
                if len(author_name) > 2:
                    entity = ExtractedEntity(
                        name=author_name,
                        entity_type=NodeType.AUTHOR,
                        metadata={"extraction_method": "text_pattern"}
                    )
                    entities.append(entity)
        
        return entities

    def _extract_from_source_reference(self, source_ref: dict[str, Any]) -> list[ExtractedEntity]:
        """Extract entities from source reference metadata."""
        entities = []
        
        # Extract from document title if present
        if "title" in source_ref:
            title_entities = self._extract_entities_from_text(str(source_ref["title"]))
            entities.extend(title_entities)
        
        # Extract authors if present
        if "authors" in source_ref:
            authors_data = source_ref["authors"]
            if isinstance(authors_data, list):
                for author in authors_data:
                    if isinstance(author, str):
                        entity = ExtractedEntity(
                            name=author,
                            entity_type=NodeType.AUTHOR,
                            metadata={"source": "external_reference"}
                        )
                        entities.append(entity)
                    elif isinstance(author, dict) and "name" in author:
                        entity = ExtractedEntity(
                            name=str(author["name"]),
                            entity_type=NodeType.AUTHOR,
                            metadata={
                                "source": "external_reference",
                                **{k: v for k, v in author.items() if k != "name"}
                            }
                        )
                        entities.append(entity)
        
        # Extract venue/journal as institution
        if "venue" in source_ref or "journal" in source_ref:
            venue = source_ref.get("venue") or source_ref.get("journal")
            if venue and isinstance(venue, str):
                entity = ExtractedEntity(
                    name=venue,
                    entity_type=NodeType.INSTITUTION,
                    metadata={"source": "external_reference", "type": "venue"}
                )
                entities.append(entity)
        
        return entities

    def deduplicate_entities(self, entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
        """Remove duplicate entities based on name similarity."""
        unique_entities = {}
        
        for entity in entities:
            # Normalize name for comparison
            normalized_name = self._normalize_entity_name(entity.name)
            key = (normalized_name, entity.entity_type)
            
            if key not in unique_entities:
                unique_entities[key] = entity
            else:
                # Merge metadata from duplicates
                existing = unique_entities[key]
                existing.metadata.update(entity.metadata)
        
        return list(unique_entities.values())

    def _normalize_entity_name(self, name: str) -> str:
        """Normalize entity names for deduplication."""
        # Remove extra whitespace and convert to lowercase
        normalized = re.sub(r'\s+', ' ', name.strip().lower())
        
        # Remove common prefixes/suffixes for institutions
        normalized = re.sub(r'\b(?:the|university|college|institute|department)\s+', '', normalized)
        normalized = re.sub(r'\s+(?:university|college|institute|department)\b', '', normalized)
        
        # Handle author name variations (J. Smith -> Smith, J.)
        if '.' in normalized and len(normalized.split()) == 2:
            parts = normalized.split()
            if len(parts[0]) <= 2:  # Likely an initial
                normalized = f"{parts[1]}, {parts[0]}"
        
        return normalized.strip()