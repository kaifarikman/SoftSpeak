from collections import defaultdict, deque
from time import monotonic

from fastapi import WebSocket

WINDOW_SECONDS = 60
MAX_CONNECTIONS_PER_WINDOW = 30

_connections: dict[str, deque[float]] = defaultdict(deque)


async def enforce_ws_rate_limit(websocket: WebSocket) -> bool:
    client_host = websocket.client.host if websocket.client else "unknown"
    now = monotonic()
    bucket = _connections[client_host]
    while bucket and now - bucket[0] > WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= MAX_CONNECTIONS_PER_WINDOW:
        await websocket.close(code=4408, reason="Rate limit exceeded")
        return False
    bucket.append(now)
    return True
