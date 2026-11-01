"""Per-project token, cost, and query accounting (Phase 10, FR-H9).

Derived entirely from ``agent_traces``, which every agent invocation has been
writing since Phase 5 — no new instrumentation, and no second source of truth
that could drift from the Reasoning Trace panel.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.db.repositories.agent_trace_repository import AgentTraceRepository


@dataclass(frozen=True, slots=True)
class AgentUsage:
    """One agent's share of a project's spend."""

    agent_name: str
    trace_count: int
    tokens_used: int
    estimated_cost: float


@dataclass(frozen=True, slots=True)
class UsageSummary:
    """A project's total spend plus its per-agent breakdown."""

    run_count: int
    trace_count: int
    tokens_used: int
    estimated_cost: float
    by_agent: list[AgentUsage]


class UsageService:
    """Aggregate a project's recorded agent activity."""

    def __init__(self, *, trace_repository: AgentTraceRepository) -> None:
        self._traces = trace_repository

    async def summary(self, *, project_id: UUID) -> UsageSummary:
        runs, traces, tokens, cost = await self._traces.summarize_for_project(
            project_id=project_id
        )
        by_agent = [
            AgentUsage(
                agent_name=agent_name,
                trace_count=trace_count,
                tokens_used=agent_tokens,
                estimated_cost=agent_cost,
            )
            for agent_name, trace_count, agent_tokens, agent_cost in (
                await self._traces.usage_by_agent(project_id=project_id)
            )
        ]
        return UsageSummary(
            run_count=runs,
            trace_count=traces,
            tokens_used=tokens,
            estimated_cost=round(cost, 6),
            by_agent=by_agent,
        )
