"""Media library API endpoints - CRUD, streaming, watch progress, collections."""

import os
import uuid as _uuid
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc, asc
from pydantic import BaseModel

from ..database import get_db
from ..models.database import Media, Collection, CollectionItem, WatchProgress
from ..services.storage_service import StorageService

router = APIRouter(prefix="/api/library", tags=["media-library"])


# ─────────────────────────── Pydantic schemas ────────────────────────────── #

class MediaOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    duration: Optional[int] = None
    thumbnail_url: Optional[str] = None
    video_url: str
    file_size: Optional[int] = None
    format: Optional[str] = None
    resolution: Optional[str] = None
    source_url: str
    source_platform: Optional[str] = None
    source_id: Optional[str] = None
    uploader: Optional[str] = None
    upload_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    added_date: Optional[datetime] = None
    file_status: str
    view_count: int
    like_count: int

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_safe(cls, obj: Media) -> "MediaOut":
        return cls(
            id=str(obj.id),
            title=obj.title,
            description=obj.description,
            duration=obj.duration,
            thumbnail_url=obj.thumbnail_url,
            video_url=obj.video_url,
            file_size=obj.file_size,
            format=obj.format,
            resolution=obj.resolution,
            source_url=obj.source_url,
            source_platform=obj.source_platform,
            source_id=obj.source_id,
            uploader=obj.uploader,
            upload_date=obj.upload_date,
            tags=obj.tags or [],
            category=obj.category,
            added_date=obj.added_date,
            file_status=obj.file_status,
            view_count=obj.view_count or 0,
            like_count=obj.like_count or 0,
        )


class MediaListOut(BaseModel):
    items: List[MediaOut]
    total: int
    page: int
    limit: int
    pages: int


class WatchProgressOut(BaseModel):
    media_id: str
    current_time: int
    duration: int
    progress: float
    completed: bool
    last_watched: Optional[datetime] = None


class CollectionOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_public: bool
    created_date: Optional[datetime] = None

    class Config:
        from_attributes = True


# ──────────────────────────── Media endpoints ─────────────────────────────── #

