"""SQLAlchemy declarative models, one module per aggregate.

Imported here so Alembic's autogenerate and the metadata used by tests see every
model regardless of which module happens to trigger the import.
"""

from app.db.models.agent_trace import AgentTrace
from app.db.models.base import Base
from app.db.models.conversation import Conversation
from app.db.models.document import Document, DocumentStatus
from app.db.models.document_chunk import DocumentChunk
from app.db.models.graph_edge import EdgeType, GraphEdge
from app.db.models.graph_node import GraphNode, NodeType
from app.db.models.message import Message, MessageRole
from app.db.models.project import Project
from app.db.models.project_memory import ProjectMemory
from app.db.models.report import Report, ReportStatus, ReportType
from app.db.models.user import User

__all__ = [
    "AgentTrace",
    "Base",
    "Conversation",
    "Document",
    "DocumentChunk",
    "DocumentStatus",
    "EdgeType",
    "GraphEdge",
    "GraphNode",
    "Message",
    "MessageRole",
    "NodeType",
    "Project",
    "ProjectMemory",
    "Report",
    "ReportStatus",
    "ReportType",
    "User",
]
