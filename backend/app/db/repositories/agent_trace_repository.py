"""Query object for the ``agent_traces`` aggregate (design §6.6, §4.6).

Every agent invocation is recorded here before the node yields (design §4.6
rule 3), so the trace panel is observable even mid-run. Every read requires
``project_id`` (design §9.3 rule 3) — there is no method that returns traces
across projects.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_trace import AgentTrace


class AgentTraceRepository:
    """Persistence for :class:`AgentTrace`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        project_id: UUID,
        run_id: UUID,
        agent_name: str,
        input_summary: str,
        output_summary: str,
        tokens_used: int,
        latency_ms: float,
        estimated_cost: float,
        status: str = "success",
        message_id: UUID | None = None,
    ) -> AgentTrace:
        trace = AgentTrace(
            project_id=project_id,
            run_id=run_id,
            agent_name=agent_name,
            input_summary=input_summary,
            output_summary=output_summary,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            estimated_cost=estimated_cost,
            status=status,
            message_id=message_id,
        )
        self._session.add(trace)
        await self._session.flush()
        return trace

    async def list_for_run(self, run_id: UUID, *, project_id: UUID) -> list[AgentTrace]:
        """Return a run's traces only if the run belongs to ``project_id``
        (design §9.3 rule 4: a run from another project is indistinguishable
        from a run that does not exist)."""
        statement = (
            select(AgentTrace)
            .where(AgentTrace.run_id == run_id, AgentTrace.project_id == project_id)
            .order_by(AgentTrace.created_at)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def summarize_for_project(self, *, project_id: UUID) -> tuple[int, int, int, float]:
        """Aggregate a project's spend for the usage dashboard (Phase 10, FR-H9).

        Returns ``(run_count, trace_count, tokens_used, estimated_cost)``.
        ``run_count`` counts distinct ``run_id``s — one per answered question or
        agent run — which is the "query count" the dashboard reports. The
        aggregation runs in SQL against the ``(project_id, run_id)`` index so a
        large trace table never has to be loaded to show a total.
        """
        statement = select(
            func.count(func.distinct(AgentTrace.run_id)),
            func.count(),
            func.coalesce(func.sum(AgentTrace.tokens_used), 0),
            func.coalesce(func.sum(AgentTrace.estimated_cost), 0.0),
        ).where(AgentTrace.project_id == project_id)
        result = await self._session.execute(statement)
        runs, traces, tokens, cost = result.one()
        return int(runs), int(traces), int(tokens), float(cost)

    async def usage_by_agent(
        self, *, project_id: UUID
    ) -> list[tuple[str, int, int, float]]:
        """Per-agent ``(agent_name, trace_count, tokens, cost)`` for one project."""
        statement = (
            select(
                AgentTrace.agent_name,
                func.count(),
                func.coalesce(func.sum(AgentTrace.tokens_used), 0),
                func.coalesce(func.sum(AgentTrace.estimated_cost), 0.0),
            )
            .where(AgentTrace.project_id == project_id)
            .group_by(AgentTrace.agent_name)
            .order_by(func.sum(AgentTrace.tokens_used).desc())
        )
        result = await self._session.execute(statement)
        return [(row[0], int(row[1]), int(row[2]), float(row[3])) for row in result.all()]

    async def attach_message(self, run_id: UUID, message_id: UUID, *, project_id: UUID) -> None:
        """Retroactively link every trace of a run to its finished message
        (design §7.2: traces exist before the message is finalised)."""
        statement = select(AgentTrace).where(
            AgentTrace.run_id == run_id, AgentTrace.project_id == project_id
        )
        result = await self._session.execute(statement)
        for trace in result.scalars().all():
            trace.message_id = message_id
        await self._session.flush()
