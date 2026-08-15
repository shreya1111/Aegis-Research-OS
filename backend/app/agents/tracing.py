"""Shared trace-writing helper for agent nodes (design §4.6 rule 3).

Every node calls :func:`traced_step` around its actual work so a
``agent_traces`` row is written before the node yields, regardless of which
node it is — this is what makes the trace panel a live, ordered feed rather
than something assembled only at the end of a run.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import TypeVar
from uuid import UUID

from app.db.repositories.agent_trace_repository import AgentTraceRepository

_T = TypeVar("_T")


async def traced_step(
    trace_repository: AgentTraceRepository,
    *,
    run_id: UUID,
    project_id: UUID,
    agent_name: str,
    input_summary: str,
    work: Callable[[], Awaitable[_T]],
    summarise_output: Callable[[_T], str] | None = None,
) -> _T:
    """Run ``work`` and write its trace row before returning the result.

    A failed step still yields a trace row marked ``failed`` and re-raises,
    so the caller can decide how the run degrades (design §4.6 rule 5).
    """
    started = time.monotonic()
    try:
        result = await work()
    except Exception:
        latency_ms = (time.monotonic() - started) * 1000
        await trace_repository.create(
            project_id=project_id,
            run_id=run_id,
            agent_name=agent_name,
            input_summary=input_summary[:500],
            output_summary="",
            tokens_used=0,
            latency_ms=latency_ms,
            estimated_cost=0.0,
            status="failed",
        )
        raise

    latency_ms = (time.monotonic() - started) * 1000
    if summarise_output is not None:
        output_summary = summarise_output(result)
    elif isinstance(result, list):
        output_summary = f"{len(result)} items"
    else:
        output_summary = str(result)[:500]

    await trace_repository.create(
        project_id=project_id,
        run_id=run_id,
        agent_name=agent_name,
        input_summary=input_summary[:500],
        output_summary=output_summary[:500],
        tokens_used=0,
        latency_ms=latency_ms,
        estimated_cost=0.0,
        status="success",
    )
    return result
