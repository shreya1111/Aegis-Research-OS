"""Redis-backed run-status cache (design §6.8 "Run status" row, §6.7).

Fast status/progress reads for the trace panel: a run is observable from the
moment it starts, not only once its first ``agent_traces`` row lands. Fails
open on any Redis error, same posture as every other cache in the system
(design §6.8: "a Redis outage degrades performance and cost but never
correctness") — callers fall back to inferring status from ``agent_traces``
when this cache is unavailable.
"""

from __future__ import annotations

import json
from typing import Literal
from uuid import UUID

from redis.asyncio import Redis

from app.core.logging import get_logger

logger = get_logger(__name__)

_PREFIX = "run:"

RunStatusValue = Literal["running", "completed", "failed"]


class AgentRunStatusCache:
    """Typed Redis helper for ``run:{run_id}`` status keys (design §6.8)."""

    def __init__(self, redis: Redis, *, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    async def set_status(
        self, run_id: UUID, status: RunStatusValue, *, detail: str = ""
    ) -> None:
        key = f"{_PREFIX}{run_id}"
        payload = json.dumps({"status": status, "detail": detail})
        try:
            await self._redis.set(key, payload, ex=self._ttl_seconds)
        except Exception:
            logger.warning(
                "agent.run_status.unavailable",
                extra={"event": "agent.run_status.unavailable", "run_id": str(run_id)},
            )

    async def get_status(self, run_id: UUID) -> dict[str, str] | None:
        key = f"{_PREFIX}{run_id}"
        try:
            raw = await self._redis.get(key)
        except Exception:
            logger.warning(
                "agent.run_status.unavailable",
                extra={"event": "agent.run_status.unavailable", "run_id": str(run_id)},
            )
            return None
        if raw is None:
            return None
        try:
            payload = json.loads(raw)
        except ValueError:
            return None
        return {"status": str(payload.get("status", "")), "detail": str(payload.get("detail", ""))}