@router.get("/", response_model=MediaListOut)
async def list_media(
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=100),
    search: Optional[str] = None,
    platform: Optional[str] = None,
    tag: Optional[str] = None,
    sort_by: str = Query("added_date"),
    sort_order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
):
    """Return a paginated list of media in the library."""
    query = select(Media).where(Media.file_status == "available")

    if search:
        term = f"%{search}%"
        query = query.where(
            or_(Media.title.ilike(term), Media.description.ilike(term))
        )

    if platform:
        query = query.where(Media.source_platform == platform)

    if tag:
        query = query.where(Media.tags.contains([tag]))

    # Sorting
    valid_columns = {"added_date", "title", "duration", "view_count"}
    col_name = sort_by if sort_by in valid_columns else "added_date"
    col = getattr(Media, col_name)
    query = query.order_by(desc(col) if sort_order == "desc" else asc(col))

    # Total count
    count_q = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_q) or 0

    # Paginate
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    items = result.scalars().all()

    return MediaListOut(
        items=[MediaOut.from_orm_safe(m) for m in items],
        total=total,
        page=page,
        limit=limit,
        pages=max(1, (total + limit - 1) // limit),
    )


@router.get("/processing", response_model=List[MediaOut])
async def get_processing(db: AsyncSession = Depends(get_db)):
    """Return videos currently being uploaded/processed."""
    result = await db.execute(
        select(Media)
        .where(Media.file_status.in_(["processing", "error"]))
        .order_by(desc(Media.added_date))
    )
    return [MediaOut.from_orm_safe(m) for m in result.scalars().all()]


@router.get("/continue-watching", response_model=List[MediaOut])
async def get_continue_watching(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Return media items that are in-progress (>5% watched, not completed)."""
    query = (
        select(Media)
        .join(WatchProgress, WatchProgress.media_id == Media.id)
        .where(
            WatchProgress.completed == False,
            WatchProgress.progress > 5,
            WatchProgress.user_id.is_(None),
        )
        .order_by(desc(WatchProgress.last_watched))
        .limit(limit)
    )
    result = await db.execute(query)
    return [MediaOut.from_orm_safe(m) for m in result.scalars().all()]


@router.get("/stats")
async def get_library_stats(db: AsyncSession = Depends(get_db)):
    """Return basic library statistics."""
    total_q = await db.scalar(
        select(func.count(Media.id)).where(Media.file_status == "available")
    )
    size_q = await db.scalar(
        select(func.sum(Media.file_size)).where(Media.file_status == "available")
    )
    platforms_q = await db.execute(
        select(Media.source_platform, func.count(Media.id))
        .where(Media.file_status == "available")
        .group_by(Media.source_platform)
    )
    return {
        "total_videos": total_q or 0,
        "total_size_bytes": size_q or 0,
        "by_platform": {row[0] or "other": row[1] for row in platforms_q.all()},
    }


@router.get("/{media_id}", response_model=MediaOut)
async def get_media(
    media_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
):
    """Get a single media item by ID and increment view count."""
    media = await db.get(Media, _uuid.UUID(media_id))
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    media.view_count = (media.view_count or 0) + 1
    await db.commit()

    return MediaOut.from_orm_safe(media)


@router.delete("/{media_id}")
async def delete_media(
    media_id: str = Path(...),
    delete_file: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """Delete a media item from the library (optionally delete the file too)."""
    media = await db.get(Media, _uuid.UUID(media_id))
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    if delete_file:
        storage = StorageService()
        await storage.delete_file(media.video_url)
        if media.thumbnail_url:
            await storage.delete_file(media.thumbnail_url)

    await db.delete(media)
    await db.commit()
    return {"status": "deleted", "media_id": media_id}


# ──────────────────────────── Streaming endpoint ──────────────────────────── #

@router.get("/{media_id}/stream")
async def stream_media(
    media_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Stream video with HTTP Range request support (enables seeking)."""
    media = await db.get(Media, _uuid.UUID(media_id))
    if not media or media.file_status != "available":
        raise HTTPException(status_code=404, detail="Media not available")

    storage = StorageService()

    if storage.storage_type == "local":
        full_path = storage.get_local_path(media.video_url)
        if not full_path or not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="Video file not found on disk")

        file_size = os.path.getsize(full_path)
        range_header = request.headers.get("range")

        # Detect MIME type
        ext = os.path.splitext(full_path)[1].lower()
        content_type = {
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".mkv": "video/x-matroska",
            ".mov": "video/quicktime",
            ".avi": "video/x-msvideo",
            ".m4v": "video/mp4",
        }.get(ext, "video/mp4")

        if not range_header:
            return FileResponse(
                full_path,
                media_type=content_type,
                headers={"Accept-Ranges": "bytes", "Content-Length": str(file_size)},
            )

        # Parse range header: "bytes=start-end"
        try:
            range_val = range_header.replace("bytes=", "")
            parts = range_val.split("-")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="Invalid Range header")

        if start >= file_size or end >= file_size:
            raise HTTPException(status_code=416, detail="Range Not Satisfiable")

        content_length = end - start + 1
        chunk_size = 1024 * 1024  # 1 MB chunks

        def file_iterator():
            with open(full_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                while remaining > 0:
                    read_size = min(chunk_size, remaining)
                    data = f.read(read_size)
                    if not data:
                        break
                    yield data
                    remaining -= len(data)

        return StreamingResponse(
            file_iterator(),
            status_code=206,
            media_type=content_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
            },
        )
    else:
        # S3: redirect to signed URL
        signed_url = storage.get_signed_url(media.video_url)
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=signed_url)


# ──────────────────────────── Download endpoint ───────────────────────────── #

