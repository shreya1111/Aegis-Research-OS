"""Shared agent-run state (design §4.5 "Run — ephemeral", §4.6 rule 1).

Every node reads and writes this typed state rather than passing messages
directly — state is the contract between agents, which makes each node
independently testable with a constructed state fixture (design §4.6 rule 1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypedDict
from uuid import UUID

from app.services.retrieval.types import CitationMap, ExternalSource, RetrievedChunk


@dataclass(slots=True)
class Subtask:
    """One unit of work the Supervisor decomposed the request into."""

    description: str
    #: Set once the Retrieval/Summarizer nodes have processed this subtask.
    retrieved_chunks: list[RetrievedChunk] = field(default_factory=list)
    external_sources: list[ExternalSource] = field(default_factory=list)
    summary: str | None = None
    done: bool = False


class AgentRunState(TypedDict, total=False):
    """The full state threaded through the LangGraph graph (design §4.6).

    ``total=False`` because LangGraph nodes return partial updates; every key
    has an explicit default applied at graph entry (see :mod:`app.agents.graph`).
    """

    # -- Identity / scope -------------------------------------------------
    run_id: UUID
    project_id: UUID
    request: str

    # -- Plan ---------------------------------------------------------------
    subtasks: list[Subtask]
    #: Index of the subtask currently being worked, or ``None`` when the plan
    #: is complete and synthesis should begin.
    active_subtask_index: int | None
    #: Whether the request needs sources beyond the uploaded corpus
    #: (design §4.6 Retrieval row: "external academic and web search when the
    #: request needs sources beyond the corpus").
    needs_external_sources: bool

    # -- Memory (design §4.5) ------------------------------------------------
    memory_digest: str

    # -- Verification / synthesis --------------------------------------------
    citation_map: CitationMap
    draft_answer: str
    flagged_claims: list[str]

    # -- Critic loop (design §4.6 rule 2 "bounded loops") --------------------
    #: Caps live in state, not in a prompt, so a misbehaving model cannot
    #: cause an unbounded cost spiral.
    synthesis_retry_count: int
    retrieval_retry_count: int
    max_retries: int
    #: The Critic's routing decision for this pass, read directly by the
    #: graph's conditional edge — never re-derived from retry counters, which
    #: only bound how many times each verdict may be acted on.
    critic_verdict: Literal["approved", "revise", "insufficient_evidence"]

    # -- Output ---------------------------------------------------------------
    final_answer: str
    citations: list[dict[str, object]]
    #: Set when the retry caps were exhausted with unresolved citation
    #: markers still present — mirrors the Phase 4 ``citation_warning`` flag
    #: (design §4.2) so the API contract stays consistent across pipelines.
    citation_warning: bool
    #: Set when a node failed and the run degrades gracefully rather than
    #: crashing (design §4.6 rule 5).
    degraded: bool
    degraded_reason: str
