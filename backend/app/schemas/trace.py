"""Wire contracts for the agent reasoning trace endpoint (design §6.1, §4.6)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.models.agent_trace import AgentTrace


class TraceStepRead(BaseModel):
    """One agent-node invocation, rendered for the trace panel (design §5.7)."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    agent_name: str
    input_summary: str
    output_summary: str
    tokens_used: int
    latency_ms: float
    estimated_cost: float
    status: str
    created_at: datetime

    @classmethod
    def from_model(cls, trace: AgentTrace) -> TraceStepRead:
        return cls(
            id=trace.id,
            agent_name=trace.agent_name,
            input_summary=trace.input_summary,
            output_summary=trace.output_summary,
            tokens_used=trace.tokens_used,
            latency_ms=trace.latency_ms,
            estimated_cost=trace.estimated_cost,
            status=trace.status,
            created_at=trace.created_at,
        )


class TraceRunRead(BaseModel):
    """Ordered trace for one run (design: ``GET /projects/{id}/traces/{run_id}``)."""

    model_config = ConfigDict(frozen=True)

    run_id: UUID
    steps: list[TraceStepRead]
