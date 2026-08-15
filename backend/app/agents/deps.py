"""Collaborators every agent node needs (design §6.4, §4.6).

Bundled into one object so node factories in :mod:`app.agents.nodes` can be
built once per request with all their dependencies closed over, while
remaining independently testable with a constructed :class:`AgentDeps`
fixture (design §4.6 rule 1).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.llm.provider import LLMProvider
from app.db.repositories.agent_trace_repository import AgentTraceRepository
from app.services.external_sources.external_source_service import ExternalSourceService
from app.services.memory_service import MemoryService
from app.services.retrieval.retrieval_service import RetrievalService


@dataclass(slots=True)
class AgentDeps:
    """Everything an agent node needs beyond the shared run state."""

    retrieval_service: RetrievalService
    external_source_service: ExternalSourceService
    llm_provider: LLMProvider
    memory_service: MemoryService
    trace_repository: AgentTraceRepository
    max_subtasks: int
    max_retries: int
