"""
Synchronous library service used by Celery tasks.

Uses sync SQLAlchemy because Celery workers run in sync context.
The DATABASE_URL is expected to be postgresql+asyncpg://...
We derive a sync URL by replacing the driver.
"""

import os
import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from ..config import settings

logger = logging.getLogger(__name__)

# Derive sync URL from async URL
_SYNC_DB_URL = settings.DATABASE_URL.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
).replace(
    "postgresql+asyncio://", "postgresql+psycopg2://"
)

_sync_engine = None
_SyncSession = None


def _get_sync_engine():
    global _sync_engine, _SyncSession
    if _sync_engine is None:
        _sync_engine = create_engine(_SYNC_DB_URL, pool_pre_ping=True)
        _SyncSession = sessionmaker(bind=_sync_engine, expire_on_commit=False)
    return _sync_engine, _SyncSession


def save_completed_download_to_library(
    filename: str,
    tmpdir: str,
    url: str,
    title: Optional[str],
    ext: Optional[str],
    yt_info: Optional[dict] = None,
) -> Optional[str]:
    """
    Move the downloaded file to persistent storage, generate a thumbnail,
    and save a Media record to the database.

    Returns the media UUID string on success, None on failure.
    """
    from ..models.database import Base, Media, DownloadJob
    from .storage_service import StorageService
    import asyncio

    try:
        # Lazy import to avoid circular deps
        _, SyncSession = _get_sync_engine()

        storage = StorageService()

        # ---- Generate thumbnail ----
        thumbnail_local = ""
        try:
            from .thumbnail_service import ThumbnailService
            thumbnail_local = asyncio.run(ThumbnailService.generate_thumbnail(filename))
        except Exception as exc:
            logger.warning("Thumbnail generation failed: %s", exc)

        # ---- Upload video to persistent storage ----
        media_id = str(uuid.uuid4())
        try:
            video_url = asyncio.run(storage.upload_video(filename, media_id))
        except Exception as exc:
            logger.error("Failed to upload video to storage: %s", exc)
            return None

        # ---- Upload thumbnail ----
        thumbnail_url = ""
        if thumbnail_local and os.path.exists(thumbnail_local):
            try:
                thumbnail_url = asyncio.run(storage.upload_thumbnail(thumbnail_local, media_id))
            except Exception as exc:
                logger.warning("Failed to upload thumbnail: %s", exc)

        # ---- Use original thumbnail from yt-dlp if local generation failed ----
        if not thumbnail_url and yt_info:
            thumbnail_url = _select_thumbnail(yt_info) or ""

        # ---- Build media record ----
        info = yt_info or {}
        media = Media(
            id=uuid.UUID(media_id),
            title=title or info.get("title") or "Untitled",
            description=info.get("description"),
            duration=int(info.get("duration") or 0) or None,
            thumbnail_url=thumbnail_url,
            video_url=video_url,
            file_size=os.path.getsize(filename) if os.path.exists(filename) else None,
            format=ext or info.get("ext"),
            resolution=_extract_resolution(info),
            source_url=url,
            source_platform=_detect_platform(url),
            source_id=info.get("id"),
            uploader=info.get("uploader") or info.get("channel"),
            upload_date=_parse_upload_date(info.get("upload_date")),
            tags=info.get("tags") or [],
            file_status="available",
        )

        with SyncSession() as session:
            # Check if same source_id + platform already exists
            if media.source_id and media.source_platform:
                from sqlalchemy import select
                existing = session.execute(
                    select(Media).where(
                        Media.source_platform == media.source_platform,
                        Media.source_id == media.source_id,
                    )
                ).scalar_one_or_none()
                if existing:
                    logger.info(
                        "Media %s/%s already in library (id=%s)",
                        media.source_platform,
                        media.source_id,
                        existing.id,
                    )
                    return str(existing.id)

            session.add(media)
            session.commit()
            logger.info("Saved media %s to library: %s", media_id, media.title)

        # ---- Cleanup temp files ----
        _cleanup(filename, thumbnail_local)

        return media_id

    except Exception as exc:
        logger.exception("save_completed_download_to_library failed: %s", exc)
        return None


# ---- Helpers ----

def _detect_platform(url: str) -> str:
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    if "instagram.com" in url_lower:
        return "instagram"
    if "facebook.com" in url_lower or "fb.watch" in url_lower:
        return "facebook"
    if "twitter.com" in url_lower or "x.com" in url_lower:
        return "twitter"
    if "tiktok.com" in url_lower:
        return "tiktok"
    return "other"


def _extract_resolution(info: dict) -> Optional[str]:
    height = info.get("height")
    if height:
        return f"{height}p"
    return None


def _parse_upload_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y%m%d")
    except Exception:
        return None


def _select_thumbnail(info: dict) -> Optional[str]:
    """Pick the best thumbnail URL from yt-dlp info."""
    thumbnails = info.get("thumbnails") or []
    if thumbnails:
        # Prefer highest resolution
        best = max(thumbnails, key=lambda t: (t.get("width") or 0) * (t.get("height") or 0), default=None)
        if best:
            return best.get("url")
    return info.get("thumbnail")


def _cleanup(*paths: str):
    """Remove temporary files."""
    import shutil
    for path in paths:
        if not path:
            continue
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass
