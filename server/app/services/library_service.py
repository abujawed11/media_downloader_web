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
    job_id: Optional[str] = None,
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
        from ..models.database import Base, Media, DownloadJob
        from .storage_service import StorageService
        from sqlalchemy import select
        import asyncio

        _, SyncSession = _get_sync_engine()
        info = yt_info or {}
        media_id = str(uuid.uuid4())

        # ---- Step 1: Create DB record immediately with status="processing" ----
        # This makes the video appear in the Library right away (as "processing")
        # so the user knows it's on its way.
        media = Media(
            id=uuid.UUID(media_id),
            title=title or info.get("title") or "Untitled",
            description=info.get("description"),
            duration=int(info.get("duration") or 0) or None,
            thumbnail_url=_select_thumbnail(info) or "",  # use yt-dlp thumb initially
            video_url="",   # filled in after upload
            file_size=os.path.getsize(filename) if os.path.exists(filename) else None,
            format=ext or info.get("ext"),
            resolution=_extract_resolution(info),
            source_url=url,
            source_platform=_detect_platform(url),
            source_id=info.get("id"),
            uploader=info.get("uploader") or info.get("channel"),
            upload_date=_parse_upload_date(info.get("upload_date")),
            tags=info.get("tags") or [],
            file_status="processing",
        )

        with SyncSession() as session:
            # Check duplicate
            if media.source_id and media.source_platform:
                existing = session.execute(
                    select(Media).where(
                        Media.source_platform == media.source_platform,
                        Media.source_id == media.source_id,
                    )
                ).scalar_one_or_none()
                if existing:
                    logger.info("Media %s/%s already in library (id=%s)",
                                media.source_platform, media.source_id, existing.id)
                    return str(existing.id)

            session.add(media)
            session.commit()
            logger.info("Created processing record %s: %s", media_id, media.title)

        # ---- Step 2: Generate thumbnail ----
        thumbnail_local = ""
        try:
            from .thumbnail_service import ThumbnailService
            thumbnail_local = asyncio.run(ThumbnailService.generate_thumbnail(filename))
        except Exception as exc:
            logger.warning("Thumbnail generation failed: %s", exc)

        # ---- Step 3: Upload video to storage (local copy or R2 upload) ----
        from .redis_pubsub import publish_started, publish_progress, publish_complete, publish_error
        publish_started(media_id, job_id=job_id)  # tells browser to fetch the new processing record

        storage = StorageService()
        logger.info("Uploading video to storage (type=%s)...", storage.storage_type)
        try:
            def _on_progress(percent: int) -> None:
                logger.info("Upload progress %s%%: %s", percent, media_id)
                publish_progress(media_id, percent, job_id=job_id)

            video_url = asyncio.run(storage.upload_video(filename, media_id, progress_callback=_on_progress))
        except Exception as exc:
            logger.error("Failed to upload video to storage: %s", exc)
            publish_error(media_id, job_id=job_id)
            # Mark as error in DB
            with SyncSession() as session:
                m = session.get(Media, uuid.UUID(media_id))
                if m:
                    m.file_status = "error"
                    session.commit()
            return None

        # ---- Step 4: Upload thumbnail ----
        # Only upload thumbnail to R2 if CDN_URL is set (public bucket).
        # Private R2 URLs are not accessible by the browser directly.
        # Without CDN_URL, always use the yt-dlp public thumbnail URL.
        thumbnail_url = ""
        can_upload_thumbnail = (
            storage.storage_type == "local"
            or (storage.storage_type == "s3" and bool(settings.CDN_URL))
        )

        if can_upload_thumbnail and thumbnail_local and os.path.exists(thumbnail_local):
            try:
                thumbnail_url = asyncio.run(storage.upload_thumbnail(thumbnail_local, media_id))
                logger.info("Thumbnail uploaded: %s", thumbnail_url)
            except Exception as exc:
                logger.warning("Failed to upload thumbnail: %s", exc)

        # Always fall back to yt-dlp public thumbnail URL if we have no uploaded one
        if not thumbnail_url:
            thumbnail_url = _select_thumbnail(info) or ""
            if thumbnail_url:
                logger.info("Using yt-dlp thumbnail URL: %s", thumbnail_url)

        # ---- Step 5: Update DB record to "available" with final URLs ----
        with SyncSession() as session:
            m = session.get(Media, uuid.UUID(media_id))
            if m:
                m.video_url = video_url
                m.thumbnail_url = thumbnail_url
                m.file_status = "available"
                session.commit()
                logger.info("Media %s now available at %s", media_id, video_url)

        # Notify browser: upload done, library can refresh
        publish_complete(media_id, job_id=job_id)

        # ---- Step 6: Cleanup temp directory ----
        _cleanup(tmpdir)  # removes the whole temp dir and everything inside

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
