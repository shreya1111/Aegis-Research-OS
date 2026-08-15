"""The seven core agent nodes (design §4.6).

Each node is a plain async function ``(state, deps) -> partial_state_update``,
LangGraph's standard node shape. Every node's real work is wrapped in
:func:`traced_step` so a trace row exists before the node returns
(design §4.6 rule 3), and every LLM call declares its tier explicitly
(design §4.6 rule 4) — Supervisor/Synthesis/Critic run ``strong``,
Retrieval/Summarizer/Fact-Checker/Memory run ``fast``.
"""

from __future__ import annotations

from app.agents.deps import AgentDeps
from app.agents.state import AgentRunState, Subtask
from app.agents.tools import ExternalSearchInput, HybridSearchInput, external_search, hybrid_search
from app.agents.tracing import traced_step
from app.core.llm.provider import Message
from app.services.retrieval.citation import (
    build_citation_map,
    to_message_citations,
    validate_citations,
)
from app.services.retrieval.types import ExternalSource, RetrievedChunk

_SUPERVISOR_PROMPT = (
    "You are the research supervisor. Decompose the user's research request "
    "into a short numbered list of concrete subtasks (at most {max_subtasks}). "
    "Each subtask should be answerable by retrieving and summarising evidence. "
    "If the request is a single simple question, return exactly one subtask "
    "that restates it. Also decide whether the request plausibly needs "
    "sources beyond the user's uploaded documents (e.g. it asks about "
    "external literature, comparisons to published work, or general "
    "background) — answer with a final line 'EXTERNAL: yes' or "
    "'EXTERNAL: no'. Return only the numbered list followed by that line."
)

_SUMMARIZER_PROMPT = (
    "Summarise the following retrieved material into a concise, factual "
    "paragraph that directly addresses the subtask. Preserve any citation "
    "markers exactly as given (e.g. [Doc 1, p.2])."
)

_FACT_CHECK_PROMPT = (
    "You are fact-checking a summary against its cited sources. For each "
    "claim, confirm whether the cited source actually supports it. List any "
    "unsupported claims on separate lines prefixed with 'UNSUPPORTED:'. If "
    "everything is supported, respond with exactly 'ALL SUPPORTED'."
)

_SYNTHESIS_PROMPT = (
    "You are composing the final research answer from verified, summarised "
    "material below. Write a coherent, well-organised answer that directly "
    "addresses the original request. Cite every claim inline using the "
    "exact markers supplied — never invent a marker. If material is "
    "insufficient for a subtask, say so rather than guessing."
)

_CRITIC_PROMPT = (
    "You are reviewing a synthesised research answer for coherence, "
    "unsupported claims, and completeness against the original request. "
    "If the answer is acceptable, respond with exactly 'APPROVED'. "
    "Otherwise respond with 'REVISE: <reason>' if the writing needs "
    "improvement, or 'INSUFFICIENT_EVIDENCE: <reason>' if more retrieval is "
    "needed."
)


def _parse_subtasks(text: str) -> tuple[list[Subtask], bool]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    needs_external = False
    descriptions: list[str] = []
    for line in lines:
        upper = line.upper()
        if upper.startswith("EXTERNAL:"):
            needs_external = "YES" in upper
            continue
        # Strip a leading "1.", "1)", "-" list marker if present.
        cleaned = line.lstrip("0123456789.)- ").strip()
        if cleaned:
            descriptions.append(cleaned)
    if not descriptions:
        descriptions = [text.strip() or "Answer the request."]
    return [Subtask(description=description) for description in descriptions], needs_external


async def supervisor_node(state: AgentRunState, deps: AgentDeps) -> dict[str, object]:
    """Decompose the request into subtasks and decide external-source need
    (design §4.6 roster: "strong" tier)."""
    subtasks = state.get("subtasks")
    if subtasks is not None:
        # Re-entry after Summarizer: advance to the next undone subtask, or
        # signal the plan is complete.
        next_index = next((i for i, task in enumerate(subtasks) if not task.done), None)
        return {"active_subtask_index": next_index}

    async def work() -> str:
        messages = [
            Message(
                role="system",
                content=_SUPERVISOR_PROMPT.format(max_subtasks=deps.max_subtasks),
            ),
            Message(role="user", content=state["request"]),
        ]
        response = await deps.llm_provider.complete(messages, "strong", 400)
        return response.text

    text = await traced_step(
        deps.trace_repository,
        run_id=state["run_id"],
        project_id=state["project_id"],
        agent_name="Supervisor/Planner",
        input_summary=state["request"],
        work=work,
    )
    new_subtasks, needs_external = _parse_subtasks(text)
    new_subtasks = new_subtasks[: deps.max_subtasks]
    return {
        "subtasks": new_subtasks,
        "active_subtask_index": 0 if new_subtasks else None,
        "needs_external_sources": needs_external,
    }


