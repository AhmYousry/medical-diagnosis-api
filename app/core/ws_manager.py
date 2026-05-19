"""
WebSocket connection manager with Redis pub/sub.

Flow:
  Celery worker (any process) → Redis channel "prediction:{id}"
  FastAPI WS endpoint          → subscribes & streams to browser
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

from fastapi import WebSocket
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "prediction:"


class WebSocketManager:
    """In-process registry of active WebSocket connections."""

    def __init__(self) -> None:
        # prediction_id → set of websockets
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, prediction_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections[prediction_id].add(ws)
        logger.debug("WS connected  prediction=%s total=%d", prediction_id, len(self._connections[prediction_id]))

    def disconnect(self, prediction_id: str, ws: WebSocket) -> None:
        self._connections[prediction_id].discard(ws)
        if not self._connections[prediction_id]:
            del self._connections[prediction_id]
        logger.debug("WS disconnected prediction=%s", prediction_id)

    async def broadcast(self, prediction_id: str, payload: dict) -> None:
        sockets = list(self._connections.get(prediction_id, []))
        if not sockets:
            return
        message = json.dumps(payload)
        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(prediction_id, ws)

    async def listen(self, redis: Redis, prediction_id: str, ws: WebSocket) -> None:
        """Subscribe to Redis channel and forward messages to the WebSocket."""
        channel = f"{CHANNEL_PREFIX}{prediction_id}"
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                data = json.loads(message["data"])
                try:
                    await ws.send_text(json.dumps(data))
                except Exception:
                    break
                # stop listening once terminal state is reached
                if data.get("status") in ("completed", "failed"):
                    break
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()


ws_manager = WebSocketManager()


async def publish_prediction_update(redis: Redis, prediction_id: str, payload: dict) -> None:
    """Called from Celery tasks (via a fresh Redis connection) to push updates."""
    channel = f"{CHANNEL_PREFIX}{prediction_id}"
    await redis.publish(channel, json.dumps(payload))
