"""
Sync Redis pub/sub helpers used by the Celery worker to publish upload-progress
events. FastAPI's WebSocket endpoint subscribes to the same channel and streams
the events to connected browsers in real time.
"""
import json
import logging

logger = logging.getLogger(__name__)

CHANNEL = "library:upload_events"

_redis_client = None


def _get_client():
    global _redis_client
    if _redis_client is None:
        import redis
        from ..config import settings
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def publish_started(media_id: str) -> None:
    """Fired once when the processing DB record is created (upload about to begin)."""
    try:
        _get_client().publish(CHANNEL, json.dumps({
            "type": "started",
            "media_id": media_id,
        }))
    except Exception as exc:
        logger.debug("publish_started failed (non-fatal): %s", exc)


def publish_progress(media_id: str, percent: int) -> None:
    try:
        _get_client().publish(CHANNEL, json.dumps({
            "type": "progress",
            "media_id": media_id,
            "percent": percent,
        }))
    except Exception as exc:
        logger.debug("publish_progress failed (non-fatal): %s", exc)


def publish_complete(media_id: str) -> None:
    try:
        _get_client().publish(CHANNEL, json.dumps({
            "type": "complete",
            "media_id": media_id,
        }))
    except Exception as exc:
        logger.debug("publish_complete failed (non-fatal): %s", exc)


def publish_error(media_id: str) -> None:
    try:
        _get_client().publish(CHANNEL, json.dumps({
            "type": "error",
            "media_id": media_id,
        }))
    except Exception as exc:
        logger.debug("publish_error failed (non-fatal): %s", exc)
