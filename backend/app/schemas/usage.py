"""Wire contract for the per-project usage dashboard (Phase 10, FR-H9)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.services.usage_service import UsageSummary


class AgentUsageRead(BaseModel):
    """One agent's share of a project's recorded spend."""

    model_config = ConfigDict(frozen=True)

    agent_name: str
    trace_count: int
    tokens_used: int
    estimated_cost: float


class UsageRead(BaseModel):
    """Token, cost, and query totals for one project."""

    model_config = ConfigDict(frozen=True)

    run_count: int
    trace_count: int
    tokens_used: int
    estimated_cost: float
    by_agent: list[AgentUsageRead]

    @classmethod
    def from_summary(cls, summary: UsageSummary) -> UsageRead:
        return cls(
            run_count=summary.run_count,
            trace_count=summary.trace_count,
            tokens_used=summary.tokens_used,
            estimated_cost=summary.estimated_cost,
            by_agent=[
                AgentUsageRead(
                    agent_name=agent.agent_name,
                    trace_count=agent.trace_count,
                    tokens_used=agent.tokens_used,
                    estimated_cost=agent.estimated_cost,
                )
                for agent in summary.by_agent
            ],
        )
