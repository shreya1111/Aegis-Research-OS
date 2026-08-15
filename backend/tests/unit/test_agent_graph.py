"""Unit tests for the compiled LangGraph agent graph (design §4.6).

Exercises the full state machine — bounded retry loops, graceful
degradation, and the Critic catching a deliberately-injected unsupported
claim — against a stubbed :class:`AgentDeps` (no HTTP, no database, no real
LLM call), per design §4.6 rule 1: "each node independently testable with a
constructed state fixture".
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.deps import AgentDeps
from app.agents.graph import compile_agent_graph
from app.agents.state import AgentRunState
from app.core.llm.provider import LLMResponse, Message
from app.services.retrieval.types import ExternalSource, RetrievedChunk


def _make_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_filename="paper.pdf",
        content="the retrieved content",
        source_ref={"page_start": 1, "page_end": 1},
        rank=1,
    )


def _base_deps(
    *, complete: Any, hybrid_search_result: list[RetrievedChunk] | None = None
) -> AgentDeps:
    llm = AsyncMock()
    llm.complete = complete

    retrieval_service = MagicMock()
    chunks = hybrid_search_result if hybrid_search_result is not None else [_make_chunk()]

    async def hybrid_search(
        *, project_id: object, query: str, filters: object = None, top_n: object = None
    ) -> list[RetrievedChunk]:
        return chunks

    retrieval_service.hybrid_search = hybrid_search

    external_source_service = MagicMock()

    async def search_all(query: str) -> list[ExternalSource]:
        return []

    external_source_service.search_all = search_all

    memory_service = AsyncMock()
    memory_service.read_digest = AsyncMock(return_value="(no memory)")
    memory_service.write_facts = AsyncMock(return_value=[])

    trace_repository: Any = AsyncMock()
    trace_repository.create = AsyncMock()

    return AgentDeps(
        retrieval_service=retrieval_service,
        external_source_service=external_source_service,
        llm_provider=llm,
        memory_service=memory_service,
        trace_repository=trace_repository,
        max_subtasks=6,
        max_retries=1,
    )


def _initial_state(request: str = "compare A and B") -> AgentRunState:
    return {
        "run_id": uuid4(),
        "project_id": uuid4(),
        "request": request,
        "max_retries": 1,
        "synthesis_retry_count": 0,
        "retrieval_retry_count": 0,
    }


def _happy_path_complete(
    synthesis_text: str = "Final answer citing [Doc 1, p.1].",
    critic_text: str = "APPROVED",
) -> Any:
    async def complete(
        messages: list[Message], tier: str, max_tokens: int, tools: object = None
    ) -> LLMResponse:
        system_prompt = messages[0].content
        if "research supervisor" in system_prompt:
            text = "1. Answer the question\nEXTERNAL: no"
        elif "Summarise" in system_prompt:
            text = "A summary with [Doc 1, p.1]."
        elif "fact-checking" in system_prompt:
            text = "ALL SUPPORTED"
        elif "composing the final" in system_prompt:
            text = synthesis_text
        elif "reviewing a synthesised" in system_prompt:
            text = critic_text
        else:
            text = "ok"
        return LLMResponse(
            text=text, tokens_in=10, tokens_out=10, model_used="test", estimated_cost_usd=0.0
        )

    return complete


@pytest.mark.unit
async def test_a_simple_run_reaches_an_approved_final_answer() -> None:
    deps = _base_deps(complete=_happy_path_complete())
    compiled = compile_agent_graph()

    result = await compiled.ainvoke(_initial_state(), context=deps)

    assert result["final_answer"] == "Final answer citing [Doc 1, p.1]."
    assert result["citation_warning"] is False
    assert len(result["citations"]) == 1


@pytest.mark.unit
async def test_every_node_invocation_writes_a_trace_row() -> None:
    """Design §4.6 rule 3: "trace-on-every-node"."""
    deps = _base_deps(complete=_happy_path_complete())
    compiled = compile_agent_graph()

    await compiled.ainvoke(_initial_state(), context=deps)

    trace_repository: Any = deps.trace_repository
    # Supervisor's re-entry pass is a pure routing decision with no LLM call
    # (design §4.6: only the initial decomposition is traced work), so a
    # one-subtask run traces: Supervisor, Memory, Retrieval, Summarizer,
    # Fact-Checker, Synthesis, Critic, MemoryWrite = 8 steps.
    assert trace_repository.create.await_count == 8
    agent_names = {call.kwargs["agent_name"] for call in trace_repository.create.await_args_list}
    assert agent_names == {
        "Supervisor/Planner",
        "Memory",
        "Retrieval",
        "Summarizer",
        "Fact-Checker/Citation",
        "Synthesis/Report-Writer",
        "Critic/Reviewer",
    }


@pytest.mark.unit
async def test_critic_catches_a_deliberately_injected_unsupported_claim() -> None:
    """Phase 5 acceptance criteria: "the Critic agent demonstrably catches
    and flags at least one deliberately-injected unsupported claim".

    The synthesised draft cites a marker that was never in the citation map
    (a fabricated, unsupported claim) — citation validation must catch this
    and the Critic routes it through the bounded revise loop rather than
    ever returning it to the user unflagged.
    """
    call_count = {"synthesis": 0}

    async def complete(
        messages: list[Message], tier: str, max_tokens: int, tools: object = None
    ) -> LLMResponse:
        system_prompt = messages[0].content
        if "research supervisor" in system_prompt:
            text = "1. Answer the question\nEXTERNAL: no"
        elif "Summarise" in system_prompt:
            text = "A summary with [Doc 1, p.1]."
        elif "fact-checking" in system_prompt:
            text = "ALL SUPPORTED"
        elif "composing the final" in system_prompt:
            call_count["synthesis"] += 1
            # First pass fabricates a citation to a source that was never
            # retrieved — the injected unsupported claim.
            text = "The study proves X beyond doubt [Doc 99, p.1]."
        elif "reviewing a synthesised" in system_prompt:
            text = "APPROVED"
        else:
            text = "ok"
        return LLMResponse(
            text=text, tokens_in=10, tokens_out=10, model_used="test", estimated_cost_usd=0.0
        )

    deps = _base_deps(complete=complete)
    compiled = compile_agent_graph()

    result = await compiled.ainvoke(_initial_state(), context=deps)

    # The fabricated marker [Doc 99, p.1] never resolves against the
    # citation map, so the Critic must not accept it on the first pass.
    assert call_count["synthesis"] >= 2
    assert result["citation_warning"] is True


@pytest.mark.unit
async def test_insufficient_evidence_verdict_retries_retrieval_at_most_once() -> None:
    call_count = {"critic": 0}

    async def complete(
        messages: list[Message], tier: str, max_tokens: int, tools: object = None
    ) -> LLMResponse:
        system_prompt = messages[0].content
        if "research supervisor" in system_prompt:
            text = "1. Answer the question\nEXTERNAL: no"
        elif "Summarise" in system_prompt:
            text = "A summary with [Doc 1, p.1]."
        elif "fact-checking" in system_prompt:
            text = "ALL SUPPORTED"
        elif "composing the final" in system_prompt:
            text = "Final answer citing [Doc 1, p.1]."
        elif "reviewing a synthesised" in system_prompt:
            call_count["critic"] += 1
            text = "INSUFFICIENT_EVIDENCE: need more sources"
        else:
            text = "ok"
        return LLMResponse(
            text=text, tokens_in=10, tokens_out=10, model_used="test", estimated_cost_usd=0.0
        )

    deps = _base_deps(complete=complete)
    compiled = compile_agent_graph()

    result = await compiled.ainvoke(_initial_state(), context=deps)

    # max_retries=1: the Critic can request one extra retrieval pass, then
    # the run must accept the draft rather than loop forever (design §4.6
    # rule 2: "the cap lives in the state, not in a prompt").
    assert call_count["critic"] == 2
    assert result["final_answer"] == "Final answer citing [Doc 1, p.1]."


@pytest.mark.unit
async def test_a_failed_node_degrades_the_run_instead_of_raising() -> None:
    """Design §4.6 rule 5: "the user sees a partial result with a clear
    notice rather than an opaque error"."""

    async def failing_hybrid_search(**_kwargs: object) -> list[RetrievedChunk]:
        raise RuntimeError("retrieval backend unavailable")

    deps = _base_deps(complete=_happy_path_complete())
    deps.retrieval_service.hybrid_search = failing_hybrid_search  # type: ignore[method-assign]
    compiled = compile_agent_graph()

    result = await compiled.ainvoke(_initial_state(), context=deps)

    assert result["degraded"] is True
    assert "retrieval failed" in result["degraded_reason"].lower()
    assert result["final_answer"]  # never empty — always something useful