@router.get("/{media_id}/download")
async def download_media(
    media_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Force-download the video file to the browser.
    Sets Content-Disposition: attachment so it works cross-origin
    (unlike the <a download> attribute which browsers ignore cross-origin).
    """
    media = await db.get(Media, _uuid.UUID(media_id))
    if not media or media.file_status != "available":
        raise HTTPException(status_code=404, detail="Media not available")

    storage = StorageService()

    if storage.storage_type == "local":
        full_path = storage.get_local_path(media.video_url)
        if not full_path or not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="Video file not found on disk")

        # Build a safe filename from the title
        import re
        safe_title = re.sub(r'[^\w\s\-.]', '', media.title or "video")[:80].strip()
        ext = os.path.splitext(full_path)[1] or ".mp4"
        filename = f"{safe_title}{ext}"

        return FileResponse(
            full_path,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(os.path.getsize(full_path)),
            },
        )
    else:
        # S3: redirect to signed URL with Content-Disposition: attachment so the
        # browser downloads the file instead of playing it inline.
        # Use the human-readable title as the filename in the save dialog.
        import re as _re
        safe_title = _re.sub(r'[^\w\s\-]', '', media.title or "video")[:80].strip()
        ext = (media.video_url.rsplit(".", 1)[-1] if "." in media.video_url else "mp4")
        download_filename = f"{safe_title}.{ext}"
        signed_url = storage.get_signed_url(
            media.video_url,
            force_download=True,
            download_filename=download_filename,
        )
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=signed_url)


# ──────────────────────────── Watch progress ──────────────────────────────── #

@router.get("/{media_id}/progress", response_model=WatchProgressOut)
async def get_watch_progress(
    media_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WatchProgress).where(
            WatchProgress.media_id == _uuid.UUID(media_id),
            WatchProgress.user_id.is_(None),
        )
    )
    progress = result.scalar_one_or_none()
    if not progress:
        return WatchProgressOut(
            media_id=media_id,
            current_time=0,
            duration=0,
            progress=0.0,
            completed=False,
        )
    return WatchProgressOut(
        media_id=str(progress.media_id),
        current_time=progress.current_time,
        duration=progress.duration,
        progress=progress.progress or 0.0,
        completed=progress.completed or False,
        last_watched=progress.last_watched,
    )


@router.put("/{media_id}/progress", response_model=WatchProgressOut)
async def update_watch_progress(
    media_id: str = Path(...),
    current_time: int = Query(..., ge=0),
    duration: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
):
    media = await db.get(Media, _uuid.UUID(media_id))
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    result = await db.execute(
        select(WatchProgress).where(
            WatchProgress.media_id == _uuid.UUID(media_id),
            WatchProgress.user_id.is_(None),
        )
    )
    progress = result.scalar_one_or_none()
    now = datetime.utcnow()

    if not progress:
        progress = WatchProgress(
            media_id=_uuid.UUID(media_id),
            current_time=current_time,
            duration=duration,
            started_at=now,
        )
        db.add(progress)
    else:
        progress.current_time = current_time
        progress.duration = duration
        progress.last_watched = now

    progress.progress = (current_time / duration) * 100

    if progress.progress >= 95 and not progress.completed:
        progress.completed = True
        progress.completed_at = now

    await db.commit()

    return WatchProgressOut(
        media_id=str(progress.media_id),
        current_time=progress.current_time,
        duration=progress.duration,
        progress=progress.progress,
        completed=progress.completed,
        last_watched=progress.last_watched,
    )


# ──────────────────────────── Collections ─────────────────────────────────── #

class CollectionCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None


@router.post("/collections", response_model=CollectionOut)
async def create_collection(
    body: CollectionCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    collection = Collection(name=body.name, description=body.description)
    db.add(collection)
    await db.commit()
    return CollectionOut(
        id=str(collection.id),
        name=collection.name,
        description=collection.description,
        is_public=collection.is_public,
        created_date=collection.created_date,
    )


@router.get("/collections", response_model=List[CollectionOut])
async def list_collections(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Collection).order_by(desc(Collection.created_date)))
    return [
        CollectionOut(
            id=str(c.id),
            name=c.name,
            description=c.description,
            thumbnail_url=c.thumbnail_url,
            is_public=c.is_public,
            created_date=c.created_date,
        )
        for c in result.scalars().all()
    ]


@router.post("/collections/{collection_id}/items")
async def add_to_collection(
    collection_id: str,
    media_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    collection = await db.get(Collection, _uuid.UUID(collection_id))
    media = await db.get(Media, _uuid.UUID(media_id))

    if not collection or not media:
        raise HTTPException(status_code=404, detail="Collection or media not found")

    max_pos = await db.scalar(
        select(func.max(CollectionItem.position)).where(
            CollectionItem.collection_id == _uuid.UUID(collection_id)
        )
    ) or 0

    item = CollectionItem(
        collection_id=_uuid.UUID(collection_id),
        media_id=_uuid.UUID(media_id),
        position=max_pos + 1,
    )
    db.add(item)
    await db.commit()
    return {"status": "added"}


@router.delete("/collections/{collection_id}/items/{media_id}")
async def remove_from_collection(
    collection_id: str,
    media_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CollectionItem).where(
            CollectionItem.collection_id == _uuid.UUID(collection_id),
            CollectionItem.media_id == _uuid.UUID(media_id),
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not in collection")
    await db.delete(item)
    await db.commit()
    return {"status": "removed"}
