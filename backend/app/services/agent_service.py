"""Multi-agent orchestration entry point (design §6.4 "AgentService", §4.6).

Owns the compiled LangGraph graph and the full run lifecycle: mint a
``run_id``, seed the initial :class:`AgentRunState`, drive the graph to
completion while persisting each node's trace as it happens (design §6.7:
"progress-observable from the database... not only from process memory"),
then persist the final answer as an assistant :class:`Message` exactly like
:class:`~app.services.rag_service.RagService` does for Phase 4, so both
pipelines produce an identical, indistinguishable API response shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID, uuid4

from langgraph.graph.state import CompiledStateGraph

from app.agents.deps import AgentDeps
from app.agents.graph import compile_agent_graph
from app.agents.state import AgentRunState
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.db.models.conversation import Conversation
from app.db.models.message import MessageRole
from app.db.repositories.agent_trace_repository import AgentTraceRepository
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.message_repository import MessageRepository
from app.services.agent_run_status import AgentRunStatusCache
from app.services.retrieval.types import RetrievedChunk

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_compiled_agent_graph() -> CompiledStateGraph[
    AgentRunState, AgentDeps, AgentRunState, AgentRunState
]:
    """Return the process-wide compiled graph singleton.

    Compiling is pure graph-structure assembly (no I/O, no provider calls),
    so it is cheap, but there is still no reason to redo it per run — every
    run supplies its own :class:`AgentDeps` through LangGraph's
    ``context_schema`` at invocation time (design §6.4: `AgentService`
    "own[s] the LangGraph compiled graph").
    """
    return compile_agent_graph()


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    """The result of one completed multi-agent run."""

    run_id: UUID
    message_id: UUID
    answer: str
    citations: list[dict[str, object]]
    sources: list[RetrievedChunk]
    citation_warning: bool
    degraded: bool
    degraded_reason: str | None


class AgentService:
    """Starts and drives one LangGraph agent run end to end."""

    def __init__(
        self,
        *,
        deps: AgentDeps,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
        trace_repository: AgentTraceRepository,
        run_status_cache: AgentRunStatusCache,
        graph: CompiledStateGraph[AgentRunState, AgentDeps, AgentRunState, AgentRunState]
        | None = None,
    ) -> None:
        self._deps = deps
        self._conversations = conversation_repository
        self._messages = message_repository
        self._traces = trace_repository
        self._run_status = run_status_cache
        self._graph = graph or get_compiled_agent_graph()

    async def run(
        self,
        *,
        project_id: UUID,
        request: str,
        conversation_id: UUID | None = None,
    ) -> AgentRunResult:
        """Drive the full multi-agent pipeline for one research request and
        persist its outcome (design §3.5 end-to-end flow)."""
        run_id = uuid4()
        conversation = await self._resolve_conversation(
            project_id=project_id, conversation_id=conversation_id
        )

        await self._run_status.set_status(run_id, "running")

        initial_state: AgentRunState = {
            "run_id": run_id,
            "project_id": project_id,
            "request": request,
            "max_retries": self._deps.max_retries,
            "synthesis_retry_count": 0,
            "retrieval_retry_count": 0,
        }

        final_state = initial_state
        try:
            # ``stream_mode="updates"`` yields one ``{node_name: partial_state}``
            # dict per completed node rather than only the final state, so the
            # trace rows each node writes via `traced_step` land in the
            # database progressively as the run proceeds — the same
            # "progress-observable from the database" contract ingestion
            # already follows (design §6.7) — rather than becoming visible
            # only once the entire graph finishes.
            async for update in self._graph.astream(
                initial_state, context=self._deps, stream_mode="updates"
            ):
                for partial in update.values():
                    # A node that returns an empty update (e.g. MemoryWrite,
                    # which only has a side effect) surfaces here as ``None``
                    # rather than ``{}``.
                    if partial:
                        final_state.update(partial)
        except Exception:
            logger.exception(
                "agent.run.failed", extra={"event": "agent.run.failed", "run_id": str(run_id)}
            )
            await self._run_status.set_status(run_id, "failed", detail=str(run_id))
            raise

        answer = final_state.get(
            "final_answer", "The research pipeline did not produce an answer."
        )
        citations = final_state.get("citations", [])
        degraded = final_state.get("degraded", False)
        degraded_reason = final_state.get("degraded_reason")
        citation_warning = final_state.get("citation_warning", False)

        sources = [
            chunk for task in final_state.get("subtasks", []) for chunk in task.retrieved_chunks
        ]

        await self._messages.create(
            conversation_id=conversation.id, role=MessageRole.USER, content=request
        )
        assistant_message = await self._messages.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=answer,
            citations=citations,
        )
        await self._conversations.set_title_if_unset(conversation, request)
        await self._traces.attach_message(run_id, assistant_message.id, project_id=project_id)

        await self._run_status.set_status(
            run_id, "failed" if degraded else "completed", detail=degraded_reason or ""
        )

        return AgentRunResult(
            run_id=run_id,
            message_id=assistant_message.id,
            answer=answer,
            citations=citations,
            sources=sources,
            citation_warning=citation_warning,
            degraded=degraded,
            degraded_reason=degraded_reason,
        )

    async def _resolve_conversation(
        self, *, project_id: UUID, conversation_id: UUID | None
    ) -> Conversation:
        if conversation_id is not None:
            conversation = await self._conversations.get_by_id_for_project(
                conversation_id, project_id=project_id
            )
            if conversation is None:
                raise NotFoundError("Conversation not found.")
            return conversation
        return await self._conversations.get_or_create_default(project_id=project_id)