async def memory_node(state: AgentRunState, deps: AgentDeps) -> dict[str, object]:
    """Load project context before planning proceeds (design §4.6 state
    diagram: "Supervisor --> Memory: load project context")."""

    async def work() -> str:
        return await deps.memory_service.read_digest(
            project_id=state["project_id"], question=state["request"]
        )

    digest = await traced_step(
        deps.trace_repository,
        run_id=state["run_id"],
        project_id=state["project_id"],
        agent_name="Memory",
        input_summary=state["request"],
        work=work,
    )
    return {"memory_digest": digest}


async def retrieval_node(state: AgentRunState, deps: AgentDeps) -> dict[str, object]:
    """Hybrid search for the active subtask, plus external search when the
    Supervisor flagged the request as needing sources beyond the corpus
    (design §4.6 roster: "fast" tier)."""
    subtasks = list(state["subtasks"])
    index = state["active_subtask_index"]
    assert index is not None
    subtask = subtasks[index]

    async def retrieve_internal() -> list[RetrievedChunk]:
        return await hybrid_search(
            HybridSearchInput(query=subtask.description, project_id=state["project_id"]),
            retrieval_service=deps.retrieval_service,
        )

    chunks = await traced_step(
        deps.trace_repository,
        run_id=state["run_id"],
        project_id=state["project_id"],
        agent_name="Retrieval",
        input_summary=subtask.description,
        work=retrieve_internal,
    )
    subtask.retrieved_chunks = chunks

    if state.get("needs_external_sources"):

        async def retrieve_external() -> list[ExternalSource]:
            return await external_search(
                ExternalSearchInput(query=subtask.description),
                external_source_service=deps.external_source_service,
            )

        external_sources = await traced_step(
            deps.trace_repository,
            run_id=state["run_id"],
            project_id=state["project_id"],
            agent_name="Retrieval",
            input_summary=f"external: {subtask.description}",
            work=retrieve_external,
        )
        subtask.external_sources = external_sources

    subtasks[index] = subtask
    return {"subtasks": subtasks}


async def summarizer_node(state: AgentRunState, deps: AgentDeps) -> dict[str, object]:
    """Condense the active subtask's retrieved material (design §4.6 roster:
    "fast" tier)."""
    subtasks = list(state["subtasks"])
    index = state["active_subtask_index"]
    assert index is not None
    subtask = subtasks[index]

    citation_map = build_citation_map(subtask.retrieved_chunks, subtask.external_sources)
    context = "\n\n".join(citation_map.as_context_blocks()) or "(no material retrieved)"

    async def work() -> str:
        messages = [
            Message(role="system", content=_SUMMARIZER_PROMPT),
            Message(
                role="user",
                content=f"Subtask: {subtask.description}\n\nMaterial:\n{context}",
            ),
        ]
        response = await deps.llm_provider.complete(messages, "fast", 500)
        return response.text

    summary = await traced_step(
        deps.trace_repository,
        run_id=state["run_id"],
        project_id=state["project_id"],
        agent_name="Summarizer",
        input_summary=subtask.description,
        work=work,
    )
    subtask.summary = summary
    subtask.done = True
    subtasks[index] = subtask
    return {"subtasks": subtasks}


async def fact_checker_node(state: AgentRunState, deps: AgentDeps) -> dict[str, object]:
    """Verify each subtask summary against its sources and normalise the
    combined citation map (design §4.6 roster: "fast" tier)."""
    all_chunks = [chunk for task in state["subtasks"] for chunk in task.retrieved_chunks]
    all_external = [source for task in state["subtasks"] for source in task.external_sources]
    citation_map = build_citation_map(all_chunks, all_external)

    summaries_block = "\n\n".join(
        f"Subtask: {task.description}\nSummary: {task.summary}" for task in state["subtasks"]
    )

    async def work() -> str:
        messages = [
            Message(role="system", content=_FACT_CHECK_PROMPT),
            Message(role="user", content=summaries_block),
        ]
        response = await deps.llm_provider.complete(messages, "fast", 400)
        return response.text

    result_text = await traced_step(
        deps.trace_repository,
        run_id=state["run_id"],
        project_id=state["project_id"],
        agent_name="Fact-Checker/Citation",
        input_summary="verify subtask summaries",
        work=work,
    )
    flagged = [
        line.removeprefix("UNSUPPORTED:").strip()
        for line in result_text.splitlines()
        if line.strip().upper().startswith("UNSUPPORTED:")
    ]
    return {"citation_map": citation_map, "flagged_claims": flagged}


