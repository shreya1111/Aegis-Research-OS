"""SQLAlchemy declarative models, one module per aggregate.

Imported here so Alembic's autogenerate and the metadata used by tests see every
model regardless of which module happens to trigger the import.
"""

from app.db.models.agent_trace import AgentTrace
from app.db.models.base import Base
from app.db.models.conversation import Conversation
from app.db.models.document import Document, DocumentStatus
from app.db.models.document_chunk import DocumentChunk
from app.db.models.message import Message, MessageRole
from app.db.models.project import Project
from app.db.models.project_memory import ProjectMemory
from app.db.models.user import User

__all__ = [
    "AgentTrace",
    "Base",
    "Conversation",
    "Document",
    "DocumentChunk",
    "DocumentStatus",
    "Message",
    "MessageRole",
    "Project",
    "ProjectMemory",
    "User",
]
