"""``agent_traces`` table (design §7.2, §6.9, §4.6).

The observability spine and a user-facing feature: every agent invocation is
recorded here (agent name, input/output summaries, tokens, latency, cost).
``run_id`` is carried on trace rows so ``GET /projects/{id}/traces/{run_id}``
can return an ordered run even before the assistant message is finalised
(design §7.2).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.message import Message


class AgentTrace(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One agent-node invocation record (design §4.6 rule 3 "trace-on-every-node")."""

    __tablename__ = "agent_traces"
    __table_args__ = (
        # Trace panel, in order (design §7.4).
        Index("ix_agent_traces_run_id_created_at", "run_id", "created_at"),
        # Trace for a completed answer (design §7.4).
        Index("ix_agent_traces_message_id", "message_id"),
        # Tenancy scope filter for GET /projects/{id}/traces/{run_id}: a run_id
        # is minted before any message exists, so it carries no natural
        # project link of its own. Denormalised here for the same reason
        # `document_chunks.project_id` is (design §7.2, §7.5) — so the scope
        # predicate is enforced inside the query, not inferred after the fact.
        Index("ix_agent_traces_project_id_run_id", "project_id", "run_id"),
    )

    #: Denormalised so a run's traces are provably scoped to the project that
    #: started the run, even before any message exists (see class docstring).
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    #: Nullable: traces are written as the run progresses, before the
    #: assistant message exists. Set once the message is persisted.
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=True,
    )
    #: Links every trace row belonging to the same run, independent of
    #: whether a message has been created yet (design §7.2).
    run_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    #: Summary only — never the full payload (design §6.9: "agent_traces
    #: stores input/output summaries, not full payloads").
    input_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    output_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    #: 0 on a cache hit (design §6.8).
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    estimated_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    #: `success` | `failed` | `skipped` — supports graceful degradation
    #: (design §4.6 rule 5): a failed node still yields a trace row.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success")

    message: Mapped[Message | None] = relationship(back_populates="traces")