async def synthesis_node(state: AgentRunState, deps: AgentDeps) -> dict[str, object]:
    """Compose the final answer from verified, summarised material
    (design §4.6 roster: "strong" tier)."""
    summaries_block = "\n\n".join(
        f"Subtask: {task.description}\nSummary: {task.summary}" for task in state["subtasks"]
    )
    citation_map = state["citation_map"]
    context_block = "\n\n".join(citation_map.as_context_blocks())
    flagged = state.get("flagged_claims") or []
    flagged_block = (
        "\n\nThe Fact-Checker flagged these claims as unsupported by the retrieved "
        "sources — do not restate them as fact:\n" + "\n".join(f"- {claim}" for claim in flagged)
        if flagged
        else ""
    )

    async def work() -> str:
        messages = [
            Message(role="system", content=_SYNTHESIS_PROMPT),
            Message(
                role="user",
                content=(
                    f"Original request: {state['request']}\n\n"
                    f"Subtask summaries:\n{summaries_block}\n\n"
                    f"Available sources:\n{context_block}"
                    f"{flagged_block}"
                ),
            ),
        ]
        response = await deps.llm_provider.complete(messages, "strong", 1200)
        return response.text

    draft = await traced_step(
        deps.trace_repository,
        run_id=state["run_id"],
        project_id=state["project_id"],
        agent_name="Synthesis/Report-Writer",
        input_summary=state["request"],
        work=work,
    )
    return {"draft_answer": draft}


async def critic_node(state: AgentRunState, deps: AgentDeps) -> dict[str, object]:
    """Final QA: coherence, unsupported claims, completeness (design §4.6
    roster: "strong" tier). May loop back once via ``synthesis_retry_count``
    or ``retrieval_retry_count`` (design §4.6 rule 2)."""
    draft = state["draft_answer"]

    async def work() -> str:
        messages = [
            Message(role="system", content=_CRITIC_PROMPT),
            Message(
                role="user",
                content=f"Original request: {state['request']}\n\nDraft answer:\n{draft}",
            ),
        ]
        response = await deps.llm_provider.complete(messages, "strong", 300)
        return response.text

    verdict = await traced_step(
        deps.trace_repository,
        run_id=state["run_id"],
        project_id=state["project_id"],
        agent_name="Critic/Reviewer",
        input_summary=draft,
        work=work,
    )

    all_valid, _unresolved = validate_citations(draft, state["citation_map"])
    citations = to_message_citations(draft, state["citation_map"])

    max_retries = state.get("max_retries", deps.max_retries)
    synthesis_retry_count = state.get("synthesis_retry_count", 0)
    retrieval_retry_count = state.get("retrieval_retry_count", 0)

    if not all_valid and synthesis_retry_count < max_retries:
        # Citation validation failure always routes through the same
        # bounded regeneration path as an explicit "REVISE" verdict
        # (design §4.6 rule 2: the cap lives in state, not in a prompt).
        return {
            "critic_verdict": "revise",
            "synthesis_retry_count": synthesis_retry_count + 1,
        }

    is_insufficient = verdict.strip().upper().startswith("INSUFFICIENT_EVIDENCE")
    if is_insufficient and retrieval_retry_count < max_retries:
        # By this point every subtask is marked done (Fact-Checker only runs
        # once the plan is complete), so a retry re-opens the whole plan for
        # another retrieval + summarisation pass rather than resuming a
        # specific subtask index that no longer points anywhere useful.
        reopened_subtasks = [
            Subtask(
                description=task.description,
                retrieved_chunks=task.retrieved_chunks,
                external_sources=task.external_sources,
                summary=task.summary,
                done=False,
            )
            for task in state["subtasks"]
        ]
        return {
            "critic_verdict": "insufficient_evidence",
            "retrieval_retry_count": retrieval_retry_count + 1,
            "subtasks": reopened_subtasks,
            "active_subtask_index": 0 if reopened_subtasks else None,
        }

    if (
        verdict.strip().upper().startswith("REVISE")
        and all_valid
        and synthesis_retry_count < max_retries
    ):
        return {
            "critic_verdict": "revise",
            "synthesis_retry_count": synthesis_retry_count + 1,
        }

    # Either approved outright, or a retry cap was already exhausted — the
    # run accepts the current draft rather than looping forever (design
    # §4.6 rule 2), same graceful-degradation posture as citation warnings
    # in Phase 4.
    return {
        "critic_verdict": "approved",
        "final_answer": draft,
        "citations": citations,
        "citation_warning": not all_valid,
    }


async def memory_write_node(state: AgentRunState, deps: AgentDeps) -> dict[str, object]:
    """Distil durable facts from the approved answer into project memory
    (design §4.6 state diagram: "Critic --> MemoryWrite: approved",
    §4.5 Memory agent contract: "fast" tier)."""

    async def work() -> list[str]:
        return await deps.memory_service.write_facts(
            project_id=state["project_id"],
            answer=state["final_answer"],
            citations=state["citations"],
        )

    await traced_step(
        deps.trace_repository,
        run_id=state["run_id"],
        project_id=state["project_id"],
        agent_name="Memory",
        input_summary="write facts from approved answer",
        work=work,
    )
    return {}
