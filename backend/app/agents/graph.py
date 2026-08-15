"""The compiled LangGraph state machine (design §4.6 state diagram).

Wires the seven core nodes plus the terminal ``MemoryWrite`` step into the
exact transition graph from design §4.6:

```
[*] -> Supervisor
Supervisor -> Memory: load project context
Memory -> Supervisor
Supervisor -> Retrieval: dispatch subtasks
Retrieval -> Summarizer
Summarizer -> Supervisor: more subtasks?
Supervisor -> FactChecker: plan complete
FactChecker -> Synthesis
Synthesis -> Critic
Critic -> Synthesis: revise (max 1 retry)
Critic -> Retrieval: insufficient evidence (max 1 retry)
Critic -> MemoryWrite: approved
MemoryWrite -> [*]
```

Collaborators (LLM provider, retrieval service, etc.) are supplied per-run
through LangGraph's ``context_schema`` — :class:`AgentDeps` — rather than
closed over at build time. This lets
:class:`~app.services.agent_service.AgentService` compile the graph exactly
once per process (design §6.4: "own the LangGraph compiled graph") and reuse
it across every run.

Every node is wrapped by :func:`_guarded` so a node-level failure degrades
the run rather than raising out of ``ainvoke`` (design §4.6 rule 5:
"graceful degradation... the user sees a partial result with a clear notice
rather than an opaque error"). Once a run is marked degraded, every
conditional edge routes straight to ``END`` instead of continuing the plan.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime

from app.agents.deps import AgentDeps
from app.agents.nodes import (
    critic_node,
    fact_checker_node,
    memory_node,
    memory_write_node,
    retrieval_node,
    summarizer_node,
    supervisor_node,
    synthesis_node,
)
from app.agents.state import AgentRunState
from app.core.logging import get_logger
from app.services.retrieval.citation import to_message_citations

logger = get_logger(__name__)

_DEGRADED_NOTICE = (
    "This answer is incomplete: one step of the research pipeline failed and "
    "the run continued with whatever information had already been gathered."
)

_SUPERVISOR: Literal["supervisor"] = "supervisor"
_MEMORY: Literal["memory"] = "memory"
_RETRIEVAL: Literal["retrieval"] = "retrieval"
_SUMMARIZER: Literal["summarizer"] = "summarizer"
_FACT_CHECKER: Literal["fact_checker"] = "fact_checker"
_SYNTHESIS: Literal["synthesis"] = "synthesis"
_CRITIC: Literal["critic"] = "critic"
_MEMORY_WRITE: Literal["memory_write"] = "memory_write"
_END: Literal["__end__"] = "__end__"

_NodeFn = Callable[[AgentRunState, AgentDeps], Awaitable[dict[str, object]]]


def _best_effort_answer(state: AgentRunState) -> tuple[str, list[dict[str, object]]]:
    """Assemble the most useful answer already available in ``state``
    (design §4.6 rule 5: "hands partial state onward when the remaining
    pipeline can still produce something useful"), preferring an already
    Critic-approved answer, then a synthesised draft, then raw subtask
    summaries, over nothing at all."""
    final_answer = state.get("final_answer")
    if final_answer:
        # The pipeline had already reached an approved answer (e.g.
        # MemoryWrite failed after Critic approval) — the answer itself is
        # unaffected, only the memory side-effect was lost.
        return final_answer, state.get("citations", [])

    draft = state.get("draft_answer")
    citation_map = state.get("citation_map")
    if draft:
        citations = to_message_citations(draft, citation_map) if citation_map else []
        return f"{draft}\n\n_{_DEGRADED_NOTICE}_", citations

    summaries = [task.summary for task in state.get("subtasks", []) if task.summary]
    if summaries:
        return "\n\n".join(summaries) + f"\n\n_{_DEGRADED_NOTICE}_", []

    return _DEGRADED_NOTICE, []


def _guarded(node_name: str, node_fn: _NodeFn) -> _NodeFn:
    """Wrap a node so an unhandled exception degrades the run instead of
    crashing ``ainvoke`` (design §4.6 rule 5).

    The node's own :func:`~app.agents.tracing.traced_step` calls already
    write a ``failed`` trace row and re-raise before this wrapper ever sees
    the exception, so the failure is fully observable in the trace panel
    even though the run itself continues.
    """

    async def wrapped(state: AgentRunState, deps: AgentDeps) -> dict[str, object]:
        try:
            return await node_fn(state, deps)
        except Exception as exc:
            logger.warning(
                "agent.node.degraded",
                extra={
                    "event": "agent.node.degraded",
                    "node": node_name,
                    "run_id": str(state.get("run_id")),
                },
            )
            answer, citations = _best_effort_answer(state)
            return {
                "degraded": True,
                "degraded_reason": f"{node_name} failed: {exc}",
                "final_answer": answer,
                "citations": citations,
                "citation_warning": True,
            }

    return wrapped


def _route_from_supervisor(
    state: AgentRunState,
) -> Literal["memory", "retrieval", "fact_checker", "__end__"]:
    """Supervisor's first pass has no plan yet and must load memory first
    (design §4.6: "Supervisor --> Memory: load project context"); every later
    pass re-enters with a plan already set and either dispatches the next
    subtask or, once none remain, proceeds to fact-checking
    (design §4.6: "Supervisor --> FactChecker: plan complete")."""
    if state.get("degraded"):
        return _END
    if state.get("memory_digest") is None:
        return _MEMORY
    if state.get("active_subtask_index") is not None:
        return _RETRIEVAL
    return _FACT_CHECKER


def _route_from_critic(
    state: AgentRunState,
) -> Literal["synthesis", "retrieval", "memory_write", "__end__"]:
    if state.get("degraded"):
        return _END
    verdict = state.get("critic_verdict", "approved")
    if verdict == "revise":
        return _SYNTHESIS
    if verdict == "insufficient_evidence":
        return _RETRIEVAL
    return _MEMORY_WRITE


def _continue_or_end(next_node: str) -> Callable[[AgentRunState], str]:
    """Build a conditional-edge function for a normally-fixed transition, so
    a degraded upstream node routes straight to ``END`` instead of
    continuing a plan it no longer has the material to finish."""

    def route(state: AgentRunState) -> str:
        return _END if state.get("degraded") else next_node

    return route


async def _run_supervisor(
    state: AgentRunState, *, runtime: Runtime[AgentDeps]
) -> dict[str, object]:
    return await _guarded(_SUPERVISOR, supervisor_node)(state, runtime.context)


async def _run_memory(state: AgentRunState, *, runtime: Runtime[AgentDeps]) -> dict[str, object]:
    return await _guarded(_MEMORY, memory_node)(state, runtime.context)


async def _run_retrieval(
    state: AgentRunState, *, runtime: Runtime[AgentDeps]
) -> dict[str, object]:
    return await _guarded(_RETRIEVAL, retrieval_node)(state, runtime.context)


async def _run_summarizer(
    state: AgentRunState, *, runtime: Runtime[AgentDeps]
) -> dict[str, object]:
    return await _guarded(_SUMMARIZER, summarizer_node)(state, runtime.context)


async def _run_fact_checker(
    state: AgentRunState, *, runtime: Runtime[AgentDeps]
) -> dict[str, object]:
    return await _guarded(_FACT_CHECKER, fact_checker_node)(state, runtime.context)


async def _run_synthesis(
    state: AgentRunState, *, runtime: Runtime[AgentDeps]
) -> dict[str, object]:
    return await _guarded(_SYNTHESIS, synthesis_node)(state, runtime.context)


async def _run_critic(state: AgentRunState, *, runtime: Runtime[AgentDeps]) -> dict[str, object]:
    return await _guarded(_CRITIC, critic_node)(state, runtime.context)


async def _run_memory_write(
    state: AgentRunState, *, runtime: Runtime[AgentDeps]
) -> dict[str, object]:
    return await _guarded(_MEMORY_WRITE, memory_write_node)(state, runtime.context)


def build_agent_graph() -> StateGraph[AgentRunState, AgentDeps, AgentRunState, AgentRunState]:
    """Assemble the uncompiled graph.

    Kept separate from :func:`compile_agent_graph` so tests can inspect graph
    structure (nodes/edges) without compiling or running it.
    """
    graph: StateGraph[AgentRunState, AgentDeps, AgentRunState, AgentRunState] = StateGraph(
        AgentRunState, context_schema=AgentDeps
    )

    graph.add_node(_SUPERVISOR, _run_supervisor)
    graph.add_node(_MEMORY, _run_memory)
    graph.add_node(_RETRIEVAL, _run_retrieval)
    graph.add_node(_SUMMARIZER, _run_summarizer)
    graph.add_node(_FACT_CHECKER, _run_fact_checker)
    graph.add_node(_SYNTHESIS, _run_synthesis)
    graph.add_node(_CRITIC, _run_critic)
    graph.add_node(_MEMORY_WRITE, _run_memory_write)

    graph.set_entry_point(_SUPERVISOR)
    graph.add_conditional_edges(
        _SUPERVISOR,
        _route_from_supervisor,
        {_MEMORY: _MEMORY, _RETRIEVAL: _RETRIEVAL, _FACT_CHECKER: _FACT_CHECKER, _END: END},
    )
    graph.add_conditional_edges(
        _MEMORY, _continue_or_end(_SUPERVISOR), {_SUPERVISOR: _SUPERVISOR, _END: END}
    )
    graph.add_conditional_edges(
        _RETRIEVAL, _continue_or_end(_SUMMARIZER), {_SUMMARIZER: _SUMMARIZER, _END: END}
    )
    graph.add_conditional_edges(
        _SUMMARIZER, _continue_or_end(_SUPERVISOR), {_SUPERVISOR: _SUPERVISOR, _END: END}
    )
    graph.add_conditional_edges(
        _FACT_CHECKER, _continue_or_end(_SYNTHESIS), {_SYNTHESIS: _SYNTHESIS, _END: END}
    )
    graph.add_conditional_edges(
        _SYNTHESIS, _continue_or_end(_CRITIC), {_CRITIC: _CRITIC, _END: END}
    )
    graph.add_conditional_edges(
        _CRITIC,
        _route_from_critic,
        {_SYNTHESIS: _SYNTHESIS, _RETRIEVAL: _RETRIEVAL, _MEMORY_WRITE: _MEMORY_WRITE, _END: END},
    )
    graph.add_edge(_MEMORY_WRITE, END)

    return graph


def compile_agent_graph() -> (
    CompiledStateGraph[AgentRunState, AgentDeps, AgentRunState, AgentRunState]
):
    """Build and compile the graph once; callers reuse the returned object
    across every run (design §6.4: `AgentService` "own[s] the LangGraph
    compiled graph")."""
    return build_agent_graph().compile()