@pytest.mark.unit
async def test_a_multi_subtask_request_dispatches_retrieval_per_subtask() -> None:
    """Phase 5 acceptance criteria: a multi-part question "visibly triggers
    multiple agents"."""

    async def complete(
        messages: list[Message], tier: str, max_tokens: int, tools: object = None
    ) -> LLMResponse:
        system_prompt = messages[0].content
        if "research supervisor" in system_prompt:
            text = "1. Summarise approach A\n2. Summarise approach B\nEXTERNAL: no"
        elif "Summarise" in system_prompt:
            text = "A summary with [Doc 1, p.1]."
        elif "fact-checking" in system_prompt:
            text = "ALL SUPPORTED"
        elif "composing the final" in system_prompt:
            text = "Final answer citing [Doc 1, p.1]."
        elif "reviewing a synthesised" in system_prompt:
            text = "APPROVED"
        else:
            text = "ok"
        return LLMResponse(
            text=text, tokens_in=10, tokens_out=10, model_used="test", estimated_cost_usd=0.0
        )

    deps = _base_deps(complete=complete)
    compiled = compile_agent_graph()

    result = await compiled.ainvoke(
        _initial_state("compare approach A and B and identify open gaps"), context=deps
    )

    assert len(result["subtasks"]) == 2
    assert all(task.done for task in result["subtasks"])
    trace_repository: Any = deps.trace_repository
    retrieval_traces = [
        call
        for call in trace_repository.create.await_args_list
        if call.kwargs["agent_name"] == "Retrieval"
    ]
    assert len(retrieval_traces) == 2
