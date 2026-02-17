"""WebSocket endpoint that streams upload-progress events to the browser.

The Celery worker publishes JSON messages to the Redis channel
``library:upload_events``. This endpoint subscribes to that channel and
forwards every message to all connected WebSocket clients.

Message shapes (JSON):
    {"type": "progress",  "media_id": "<uuid>", "percent": 45}
    {"type": "complete",  "media_id": "<uuid>"}
    {"type": "error",     "media_id": "<uuid>"}
"""
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import settings
from ..services.redis_pubsub import CHANNEL

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/library")
async def library_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("WebSocket client connected")

    import redis.asyncio as aioredis

    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(CHANNEL)

    stop = asyncio.Event()

    async def _redis_to_ws() -> None:
        """Forward every Redis pub/sub message to the WebSocket."""
        try:
            async for message in pubsub.listen():
                if stop.is_set():
                    break
                if message["type"] == "message":
                    await websocket.send_text(message["data"])
        except Exception as exc:
            logger.debug("_redis_to_ws ended: %s", exc)
        finally:
            stop.set()

    async def _ws_receive() -> None:
        """Drain any incoming WebSocket frames (e.g. ping). Exits on disconnect."""
        try:
            while True:
                await websocket.receive_text()
        except (WebSocketDisconnect, Exception) as exc:
            logger.debug("WebSocket client disconnected: %s", exc)
        finally:
            stop.set()

    redis_task = asyncio.create_task(_redis_to_ws())
    ws_task = asyncio.create_task(_ws_receive())

    # Wait until either side closes
    done, pending = await asyncio.wait(
        {redis_task, ws_task},
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    await pubsub.unsubscribe(CHANNEL)
    await redis_client.aclose()
    logger.info("WebSocket client disconnected — cleanup done")
