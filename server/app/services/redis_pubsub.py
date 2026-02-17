"""
Sync Redis pub/sub helpers used by the Celery worker to publish upload-progress
events. FastAPI's WebSocket endpoint subscribes to the same channel and streams
the events to connected browsers in real time.

Every event optionally carries ``job_id`` (the Celery download task ID) so the
Uploads page can correlate Phase-2 cloud-upload progress back to the job row.
"""
import json
import logging
from typing import Optional

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


def _pub(payload: dict) -> None:
    try:
        _get_client().publish(CHANNEL, json.dumps(payload))
    except Exception as exc:
        logger.debug("publish failed (non-fatal): %s", exc)


def publish_started(media_id: str, job_id: Optional[str] = None) -> None:
    """Fired once when the processing DB record is created (upload about to begin)."""
    msg = {"type": "started", "media_id": media_id}
    if job_id:
        msg["job_id"] = job_id
    _pub(msg)


def publish_progress(media_id: str, percent: int, job_id: Optional[str] = None) -> None:
    msg = {"type": "progress", "media_id": media_id, "percent": percent}
    if job_id:
        msg["job_id"] = job_id
    _pub(msg)


def publish_complete(media_id: str, job_id: Optional[str] = None) -> None:
    msg = {"type": "complete", "media_id": media_id}
    if job_id:
        msg["job_id"] = job_id
    _pub(msg)


def publish_error(media_id: str, job_id: Optional[str] = None) -> None:
    msg = {"type": "error", "media_id": media_id}
    if job_id:
        msg["job_id"] = job_id
    _pub(msg)
