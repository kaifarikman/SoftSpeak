from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import MatchmakingQueue
from src.db.session import get_db
from src.services.matchmaking.ws_handler import chat_manager, matchmaking_manager

router = APIRouter(tags=["metrics"])


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(values)
    rank = (len(ordered) - 1) * percentile
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return float(ordered[lower])
    weight = rank - lower
    return float(ordered[lower] * (1 - weight) + ordered[upper] * weight)


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics(session: AsyncSession = Depends(get_db)) -> str:
    now = datetime.now(timezone.utc)
    queue_stmt = select(MatchmakingQueue.joined_at).where(
        MatchmakingQueue.is_searching.is_(True)
    )
    queue_result = await session.execute(queue_stmt)
    joined_at_values = [value for value in queue_result.scalars().all() if value]
    wait_seconds = [
        max(0.0, (now - joined_at).total_seconds())
        for joined_at in joined_at_values
    ]

    active_ws_connections = len(getattr(matchmaking_manager, "active_connections", {}))
    active_ws_connections += sum(
        len(connections)
        for connections in getattr(chat_manager, "chat_connections", {}).values()
    )

    payload = [
        "# HELP softspeak_active_ws_connections Active websocket connections.",
        "# TYPE softspeak_active_ws_connections gauge",
        f"softspeak_active_ws_connections {active_ws_connections}",
        "# HELP softspeak_matchmaking_queue_size Number of users currently searching.",
        "# TYPE softspeak_matchmaking_queue_size gauge",
        f"softspeak_matchmaking_queue_size {len(wait_seconds)}",
        "# HELP softspeak_matchmaking_wait_seconds Matchmaking wait duration in seconds.",
        "# TYPE softspeak_matchmaking_wait_seconds summary",
        f"softspeak_matchmaking_wait_seconds{{quantile=\"0.5\"}} {_percentile(wait_seconds, 0.5):.3f}",
        f"softspeak_matchmaking_wait_seconds{{quantile=\"0.95\"}} {_percentile(wait_seconds, 0.95):.3f}",
        f"softspeak_matchmaking_wait_seconds_sum {sum(wait_seconds):.3f}",
        f"softspeak_matchmaking_wait_seconds_count {len(wait_seconds)}",
    ]
    return "\n".join(payload) + "\n"
