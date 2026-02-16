# Netflix-Style Personal Media Cloud Player - Complete Transformation Plan

**Project:** Media Downloader Web → Personal Media Cloud Library
**Date:** February 17, 2026
**Version:** 1.0
**Purpose:** Transform the current YouTube downloader into a Netflix-like personal media streaming platform

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Vision & Goals](#vision--goals)
4. [Architecture Overview](#architecture-overview)
5. [Technical Stack](#technical-stack)
6. [Database Design](#database-design)
7. [Backend Implementation](#backend-implementation)
8. [Frontend Implementation](#frontend-implementation)
9. [Video Processing & Storage](#video-processing--storage)
10. [Streaming Implementation](#streaming-implementation)
11. [UI/UX Design](#uiux-design)
12. [Implementation Phases](#implementation-phases)
13. [API Specifications](#api-specifications)
14. [Security Considerations](#security-considerations)
15. [Cost Analysis](#cost-analysis)
16. [Testing Strategy](#testing-strategy)
17. [Deployment Guide](#deployment-guide)
18. [Future Enhancements](#future-enhancements)

---

## Executive Summary

### Current Functionality
- User pastes a video URL (YouTube, Instagram, Facebook, Twitter)
- System extracts video info and available formats
- User selects format and downloads video
- File is downloaded to local storage temporarily
- User downloads the file to their computer

### Target Functionality
- User pastes a video URL
- System downloads and stores video in cloud storage
- Video is added to personal media library with metadata
- Netflix-like UI to browse all downloaded videos
- Stream videos directly in browser with custom player
- Track watch progress, organize by collections, search/filter

### Key Benefits
- Personal media cloud accessible from anywhere
- No need to re-download videos
- Beautiful browsing experience like Netflix
- Organized library with search and categories
- Watch progress tracking and resume playback

---

## Current State Analysis

### Existing Tech Stack

**Frontend:**
- React 19.1.1 + TypeScript
- Vite for build tooling
- TailwindCSS for styling
- Zustand for state management
- React Router DOM for routing
- Axios for API calls

**Backend:**
- FastAPI (Python)
- yt-dlp for video extraction/download
- Threading-based job management
- Redis infrastructure (ready but minimal use)
- Cookie-based authentication for platforms

**Current File Structure:**
```
mediadownloader_web/
├── src/                          # Frontend
│   ├── pages/
│   │   ├── Home.tsx             # URL input page
│   │   ├── Downloads.tsx        # Download job list
│   │   └── Settings.tsx
│   ├── components/
│   │   ├── DownloadItem.tsx
│   │   ├── DownloadOptionsModal.tsx
│   │   └── Header.tsx
│   ├── features/downloads/
│   │   ├── downloads.slice.ts   # Zustand store
│   │   └── types.ts
│   └── lib/
│       ├── api.ts
│       └── mediaApi.ts
├── server/                       # Backend
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── routers/
│   │   │   └── media.py         # API endpoints
│   │   ├── services/
│   │   │   ├── ytdlp_service.py
│   │   │   ├── job_manager.py
│   │   │   └── hybrid_job_manager.py
│   │   └── models/
│   │       └── schemas.py
│   └── cookies/                 # Platform auth cookies
```

### Current API Endpoints

```python
POST   /info                     # Get video metadata
GET    /download                 # Direct download (legacy)
POST   /jobs/start              # Start download job
POST   /jobs/{id}/pause         # Pause download
POST   /jobs/{id}/resume        # Resume download
POST   /jobs/{id}/cancel        # Cancel download
GET    /jobs/{id}               # Get job status
GET    /jobs                    # List all jobs
DELETE /jobs/{id}               # Delete job
DELETE /jobs                    # Clear all jobs
GET    /jobs/{id}/file          # Download file
GET    /proxy-image             # Proxy thumbnails
```

### Current Data Flow

1. User pastes URL → Frontend validates
2. Frontend calls `/info` → Backend uses yt-dlp to extract metadata
3. User selects format → Frontend calls `/jobs/start`
4. Backend creates Job object (in-memory)
5. Background thread downloads to temp directory
6. Job status updates via polling
7. When done, user clicks "Open" → Downloads file via `/jobs/{id}/file`
8. Files stored in temp directories, cleaned up manually

### Limitations to Address

1. **No Persistent Storage:** Files in temp directories, jobs in memory
2. **No Media Library:** Can't browse previously downloaded videos
3. **No Streaming:** Must download entire file to watch
4. **No Organization:** No tags, categories, or collections
5. **No Watch Tracking:** Can't resume where you left off
6. **Limited Metadata:** Only basic info stored temporarily
7. **No Search:** Can't search through downloaded content
8. **Memory Loss:** Restart server = lose all download history

---

## Vision & Goals

### Primary Goal
Transform the application from a "download tool" to a "personal Netflix" - a media library where users can:
- Save videos from various platforms to their personal cloud
- Browse their collection with beautiful thumbnails and metadata
- Stream videos directly in browser with professional player
- Organize, search, and filter their media
- Track watch progress and resume playback

### User Stories

**As a user, I want to:**
1. Paste a video URL and have it automatically added to my library
2. See all my saved videos in a beautiful grid layout like Netflix
3. Click on a video thumbnail to watch it instantly
4. Resume watching from where I left off
5. Search my library by title or tags
6. Filter videos by platform (YouTube, Instagram, etc.)
7. Organize videos into collections/playlists
8. Access my library from any device
9. See video details like duration, upload date, source
10. Download the original file if needed

### Success Criteria

**Phase 1 (MVP):**
- ✅ Videos stored persistently (database + cloud/local storage)
- ✅ Library page showing all saved videos with thumbnails
- ✅ Video player page with streaming support
- ✅ Basic search functionality
- ✅ Mobile responsive design

**Phase 2 (Enhanced):**
- ✅ Watch progress tracking and resume
- ✅ Categories and tags
- ✅ Multiple video qualities
- ✅ Collections/playlists
- ✅ Advanced filters

**Phase 3 (Advanced):**
- ✅ Adaptive streaming (HLS)
- ✅ Video transcoding
- ✅ Recommendations
- ✅ Social features (if multi-user)

---

## Architecture Overview

### New System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Add URL │  │ Library  │  │  Player  │  │ Search   │       │
│  │   Page   │  │   Grid   │  │   Page   │  │  Filter  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FASTAPI BACKEND                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Media Router │  │  Auth Router │  │ Stream Router│         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Business Logic                        │  │
│  │  • Download Manager  • Metadata Extractor               │  │
│  │  • Upload Manager    • Thumbnail Generator              │  │
│  │  • Progress Tracker  • Video Processor                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
           │                    │                    │
           │                    │                    │
           ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   PostgreSQL     │  │  Redis (Queue)   │  │  Cloud Storage   │
│                  │  │                  │  │  (S3/R2/Local)   │
│  • media         │  │  • Celery tasks  │  │                  │
│  • collections   │  │  • Job queue     │  │  • Video files   │
│  • tags          │  │  • Cache         │  │  • Thumbnails    │
│  • watch_history │  │                  │  │  • Subtitles     │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

### Component Responsibilities

**Frontend Components:**
1. **Add Media Page:** URL input, format selection (keep current functionality)
2. **Library Page:** Grid of video thumbnails, search bar, filters
3. **Video Player Page:** Full video player with controls, metadata sidebar
4. **Collections Page:** User-created playlists/collections
5. **Search/Filter:** Advanced search and filtering interface

**Backend Services:**
1. **Download Service:** Handles yt-dlp downloads (existing, modified)
2. **Storage Service:** Uploads to S3/local storage
3. **Metadata Service:** Extracts and stores video metadata
4. **Thumbnail Service:** Generates video thumbnails
5. **Streaming Service:** Serves videos with range request support
6. **Progress Service:** Tracks watch progress per user/video

**Background Workers (Celery):**
1. **Download Worker:** Process download jobs
2. **Upload Worker:** Upload completed downloads to cloud
3. **Transcode Worker:** Convert videos to streaming formats (future)
4. **Cleanup Worker:** Remove old temp files

---

## Technical Stack

### Frontend Dependencies (New Additions)

```json
{
  "dependencies": {
    // Existing
    "react": "^19.1.1",
    "react-dom": "^19.1.1",
    "react-router-dom": "^7.8.2",
    "axios": "^1.11.0",
    "zustand": "^5.0.8",
    "zod": "^4.1.0",

    // NEW: Video Player
    "video.js": "^8.10.0",
    "@videojs/themes": "^1.0.1",
    "videojs-contrib-quality-levels": "^3.0.0",

    // OR Alternative: Plyr
    "plyr-react": "^5.3.0",

    // NEW: Data Fetching
    "@tanstack/react-query": "^5.20.0",

    // NEW: UI Enhancements
    "framer-motion": "^11.0.0",
    "react-intersection-observer": "^9.8.0",
    "react-hot-toast": "^2.4.1",

    // NEW: Icons
    "lucide-react": "^0.344.0",

    // NEW: Virtual Scrolling (for large libraries)
    "@tanstack/react-virtual": "^3.1.0"
  }
}
```

### Backend Dependencies (New Additions)

```python
# requirements.txt

# Existing
fastapi==0.109.0
uvicorn[standard]==0.27.0
yt-dlp==2024.1.0
redis==5.0.1
celery==5.3.6

# NEW: Database
sqlalchemy==2.0.25
alembic==1.13.1
psycopg2-binary==2.9.9
asyncpg==0.29.0

# NEW: Cloud Storage
boto3==1.34.34              # AWS S3 / Cloudflare R2
python-multipart==0.0.9     # File uploads

# NEW: Video Processing
ffmpeg-python==0.2.0
pillow==10.2.0

# NEW: Authentication (future)
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9

# NEW: Utilities
python-dotenv==1.0.0
httpx==0.26.0
```

### Infrastructure Requirements

**Development:**
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- FFmpeg (for video processing)

**Production:**
- VPS with 2GB+ RAM (existing)
- PostgreSQL database
- Redis server
- S3-compatible storage (optional)
- Nginx reverse proxy (recommended)

---

## Database Design

### Schema Overview

```sql
-- Media table (main video records)
CREATE TABLE media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Video Information
    title VARCHAR(500) NOT NULL,
    description TEXT,
    duration INTEGER,  -- seconds
    thumbnail_url TEXT,

    -- File Information
    video_url TEXT NOT NULL,  -- S3/CDN URL or local path
    file_size BIGINT,  -- bytes
    format VARCHAR(50),  -- mp4, webm, etc.
    resolution VARCHAR(20),  -- 1080p, 720p, etc.
    codec VARCHAR(50),

    -- Source Information
    source_url TEXT NOT NULL,
    source_platform VARCHAR(50),  -- youtube, instagram, facebook, twitter
    source_id VARCHAR(255),  -- Original video ID from platform
    uploader VARCHAR(255),
    upload_date DATE,

    -- Metadata
    tags TEXT[],  -- Array of tags
    category VARCHAR(100),
    language VARCHAR(10),

    -- System Fields
    added_date TIMESTAMP DEFAULT NOW(),
    modified_date TIMESTAMP DEFAULT NOW(),
    file_status VARCHAR(20) DEFAULT 'processing',  -- processing, available, error

    -- Stats
    view_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,

    CONSTRAINT unique_source UNIQUE(source_platform, source_id)
);

-- Collections (playlists)
CREATE TABLE collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    thumbnail_url TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    created_date TIMESTAMP DEFAULT NOW(),
    modified_date TIMESTAMP DEFAULT NOW()
);

-- Collection Items (many-to-many relationship)
CREATE TABLE collection_items (
    collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,
    media_id UUID REFERENCES media(id) ON DELETE CASCADE,
    position INTEGER,  -- Order in collection
    added_date TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (collection_id, media_id)
);

-- Watch History / Progress Tracking
CREATE TABLE watch_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    media_id UUID REFERENCES media(id) ON DELETE CASCADE,
    user_id UUID,  -- For future multi-user support, NULL for single user

    -- Progress
    current_time INTEGER NOT NULL,  -- seconds
    duration INTEGER NOT NULL,  -- total duration
    progress DECIMAL(5,2),  -- percentage (0-100)
    completed BOOLEAN DEFAULT FALSE,

    -- Timestamps
    started_at TIMESTAMP,
    last_watched TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,

    CONSTRAINT unique_user_media UNIQUE(media_id, user_id)
);

-- Tags (for autocomplete and organization)
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    usage_count INTEGER DEFAULT 0,
    created_date TIMESTAMP DEFAULT NOW()
);

-- Download Jobs (enhanced version of current in-memory jobs)
CREATE TABLE download_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Job Information
    url TEXT NOT NULL,
    format_string VARCHAR(100),
    status VARCHAR(20) NOT NULL,  -- queued, downloading, processing, completed, failed

    -- Progress
    progress DECIMAL(5,2) DEFAULT 0,
    downloaded_bytes BIGINT DEFAULT 0,
    total_bytes BIGINT,
    speed_bps BIGINT,
    eta_seconds INTEGER,

    -- Result
    media_id UUID REFERENCES media(id) ON DELETE SET NULL,
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Metadata
    temp_file_path TEXT,
    metadata JSONB  -- Store original yt-dlp metadata
);

-- Indexes for performance
CREATE INDEX idx_media_added_date ON media(added_date DESC);
CREATE INDEX idx_media_platform ON media(source_platform);
CREATE INDEX idx_media_status ON media(file_status);
CREATE INDEX idx_media_tags ON media USING GIN(tags);
CREATE INDEX idx_watch_progress_media ON watch_progress(media_id);
CREATE INDEX idx_watch_progress_last_watched ON watch_progress(last_watched DESC);
CREATE INDEX idx_download_jobs_status ON download_jobs(status);
CREATE INDEX idx_collection_items_collection ON collection_items(collection_id);

-- Full-text search
CREATE INDEX idx_media_title_search ON media USING GIN(to_tsvector('english', title));
CREATE INDEX idx_media_description_search ON media USING GIN(to_tsvector('english', description));
```

### Database Models (SQLAlchemy)

```python
# server/app/models/database.py

from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Boolean, Text, ARRAY, Float, ForeignKey, Table, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime

Base = declarative_base()

class Media(Base):
    __tablename__ = "media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Video Information
    title = Column(String(500), nullable=False)
    description = Column(Text)
    duration = Column(Integer)
    thumbnail_url = Column(Text)

    # File Information
    video_url = Column(Text, nullable=False)
    file_size = Column(BigInteger)
    format = Column(String(50))
    resolution = Column(String(20))
    codec = Column(String(50))

    # Source Information
    source_url = Column(Text, nullable=False)
    source_platform = Column(String(50))
    source_id = Column(String(255))
    uploader = Column(String(255))
    upload_date = Column(DateTime)

    # Metadata
    tags = Column(ARRAY(String))
    category = Column(String(100))
    language = Column(String(10))

    # System Fields
    added_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    file_status = Column(String(20), default='processing')

    # Stats
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)

    # Relationships
    watch_progress = relationship("WatchProgress", back_populates="media", cascade="all, delete-orphan")
    collection_items = relationship("CollectionItem", back_populates="media", cascade="all, delete-orphan")
    download_job = relationship("DownloadJob", back_populates="media", uselist=False)


class Collection(Base):
    __tablename__ = "collections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    thumbnail_url = Column(Text)
    is_public = Column(Boolean, default=False)
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = relationship("CollectionItem", back_populates="collection", cascade="all, delete-orphan")


class CollectionItem(Base):
    __tablename__ = "collection_items"

    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), primary_key=True)
    position = Column(Integer)
    added_date = Column(DateTime, default=datetime.utcnow)

    # Relationships
    collection = relationship("Collection", back_populates="items")
    media = relationship("Media", back_populates="collection_items")


class WatchProgress(Base):
    __tablename__ = "watch_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True))  # NULL for single user

    # Progress
    current_time = Column(Integer, nullable=False)
    duration = Column(Integer, nullable=False)
    progress = Column(Float)
    completed = Column(Boolean, default=False)

    # Timestamps
    started_at = Column(DateTime)
    last_watched = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    # Relationships
    media = relationship("Media", back_populates="watch_progress")


class DownloadJob(Base):
    __tablename__ = "download_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Job Information
    url = Column(Text, nullable=False)
    format_string = Column(String(100))
    status = Column(String(20), nullable=False)

    # Progress
    progress = Column(Float, default=0)
    downloaded_bytes = Column(BigInteger, default=0)
    total_bytes = Column(BigInteger)
    speed_bps = Column(BigInteger)
    eta_seconds = Column(Integer)

    # Result
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="SET NULL"))
    error_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Metadata
    temp_file_path = Column(Text)
    metadata = Column(JSONB)

    # Relationships
    media = relationship("Media", back_populates="download_job")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    usage_count = Column(Integer, default=0)
    created_date = Column(DateTime, default=datetime.utcnow)
```

### Database Connection Setup

```python
# server/app/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .config import settings
from contextlib import asynccontextmanager

# Database URL from environment
DATABASE_URL = settings.DATABASE_URL
# For async: postgresql+asyncpg://user:pass@host/db
# For sync: postgresql://user:pass@host/db

# Async engine (recommended for FastAPI)
async_engine = create_async_engine(
    DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    pool_size=10,
    max_overflow=20
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency for FastAPI routes
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

---

## Backend Implementation

### Modified Download Flow

```python
# server/app/services/enhanced_job_manager.py

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.database import DownloadJob, Media
from ..services.storage_service import StorageService
from ..services.thumbnail_service import ThumbnailService
from ..services.ytdlp_service import extract_info, _normalize_youtube_url
import yt_dlp
import os
from datetime import datetime

class EnhancedJobManager:
    """
    Enhanced job manager that:
    1. Downloads video to temp storage
    2. Uploads to cloud/persistent storage
    3. Generates thumbnails
    4. Saves metadata to database
    5. Cleans up temp files
    """

    def __init__(self, storage_service: StorageService, db: AsyncSession):
        self.storage = storage_service
        self.db = db

    async def start_download(self, url: str, format_string: str, title: str = None, ext: str = None) -> DownloadJob:
        """
        Start a new download job and save to database
        """
        # Create job in database
        job = DownloadJob(
            id=uuid.uuid4(),
            url=url,
            format_string=format_string,
            status="queued"
        )
        self.db.add(job)
        await self.db.commit()

        # Queue Celery task for background processing
        from ..celery_tasks import process_download_task
        process_download_task.delay(str(job.id))

        return job

    async def process_download(self, job_id: str):
        """
        Background task to process download:
        1. Download video
        2. Upload to storage
        3. Generate thumbnail
        4. Create media record
        5. Cleanup
        """
        job = await self.db.get(DownloadJob, job_id)

        try:
            # Update status
            job.status = "downloading"
            job.started_at = datetime.utcnow()
            await self.db.commit()

            # Step 1: Download video using yt-dlp
            temp_file = await self._download_video(job)

            # Step 2: Extract additional metadata
            metadata = extract_info(job.url)

            # Step 3: Generate thumbnail
            thumbnail_path = await ThumbnailService.generate_thumbnail(temp_file)

            # Step 4: Upload video and thumbnail to storage
            job.status = "uploading"
            await self.db.commit()

            video_url = await self.storage.upload_video(temp_file, job.id)
            thumbnail_url = await self.storage.upload_thumbnail(thumbnail_path, job.id)

            # Step 5: Create media record in database
            media = Media(
                title=metadata.get("title") or job.url,
                description=metadata.get("description"),
                duration=int(metadata.get("duration", 0)),
                thumbnail_url=thumbnail_url,
                video_url=video_url,
                file_size=os.path.getsize(temp_file),
                format=metadata.get("ext"),
                resolution=self._extract_resolution(metadata),
                source_url=job.url,
                source_platform=self._detect_platform(job.url),
                source_id=metadata.get("id"),
                uploader=metadata.get("uploader"),
                upload_date=metadata.get("upload_date"),
                file_status="available"
            )

            self.db.add(media)

            # Update job
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.media_id = media.id
            job.progress = 100

            await self.db.commit()

            # Step 6: Cleanup temp files
            self._cleanup_temp_files(temp_file, thumbnail_path)

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            await self.db.commit()
            raise

    async def _download_video(self, job: DownloadJob) -> str:
        """Download video to temp directory"""
        import tempfile
        tmpdir = tempfile.mkdtemp(prefix=f"job_{job.id}_")

        ydl_opts = {
            "format": job.format_string,
            "outtmpl": os.path.join(tmpdir, "%(title)s.%(ext)s"),
            "progress_hooks": [self._create_progress_hook(job)],
            "merge_output_format": "mp4"
        }

        url = _normalize_youtube_url(job.url)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return info.get("_filename")

    def _create_progress_hook(self, job: DownloadJob):
        """Create progress callback for yt-dlp"""
        async def hook(d):
            if d['status'] == 'downloading':
                job.downloaded_bytes = d.get('downloaded_bytes', 0)
                job.total_bytes = d.get('total_bytes', 0)
                job.speed_bps = d.get('speed', 0)
                job.eta_seconds = d.get('eta', 0)

                if job.total_bytes:
                    job.progress = (job.downloaded_bytes / job.total_bytes) * 100

                await self.db.commit()

        return hook

    def _detect_platform(self, url: str) -> str:
        """Detect platform from URL"""
        url_lower = url.lower()
        if "youtube.com" in url_lower or "youtu.be" in url_lower:
            return "youtube"
        elif "instagram.com" in url_lower:
            return "instagram"
        elif "facebook.com" in url_lower or "fb.watch" in url_lower:
            return "facebook"
        elif "twitter.com" in url_lower or "x.com" in url_lower:
            return "twitter"
        return "other"

    def _extract_resolution(self, metadata: dict) -> str:
        """Extract resolution from metadata"""
        height = metadata.get("height")
        if height:
            return f"{height}p"
        return "unknown"

    def _cleanup_temp_files(self, *files):
        """Delete temporary files"""
        for file in files:
            try:
                if os.path.exists(file):
                    os.remove(file)
            except:
                pass
```

### Storage Service

```python
# server/app/services/storage_service.py

import boto3
from botocore.config import Config
import os
from typing import Optional
from ..config import settings

class StorageService:
    """
    Handles video and thumbnail storage.
    Supports both S3-compatible storage and local filesystem.
    """

    def __init__(self):
        self.storage_type = settings.STORAGE_TYPE  # "s3" or "local"

        if self.storage_type == "s3":
            self.s3_client = boto3.client(
                's3',
                endpoint_url=settings.S3_ENDPOINT_URL,
                aws_access_key_id=settings.S3_ACCESS_KEY_ID,
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
                config=Config(signature_version='s3v4'),
                region_name=settings.S3_REGION
            )
            self.bucket_name = settings.S3_BUCKET_NAME
        else:
            self.local_storage_path = settings.LOCAL_STORAGE_PATH
            os.makedirs(self.local_storage_path, exist_ok=True)

    async def upload_video(self, local_file_path: str, media_id: str) -> str:
        """
        Upload video file to storage and return URL
        """
        filename = f"videos/{media_id}.mp4"

        if self.storage_type == "s3":
            # Upload to S3
            self.s3_client.upload_file(
                local_file_path,
                self.bucket_name,
                filename,
                ExtraArgs={'ContentType': 'video/mp4'}
            )

            # Return CDN URL or S3 URL
            if settings.CDN_URL:
                return f"{settings.CDN_URL}/{filename}"
            else:
                return f"{settings.S3_ENDPOINT_URL}/{self.bucket_name}/{filename}"
        else:
            # Copy to local storage
            import shutil
            dest_path = os.path.join(self.local_storage_path, filename)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(local_file_path, dest_path)

            # Return relative URL (will be served by FastAPI)
            return f"/storage/{filename}"

    async def upload_thumbnail(self, local_file_path: str, media_id: str) -> str:
        """
        Upload thumbnail to storage and return URL
        """
        filename = f"thumbnails/{media_id}.jpg"

        if self.storage_type == "s3":
            self.s3_client.upload_file(
                local_file_path,
                self.bucket_name,
                filename,
                ExtraArgs={'ContentType': 'image/jpeg'}
            )

            if settings.CDN_URL:
                return f"{settings.CDN_URL}/{filename}"
            else:
                return f"{settings.S3_ENDPOINT_URL}/{self.bucket_name}/{filename}"
        else:
            import shutil
            dest_path = os.path.join(self.local_storage_path, filename)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(local_file_path, dest_path)
            return f"/storage/{filename}"

    async def delete_file(self, file_url: str):
        """Delete file from storage"""
        if self.storage_type == "s3":
            # Extract key from URL
            key = file_url.split(f"{self.bucket_name}/")[1]
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
        else:
            # Delete from local storage
            file_path = file_url.replace("/storage/", "")
            full_path = os.path.join(self.local_storage_path, file_path)
            if os.path.exists(full_path):
                os.remove(full_path)

    def get_signed_url(self, file_url: str, expiration: int = 3600) -> str:
        """
        Generate signed URL for private files (S3 only)
        """
        if self.storage_type == "s3":
            key = file_url.split(f"{self.bucket_name}/")[1]
            return self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
        return file_url
```

### Thumbnail Generator

```python
# server/app/services/thumbnail_service.py

import ffmpeg
import os
from typing import Optional

class ThumbnailService:
    """Generate video thumbnails using FFmpeg"""

    @staticmethod
    async def generate_thumbnail(video_path: str, timestamp: float = 1.0) -> str:
        """
        Generate thumbnail from video at specified timestamp
        Returns path to generated thumbnail
        """
        output_path = video_path.rsplit('.', 1)[0] + '_thumb.jpg'

        try:
            # Use ffmpeg to extract frame
            (
                ffmpeg
                .input(video_path, ss=timestamp)
                .filter('scale', 1280, -1)  # Scale to 1280px width, maintain aspect ratio
                .output(output_path, vframes=1, format='image2', vcodec='mjpeg')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

            return output_path
        except ffmpeg.Error as e:
            print(f"Error generating thumbnail: {e.stderr.decode()}")
            raise

    @staticmethod
    async def generate_multiple_thumbnails(video_path: str, count: int = 5) -> list[str]:
        """
        Generate multiple thumbnails at different timestamps
        Useful for timeline preview like Netflix
        """
        try:
            # Get video duration
            probe = ffmpeg.probe(video_path)
            duration = float(probe['streams'][0]['duration'])

            thumbnails = []
            interval = duration / (count + 1)

            for i in range(1, count + 1):
                timestamp = interval * i
                output_path = video_path.rsplit('.', 1)[0] + f'_thumb_{i}.jpg'

                (
                    ffmpeg
                    .input(video_path, ss=timestamp)
                    .filter('scale', 320, -1)
                    .output(output_path, vframes=1, format='image2', vcodec='mjpeg')
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True, quiet=True)
                )

                thumbnails.append(output_path)

            return thumbnails
        except Exception as e:
            print(f"Error generating thumbnails: {str(e)}")
            return []
```

### Celery Tasks

```python
# server/app/celery_tasks.py

from celery import Celery
from .config import settings
from .database import AsyncSessionLocal
from .services.enhanced_job_manager import EnhancedJobManager
from .services.storage_service import StorageService

celery_app = Celery(
    "media_downloader",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

@celery_app.task(name="process_download")
def process_download_task(job_id: str):
    """
    Background task to process video download
    """
    import asyncio

    async def process():
        async with AsyncSessionLocal() as db:
            storage = StorageService()
            manager = EnhancedJobManager(storage, db)
            await manager.process_download(job_id)

    asyncio.run(process())

@celery_app.task(name="cleanup_old_temp_files")
def cleanup_old_temp_files():
    """
    Periodic task to clean up old temporary files
    """
    import os
    import time
    from pathlib import Path

    temp_dir = "/tmp"
    max_age = 86400  # 24 hours

    now = time.time()
    for path in Path(temp_dir).glob("job_*"):
        if path.is_dir():
            age = now - path.stat().st_mtime
            if age > max_age:
                import shutil
                shutil.rmtree(path, ignore_errors=True)

# Schedule periodic tasks
celery_app.conf.beat_schedule = {
    'cleanup-temp-files': {
        'task': 'cleanup_old_temp_files',
        'schedule': 3600.0,  # Every hour
    },
}
```

---

## API Specifications

### New API Endpoints

```python
# server/app/routers/media_library.py

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List, Optional
from ..database import get_db
from ..models.database import Media, Collection, WatchProgress
from ..schemas.media import MediaResponse, MediaListResponse, MediaCreateRequest

router = APIRouter(prefix="/api/media", tags=["media-library"])

# ========== MEDIA ENDPOINTS ==========

@router.post("/add", response_model=MediaResponse, status_code=202)
async def add_media(
    request: MediaCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Start downloading a video and adding it to library
    Returns job status, media will be available when processing completes
    """
    from ..services.enhanced_job_manager import EnhancedJobManager
    from ..services.storage_service import StorageService

    storage = StorageService()
    manager = EnhancedJobManager(storage, db)

    job = await manager.start_download(
        url=request.url,
        format_string=request.format_string,
        title=request.title
    )

    return {
        "id": job.id,
        "status": job.status,
        "message": "Video is being processed and will appear in your library soon"
    }


@router.get("/", response_model=MediaListResponse)
async def list_media(
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=100),
    search: Optional[str] = None,
    platform: Optional[str] = None,
    tag: Optional[str] = None,
    sort_by: str = Query("added_date", regex="^(added_date|title|duration|view_count)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of media in library with filters
    """
    # Build query
    query = select(Media).where(Media.file_status == "available")

    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Media.title.ilike(search_term),
                Media.description.ilike(search_term)
            )
        )

    if platform:
        query = query.where(Media.source_platform == platform)

    if tag:
        query = query.where(Media.tags.contains([tag]))

    # Apply sorting
    sort_column = getattr(Media, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    # Execute
    result = await db.execute(query)
    media_list = result.scalars().all()

    return {
        "items": media_list,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }


@router.get("/{media_id}", response_model=MediaResponse)
async def get_media(
    media_id: str = Path(...),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific media item"""
    media = await db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    # Increment view count
    media.view_count += 1
    await db.commit()

    return media


@router.delete("/{media_id}")
async def delete_media(
    media_id: str = Path(...),
    delete_file: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """Delete media from library (optionally delete file from storage)"""
    media = await db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    # Delete file from storage if requested
    if delete_file:
        from ..services.storage_service import StorageService
        storage = StorageService()
        await storage.delete_file(media.video_url)
        await storage.delete_file(media.thumbnail_url)

    await db.delete(media)
    await db.commit()

    return {"status": "deleted", "media_id": media_id}


# ========== WATCH PROGRESS ENDPOINTS ==========

@router.get("/{media_id}/progress")
async def get_watch_progress(
    media_id: str = Path(...),
    db: AsyncSession = Depends(get_db)
):
    """Get watch progress for a media item"""
    query = select(WatchProgress).where(
        WatchProgress.media_id == media_id,
        WatchProgress.user_id.is_(None)  # Single user for now
    )
    result = await db.execute(query)
    progress = result.scalar_one_or_none()

    if not progress:
        return {"current_time": 0, "progress": 0, "completed": False}

    return progress


@router.put("/{media_id}/progress")
async def update_watch_progress(
    media_id: str = Path(...),
    current_time: int = Query(..., ge=0),
    duration: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db)
):
    """Update watch progress for a media item"""
    # Check if media exists
    media = await db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    # Find or create progress record
    query = select(WatchProgress).where(
        WatchProgress.media_id == media_id,
        WatchProgress.user_id.is_(None)
    )
    result = await db.execute(query)
    progress = result.scalar_one_or_none()

    from datetime import datetime

    if not progress:
        progress = WatchProgress(
            media_id=media_id,
            current_time=current_time,
            duration=duration,
            started_at=datetime.utcnow()
        )
        db.add(progress)
    else:
        progress.current_time = current_time
        progress.duration = duration
        progress.last_watched = datetime.utcnow()

    # Calculate progress percentage
    progress.progress = (current_time / duration) * 100

    # Mark as completed if >95% watched
    if progress.progress >= 95:
        progress.completed = True
        if not progress.completed_at:
            progress.completed_at = datetime.utcnow()

    await db.commit()
    return progress


@router.get("/continue-watching")
async def get_continue_watching(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get list of media to continue watching (not completed, has progress)"""
    query = (
        select(Media)
        .join(WatchProgress)
        .where(
            WatchProgress.completed == False,
            WatchProgress.progress > 5,  # At least 5% watched
            WatchProgress.user_id.is_(None)
        )
        .order_by(WatchProgress.last_watched.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    return result.scalars().all()


# ========== COLLECTION ENDPOINTS ==========

@router.post("/collections", response_model=dict)
async def create_collection(
    name: str,
    description: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Create a new collection/playlist"""
    collection = Collection(name=name, description=description)
    db.add(collection)
    await db.commit()
    return collection


@router.get("/collections")
async def list_collections(db: AsyncSession = Depends(get_db)):
    """List all collections"""
    result = await db.execute(select(Collection))
    return result.scalars().all()


@router.post("/collections/{collection_id}/items")
async def add_to_collection(
    collection_id: str,
    media_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Add media to collection"""
    from ..models.database import CollectionItem

    # Verify collection and media exist
    collection = await db.get(Collection, collection_id)
    media = await db.get(Media, media_id)

    if not collection or not media:
        raise HTTPException(status_code=404, detail="Collection or media not found")

    # Get current max position
    query = select(func.max(CollectionItem.position)).where(
        CollectionItem.collection_id == collection_id
    )
    max_position = await db.scalar(query) or 0

    # Add item
    item = CollectionItem(
        collection_id=collection_id,
        media_id=media_id,
        position=max_position + 1
    )
    db.add(item)
    await db.commit()

    return {"status": "added"}


# ========== STREAMING ENDPOINT ==========

from fastapi import Request
from fastapi.responses import StreamingResponse, FileResponse
import os

@router.get("/{media_id}/stream")
async def stream_media(
    media_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Stream video with HTTP range request support (for seeking)
    """
    media = await db.get(Media, media_id)
    if not media or media.file_status != "available":
        raise HTTPException(status_code=404, detail="Media not available")

    # Get video file path
    from ..services.storage_service import StorageService
    storage = StorageService()

    if storage.storage_type == "local":
        # Serve from local storage with range support
        video_path = media.video_url.replace("/storage/", "")
        full_path = os.path.join(storage.local_storage_path, video_path)

        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="Video file not found")

        # Get file size
        file_size = os.path.getsize(full_path)

        # Parse range header
        range_header = request.headers.get("range")

        if not range_header:
            # No range, return full file
            return FileResponse(
                full_path,
                media_type="video/mp4",
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(file_size)
                }
            )

        # Parse range (format: "bytes=start-end")
        range_match = range_header.replace("bytes=", "").split("-")
        start = int(range_match[0]) if range_match[0] else 0
        end = int(range_match[1]) if len(range_match) > 1 and range_match[1] else file_size - 1

        # Validate range
        if start >= file_size or end >= file_size:
            raise HTTPException(status_code=416, detail="Range not satisfiable")

        # Calculate content length
        content_length = end - start + 1

        # Stream file chunk
        def file_iterator():
            with open(full_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                chunk_size = 8192

                while remaining > 0:
                    read_size = min(chunk_size, remaining)
                    chunk = f.read(read_size)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        return StreamingResponse(
            file_iterator(),
            status_code=206,
            media_type="video/mp4",
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length)
            }
        )

    else:
        # For S3: redirect to signed URL or proxy
        signed_url = storage.get_signed_url(media.video_url)
        from fastapi.responses import RedirectResponse
        return RedirectResponse(signed_url)


# ========== STATS ENDPOINTS ==========

@router.get("/stats/overview")
async def get_library_stats(db: AsyncSession = Depends(get_db)):
    """Get library statistics"""
    # Total media count
    total_media = await db.scalar(
        select(func.count()).select_from(Media).where(Media.file_status == "available")
    )

    # Total storage used
    total_storage = await db.scalar(
        select(func.sum(Media.file_size)).where(Media.file_status == "available")
    )

    # Media by platform
    platform_counts = await db.execute(
        select(Media.source_platform, func.count())
        .where(Media.file_status == "available")
        .group_by(Media.source_platform)
    )

    # Recently added (last 7 days)
    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_count = await db.scalar(
        select(func.count())
        .select_from(Media)
        .where(
            Media.file_status == "available",
            Media.added_date >= week_ago
        )
    )

    return {
        "total_media": total_media,
        "total_storage_bytes": total_storage or 0,
        "total_storage_gb": round((total_storage or 0) / (1024**3), 2),
        "by_platform": dict(platform_counts.all()),
        "added_last_week": recent_count
    }
```

### Pydantic Schemas

```python
# server/app/schemas/media.py

from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class MediaCreateRequest(BaseModel):
    url: HttpUrl
    format_string: str
    title: Optional[str] = None

class MediaResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    duration: Optional[int]
    thumbnail_url: Optional[str]
    video_url: str
    file_size: Optional[int]
    format: Optional[str]
    resolution: Optional[str]
    source_url: str
    source_platform: Optional[str]
    uploader: Optional[str]
    tags: List[str]
    added_date: datetime
    view_count: int

    class Config:
        from_attributes = True

class MediaListResponse(BaseModel):
    items: List[MediaResponse]
    total: int
    page: int
    limit: int
    pages: int

class WatchProgressResponse(BaseModel):
    current_time: int
    duration: int
    progress: float
    completed: bool
    last_watched: datetime

    class Config:
        from_attributes = True
```

---

## Frontend Implementation

### New Pages

#### 1. Library Page (Main Browse)

```tsx
// src/pages/Library.tsx

import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { mediaApi } from '../lib/mediaApi'
import { Search, Filter, Grid, List } from 'lucide-react'

export default function Library() {
  const [search, setSearch] = useState('')
  const [platform, setPlatform] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['media', page, search, platform],
    queryFn: () => mediaApi.listMedia({ page, search, platform })
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">My Library</h1>

        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
            <input
              type="search"
              placeholder="Search videos..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg"
            />
          </div>

          {/* View Toggle */}
          <button
            onClick={() => setViewMode(viewMode === 'grid' ? 'list' : 'grid')}
            className="p-2 hover:bg-white/5 rounded-lg"
          >
            {viewMode === 'grid' ? <List /> : <Grid />}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        <FilterButton active={!platform} onClick={() => setPlatform(null)}>
          All
        </FilterButton>
        <FilterButton active={platform === 'youtube'} onClick={() => setPlatform('youtube')}>
          YouTube
        </FilterButton>
        <FilterButton active={platform === 'instagram'} onClick={() => setPlatform('instagram')}>
          Instagram
        </FilterButton>
        <FilterButton active={platform === 'facebook'} onClick={() => setPlatform('facebook')}>
          Facebook
        </FilterButton>
        <FilterButton active={platform === 'twitter'} onClick={() => setPlatform('twitter')}>
          Twitter
        </FilterButton>
      </div>

      {/* Loading */}
      {isLoading && <LoadingSkeleton />}

      {/* Media Grid */}
      {data && (
        <>
          {viewMode === 'grid' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {data.items.map((media) => (
                <MediaCard key={media.id} media={media} />
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {data.items.map((media) => (
                <MediaListItem key={media.id} media={media} />
              ))}
            </div>
          )}

          {/* Pagination */}
          <Pagination
            current={page}
            total={data.pages}
            onChange={setPage}
          />
        </>
      )}

      {/* Empty State */}
      {data && data.items.length === 0 && (
        <div className="text-center py-20">
          <p className="text-white/60 text-lg">No videos in your library yet.</p>
          <Link to="/" className="btn-primary mt-4">
            Add Your First Video
          </Link>
        </div>
      )}
    </div>
  )
}

// Media Card Component (Netflix-style)
function MediaCard({ media }: { media: any }) {
  const [imageLoaded, setImageLoaded] = useState(false)

  return (
    <Link
      to={`/watch/${media.id}`}
      className="group relative aspect-video rounded-lg overflow-hidden bg-white/5"
    >
      {/* Thumbnail */}
      <img
        src={media.thumbnail_url}
        alt={media.title}
        className={`w-full h-full object-cover transition-all duration-300 group-hover:scale-105 ${
          imageLoaded ? 'opacity-100' : 'opacity-0'
        }`}
        onLoad={() => setImageLoaded(true)}
      />

      {/* Skeleton while loading */}
      {!imageLoaded && (
        <div className="absolute inset-0 animate-pulse bg-white/10" />
      )}

      {/* Overlay on hover */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
        <div className="absolute bottom-0 left-0 right-0 p-4">
          <h3 className="font-semibold line-clamp-2 mb-1">{media.title}</h3>
          <div className="flex items-center gap-2 text-sm text-white/70">
            <span>{formatDuration(media.duration)}</span>
            <span>•</span>
            <span className="capitalize">{media.source_platform}</span>
          </div>
        </div>
      </div>

      {/* Play button */}
      <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
        <div className="w-16 h-16 rounded-full bg-yellow-400 flex items-center justify-center">
          <Play className="w-8 h-8 text-black ml-1" fill="currentColor" />
        </div>
      </div>

      {/* Platform badge */}
      <div className="absolute top-2 right-2 px-2 py-1 rounded bg-black/60 text-xs">
        {media.source_platform}
      </div>
    </Link>
  )
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60

  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  return `${m}:${s.toString().padStart(2, '0')}`
}
```

#### 2. Video Player Page

```tsx
// src/pages/Watch.tsx

import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { mediaApi } from '../lib/mediaApi'
import VideoPlayer from '../components/VideoPlayer'
import { ArrowLeft, Download, Share, Trash } from 'lucide-react'

export default function Watch() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [currentTime, setCurrentTime] = useState(0)

  // Fetch media details
  const { data: media, isLoading } = useQuery({
    queryKey: ['media', id],
    queryFn: () => mediaApi.getMedia(id!)
  })

  // Fetch watch progress
  const { data: progress } = useQuery({
    queryKey: ['progress', id],
    queryFn: () => mediaApi.getWatchProgress(id!)
  })

  // Update progress mutation
  const updateProgress = useMutation({
    mutationFn: (time: number) =>
      mediaApi.updateWatchProgress(id!, time, media!.duration)
  })

  // Save progress periodically
  useEffect(() => {
    if (!media) return

    const interval = setInterval(() => {
      if (currentTime > 0) {
        updateProgress.mutate(currentTime)
      }
    }, 10000) // Save every 10 seconds

    return () => clearInterval(interval)
  }, [currentTime, media])

  if (isLoading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>
  }

  if (!media) {
    return <div className="flex items-center justify-center h-screen">Media not found</div>
  }

  const streamUrl = mediaApi.getStreamUrl(media.id)

  return (
    <div className="min-h-screen bg-black">
      {/* Back button */}
      <button
        onClick={() => navigate('/library')}
        className="absolute top-4 left-4 z-50 p-2 rounded-lg bg-black/50 hover:bg-black/70 transition"
      >
        <ArrowLeft className="w-6 h-6" />
      </button>

      {/* Video Player */}
      <VideoPlayer
        src={streamUrl}
        poster={media.thumbnail_url}
        startTime={progress?.current_time || 0}
        onTimeUpdate={setCurrentTime}
      />

      {/* Video Info */}
      <div className="container mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-[1fr_300px] gap-8">
          {/* Main Info */}
          <div>
            <h1 className="text-3xl font-bold mb-4">{media.title}</h1>

            <div className="flex items-center gap-4 text-white/70 mb-6">
              <span>{formatDuration(media.duration)}</span>
              <span>•</span>
              <span className="capitalize">{media.source_platform}</span>
              <span>•</span>
              <span>{formatDate(media.added_date)}</span>
              <span>•</span>
              <span>{media.view_count} views</span>
            </div>

            {media.description && (
              <div className="bg-white/5 rounded-lg p-4">
                <p className="text-white/80 whitespace-pre-wrap">{media.description}</p>
              </div>
            )}

            {/* Tags */}
            {media.tags && media.tags.length > 0 && (
              <div className="mt-6 flex flex-wrap gap-2">
                {media.tags.map((tag: string) => (
                  <span key={tag} className="px-3 py-1 bg-white/10 rounded-full text-sm">
                    #{tag}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Sidebar Actions */}
          <div className="space-y-3">
            <a
              href={media.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary w-full"
            >
              View Original
            </a>

            <button className="btn-ghost w-full">
              <Download className="w-5 h-5 mr-2" />
              Download
            </button>

            <button className="btn-ghost w-full">
              <Share className="w-5 h-5 mr-2" />
              Share
            </button>

            <button className="btn-ghost w-full text-red-400 hover:bg-red-400/10">
              <Trash className="w-5 h-5 mr-2" />
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function formatDate(date: string): string {
  return new Date(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}
```

#### 3. Video Player Component

```tsx
// src/components/VideoPlayer.tsx

import { useRef, useEffect } from 'react'
import videojs from 'video.js'
import 'video.js/dist/video-js.css'

interface VideoPlayerProps {
  src: string
  poster?: string
  startTime?: number
  onTimeUpdate?: (time: number) => void
}

export default function VideoPlayer({ src, poster, startTime = 0, onTimeUpdate }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const playerRef = useRef<any>(null)

  useEffect(() => {
    if (!videoRef.current) return

    // Initialize Video.js
    const player = videojs(videoRef.current, {
      controls: true,
      fluid: true,
      aspectRatio: '16:9',
      playbackRates: [0.5, 0.75, 1, 1.25, 1.5, 2],
      controlBar: {
        volumePanel: { inline: false },
        pictureInPictureToggle: true,
        fullscreenToggle: true
      }
    })

    playerRef.current = player

    // Set start time
    if (startTime > 0) {
      player.currentTime(startTime)
    }

    // Time update listener
    if (onTimeUpdate) {
      player.on('timeupdate', () => {
        onTimeUpdate(player.currentTime())
      })
    }

    return () => {
      if (player) {
        player.dispose()
      }
    }
  }, [])

  useEffect(() => {
    if (playerRef.current && src) {
      playerRef.current.src({ src, type: 'video/mp4' })
    }
  }, [src])

  return (
    <div className="video-container">
      <video
        ref={videoRef}
        className="video-js vjs-big-play-centered vjs-theme-fantasy"
        poster={poster}
      />
    </div>
  )
}
```

### Updated API Client

```typescript
// src/lib/mediaApi.ts

import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const mediaApi = {
  // Media Library
  listMedia: async (params: {
    page?: number
    search?: string
    platform?: string | null
    tag?: string
  }) => {
    const { data } = await axios.get(`${API_URL}/api/media`, { params })
    return data
  },

  getMedia: async (id: string) => {
    const { data } = await axios.get(`${API_URL}/api/media/${id}`)
    return data
  },

  deleteMedia: async (id: string, deleteFile: boolean = false) => {
    const { data } = await axios.delete(`${API_URL}/api/media/${id}`, {
      params: { delete_file: deleteFile }
    })
    return data
  },

  // Watch Progress
  getWatchProgress: async (id: string) => {
    const { data } = await axios.get(`${API_URL}/api/media/${id}/progress`)
    return data
  },

  updateWatchProgress: async (id: string, currentTime: number, duration: number) => {
    const { data } = await axios.put(
      `${API_URL}/api/media/${id}/progress`,
      null,
      { params: { current_time: currentTime, duration } }
    )
    return data
  },

  getContinueWatching: async () => {
    const { data } = await axios.get(`${API_URL}/api/media/continue-watching`)
    return data
  },

  // Collections
  createCollection: async (name: string, description?: string) => {
    const { data } = await axios.post(`${API_URL}/api/media/collections`, {
      name,
      description
    })
    return data
  },

  listCollections: async () => {
    const { data } = await axios.get(`${API_URL}/api/media/collections`)
    return data
  },

  addToCollection: async (collectionId: string, mediaId: string) => {
    const { data } = await axios.post(
      `${API_URL}/api/media/collections/${collectionId}/items`,
      { media_id: mediaId }
    )
    return data
  },

  // Streaming
  getStreamUrl: (id: string) => {
    return `${API_URL}/api/media/${id}/stream`
  },

  // Stats
  getLibraryStats: async () => {
    const { data} = await axios.get(`${API_URL}/api/media/stats/overview`)
    return data
  }
}
```

### Updated Router

```tsx
// src/app/router.tsx

import { createBrowserRouter } from 'react-router-dom'
import App from '../App'
import Home from '../pages/Home'
import Library from '../pages/Library'
import Watch from '../pages/Watch'
import Downloads from '../pages/Downloads'
import Settings from '../pages/Settings'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Home /> },
      { path: 'library', element: <Library /> },
      { path: 'watch/:id', element: <Watch /> },
      { path: 'downloads', element: <Downloads /> },
      { path: 'settings', element: <Settings /> }
    ]
  }
])
```

---

## Video Processing & Storage

### Configuration

```python
# server/app/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Existing settings...

    # Storage Configuration
    STORAGE_TYPE: str = "local"  # "local" or "s3"
    LOCAL_STORAGE_PATH: str = "./storage"

    # S3/R2 Configuration (if STORAGE_TYPE="s3")
    S3_ENDPOINT_URL: str = ""  # e.g., https://[account-id].r2.cloudflarestorage.com
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = "media-library"
    S3_REGION: str = "auto"
    CDN_URL: str = ""  # Optional CDN URL for faster delivery

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost/media_library"

    class Config:
        env_file = ".env"

settings = Settings()
```

### Environment Variables

```bash
# server/.env

# Storage (choose one)
STORAGE_TYPE=local
LOCAL_STORAGE_PATH=./storage

# OR for S3/R2
# STORAGE_TYPE=s3
# S3_ENDPOINT_URL=https://xxxxx.r2.cloudflarestorage.com
# S3_ACCESS_KEY_ID=your_access_key
# S3_SECRET_ACCESS_KEY=your_secret_key
# S3_BUCKET_NAME=media-library
# CDN_URL=https://cdn.yourdomain.com  # Optional

# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/media_library

# Redis & Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

---

## UI/UX Design

### Design System (TailwindCSS)

```css
/* src/styles/tailwind.css */

@layer base {
  :root {
    --color-primary: #f59e0b;  /* yellow-400 */
    --color-primary-dark: #d97706;
    --color-background: #0a0a0a;
    --color-surface: #1a1a1a;
    --color-surface-hover: #2a2a2a;
  }

  body {
    @apply bg-[#0a0a0a] text-white antialiased;
  }
}

@layer components {
  .btn-primary {
    @apply px-4 py-2 bg-yellow-400 text-black font-semibold rounded-lg
           hover:bg-yellow-500 transition-colors;
  }

  .btn-ghost {
    @apply px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors;
  }

  .card {
    @apply bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl;
  }

  .input {
    @apply w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg
           text-white placeholder-white/40 focus:border-yellow-400
           focus:ring-2 focus:ring-yellow-400/20 outline-none transition;
  }
}

/* Video.js theme customization */
.video-js.vjs-theme-fantasy {
  --vjs-theme-fantasy--primary: #f59e0b;
  --vjs-theme-fantasy--secondary: #1a1a1a;
}
```

### Loading Skeletons

```tsx
// src/components/LoadingSkeleton.tsx

export function MediaGridSkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="animate-pulse">
          <div className="aspect-video bg-white/10 rounded-lg mb-3" />
          <div className="h-4 bg-white/10 rounded w-3/4 mb-2" />
          <div className="h-3 bg-white/10 rounded w-1/2" />
        </div>
      ))}
    </div>
  )
}
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal:** Set up database and storage infrastructure

**Tasks:**
- [ ] Set up PostgreSQL database
- [ ] Create database models and migrations
- [ ] Implement storage service (start with local)
- [ ] Create enhanced job manager
- [ ] Set up Celery workers
- [ ] Update download flow to save to database
- [ ] Test end-to-end download → store → database

**Deliverables:**
- Working database with schema
- Downloads saved to persistent storage
- Media records created in database

---

### Phase 2: Library UI (Week 3)

**Goal:** Build browsing interface

**Tasks:**
- [ ] Create Library page with grid layout
- [ ] Implement media cards with thumbnails
- [ ] Add search functionality
- [ ] Add platform filters
- [ ] Implement pagination
- [ ] Add loading states and skeletons
- [ ] Make responsive for mobile

**Deliverables:**
- Beautiful library grid view
- Working search and filters
- Mobile-responsive design

---

### Phase 3: Video Player (Week 4)

**Goal:** Implement streaming and playback

**Tasks:**
- [ ] Set up Video.js player
- [ ] Implement streaming endpoint with range requests
- [ ] Create Watch page with player
- [ ] Add player controls customization
- [ ] Implement watch progress tracking
- [ ] Add "Continue Watching" section
- [ ] Test seeking and playback

**Deliverables:**
- Working video player
- Streaming with seek support
- Watch progress tracking

---

### Phase 4: Organization (Week 5)

**Goal:** Add collections and organization

**Tasks:**
- [ ] Implement collections/playlists
- [ ] Add tagging system
- [ ] Create collection management UI
- [ ] Add "Add to Collection" modal
- [ ] Implement advanced filters
- [ ] Add sorting options

**Deliverables:**
- Working collections
- Tag management
- Enhanced filtering

---

### Phase 5: Polish & Optimization (Week 6)

**Goal:** Improve UX and performance

**Tasks:**
- [ ] Add animations with Framer Motion
- [ ] Implement virtual scrolling for large libraries
- [ ] Optimize thumbnail generation
- [ ] Add error handling and retry logic
- [ ] Implement proper caching
- [ ] Add toast notifications
- [ ] Performance testing

**Deliverables:**
- Smooth animations
- Fast performance
- Good error handling

---

### Phase 6: Advanced Features (Future)

**Optional enhancements:**
- [ ] Multi-quality video transcoding (HLS)
- [ ] Timeline thumbnail previews
- [ ] Subtitle support
- [ ] Recommendations engine
- [ ] User accounts (multi-user)
- [ ] Chromecast/AirPlay support
- [ ] Mobile apps
- [ ] Social sharing
- [ ] Comments and ratings

---

## Security Considerations

### Authentication (Future Multi-User)

```python
# server/app/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

router = APIRouter(prefix="/auth", tags=["authentication"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SECRET_KEY = "your-secret-key-here"  # Use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Verify user credentials
    user = await verify_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}
```

### Content Security

1. **Validate URLs:** Only allow supported platforms
2. **Rate Limiting:** Prevent abuse
3. **File Size Limits:** Prevent storage overflow
4. **Access Control:** Private libraries by default
5. **HTTPS Only:** For production deployment

### Privacy

1. **No tracking:** User data stays local
2. **No analytics:** Unless explicitly enabled
3. **Private by default:** Not indexable by search engines
4. **Optional sharing:** User controls visibility

---

## Cost Analysis

### Storage Costs (Example: 1TB library)

**Cloudflare R2:**
- Storage: $0.015/GB/month = $15/month
- Egress: $0 (free!)
- Operations: ~$1/month
- **Total: ~$16/month**

**AWS S3 (for comparison):**
- Storage: $0.023/GB/month = $23/month
- Egress: $0.09/GB = $90/month for 1TB streaming
- **Total: ~$113/month**

**Local VPS Storage:**
- Depends on VPS plan
- 1TB SSD storage: ~$10-20/month additional
- No egress fees
- **Total: ~$10-20/month**

### Infrastructure Costs

**Minimal Setup (VPS only):**
- VPS (4GB RAM, 2 CPU): $20/month
- Local storage: Included
- **Total: $20/month**

**Optimal Setup (VPS + R2):**
- VPS (2GB RAM, 1 CPU): $10/month
- Cloudflare R2 (1TB): $16/month
- **Total: $26/month**

### Recommendation
Start with local VPS storage, migrate to R2 when:
- Library exceeds VPS disk space
- Need faster global delivery
- Want to reduce VPS load

---

## Testing Strategy

### Backend Tests

```python
# tests/test_media_api.py

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_add_media():
    response = client.post("/api/media/add", json={
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "format_string": "best",
        "title": "Test Video"
    })
    assert response.status_code == 202
    assert "id" in response.json()

def test_list_media():
    response = client.get("/api/media")
    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()

def test_get_media():
    # First create a media
    create_response = client.post("/api/media/add", json={
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "format_string": "best"
    })
    media_id = create_response.json()["id"]

    # Then get it
    response = client.get(f"/api/media/{media_id}")
    assert response.status_code == 200
    assert response.json()["id"] == media_id
```

### Frontend Tests

```typescript
// src/components/__tests__/MediaCard.test.tsx

import { render, screen } from '@testing-library/react'
import { MediaCard } from '../MediaCard'

test('renders media card', () => {
  const media = {
    id: '1',
    title: 'Test Video',
    thumbnail_url: 'https://example.com/thumb.jpg',
    duration: 300,
    source_platform: 'youtube'
  }

  render(<MediaCard media={media} />)

  expect(screen.getByText('Test Video')).toBeInTheDocument()
  expect(screen.getByText('youtube')).toBeInTheDocument()
})
```

---

## Deployment Guide

### Docker Compose

```yaml
# docker-compose.yml

version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: media_library
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: ./server
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    volumes:
      - ./server:/app
      - ./storage:/app/storage
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/media_library
      - REDIS_URL=redis://redis:6379/0
      - STORAGE_TYPE=local
      - LOCAL_STORAGE_PATH=/app/storage
    depends_on:
      - postgres
      - redis

  celery:
    build: ./server
    command: celery -A app.celery_tasks worker --loglevel=info
    volumes:
      - ./server:/app
      - ./storage:/app/storage
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/media_library
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    depends_on:
      - postgres
      - redis

  frontend:
    build: .
    ports:
      - "5173:5173"
    volumes:
      - ./src:/app/src
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend

volumes:
  postgres_data:
```

### Production Deployment Checklist

- [ ] Set up PostgreSQL database
- [ ] Configure Redis
- [ ] Set up Nginx reverse proxy
- [ ] Enable HTTPS with Let's Encrypt
- [ ] Configure firewall
- [ ] Set up S3/R2 (if using cloud storage)
- [ ] Configure environment variables
- [ ] Set up automatic backups
- [ ] Configure monitoring (optional)
- [ ] Test streaming performance
- [ ] Set up log rotation

---

## Future Enhancements

### Phase 7: Video Transcoding (Advanced)

```python
# server/app/services/transcoding_service.py

import ffmpeg
import os

class TranscodingService:
    """
    Transcode videos to multiple qualities and formats (HLS)
    """

    @staticmethod
    async def transcode_to_hls(input_file: str, output_dir: str):
        """
        Transcode video to HLS with multiple qualities
        Generates .m3u8 playlist and .ts segments
        """
        os.makedirs(output_dir, exist_ok=True)

        qualities = [
            {'height': 1080, 'bitrate': '5000k', 'name': '1080p'},
            {'height': 720, 'bitrate': '3000k', 'name': '720p'},
            {'height': 480, 'bitrate': '1500k', 'name': '480p'},
            {'height': 360, 'bitrate': '800k', 'name': '360p'}
        ]

        for quality in qualities:
            output_path = os.path.join(output_dir, f"{quality['name']}.m3u8")

            (
                ffmpeg
                .input(input_file)
                .output(
                    output_path,
                    format='hls',
                    vcodec='h264',
                    video_bitrate=quality['bitrate'],
                    vf=f"scale=-2:{quality['height']}",
                    hls_time=10,
                    hls_list_size=0,
                    hls_segment_filename=os.path.join(output_dir, f"{quality['name']}_%03d.ts")
                )
                .overwrite_output()
                .run()
            )

        # Create master playlist
        master_playlist = "#EXTM3U\n#EXT-X-VERSION:3\n"
        for quality in qualities:
            bandwidth = int(quality['bitrate'].replace('k', '000'))
            master_playlist += f"#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={quality['height']}x{quality['height']}\n"
            master_playlist += f"{quality['name']}.m3u8\n"

        with open(os.path.join(output_dir, 'master.m3u8'), 'w') as f:
            f.write(master_playlist)
```

### Timeline Thumbnails (Netflix-style)

```python
# Generate sprite sheet for timeline scrubbing
async def generate_timeline_sprites(video_path: str, output_path: str):
    """
    Generate sprite sheet of thumbnails for timeline preview
    """
    # Get video duration
    probe = ffmpeg.probe(video_path)
    duration = float(probe['streams'][0]['duration'])

    # Generate 100 thumbnails
    count = 100
    interval = duration / count

    # Generate thumbnails and combine into sprite sheet
    # ... implementation
```

### Recommendations Engine

```python
# Simple recommendation based on watch history and tags
async def get_recommendations(user_id: str, limit: int = 10):
    """
    Recommend media based on:
    - Watch history
    - Similar tags
    - Same platform
    - Popularity
    """
    # Implementation using collaborative filtering or content-based filtering
```

---

## Migration Guide

### Migrating from Current System

If you have existing downloads, here's how to migrate:

```python
# scripts/migrate_existing_downloads.py

import os
from sqlalchemy.orm import Session
from app.models.database import Media
from app.services.ytdlp_service import extract_info
from app.services.storage_service import StorageService
from app.database import SessionLocal

async def migrate_existing_downloads(downloads_dir: str):
    """
    Migrate existing downloaded files to new system
    """
    db = SessionLocal()
    storage = StorageService()

    for filename in os.listdir(downloads_dir):
        file_path = os.path.join(downloads_dir, filename)

        if not os.path.isfile(file_path):
            continue

        # Try to extract metadata from filename or skip
        print(f"Processing {filename}...")

        # Upload to storage
        video_url = await storage.upload_video(file_path, filename)

        # Create media record (with limited metadata)
        media = Media(
            title=filename,
            video_url=video_url,
            file_size=os.path.getsize(file_path),
            format=filename.split('.')[-1],
            source_url="unknown",
            source_platform="unknown",
            file_status="available"
        )

        db.add(media)
        db.commit()

        print(f"Migrated: {filename}")

    db.close()
```

---

## Monitoring & Maintenance

### Health Checks

```python
# server/app/routers/health.py

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive health check
    """
    checks = {
        "status": "healthy",
        "database": await check_database(db),
        "redis": await check_redis(),
        "storage": await check_storage(),
        "celery": await check_celery()
    }

    if any(not v for v in checks.values() if isinstance(v, bool)):
        checks["status"] = "degraded"

    return checks
```

### Backup Strategy

```bash
#!/bin/bash
# scripts/backup.sh

# Backup PostgreSQL database
pg_dump -U postgres media_library > backup_$(date +%Y%m%d).sql

# Backup storage (if local)
tar -czf storage_backup_$(date +%Y%m%d).tar.gz ./storage

# Upload to S3 (optional)
aws s3 cp backup_$(date +%Y%m%d).sql s3://your-backup-bucket/
```

---

## Conclusion

This comprehensive plan transforms your media downloader into a full-featured personal Netflix-like platform. The implementation is divided into manageable phases, allowing you to:

1. **Start Simple:** Begin with local storage and basic library
2. **Scale Gradually:** Add features incrementally
3. **Migrate Later:** Move to cloud storage when needed
4. **Extend Easily:** Architecture supports future enhancements

**Key Benefits:**
- ✅ Personal media library accessible anywhere
- ✅ Beautiful Netflix-like browsing experience
- ✅ Stream videos without re-downloading
- ✅ Track watch progress and organize content
- ✅ Scalable architecture for growth

**Next Steps:**
1. Review this plan
2. Set up development environment
3. Start with Phase 1 (Database & Storage)
4. Implement phases incrementally
5. Test thoroughly at each phase
6. Deploy and enjoy your personal Netflix!

---

## References & Resources

**Documentation:**
- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://www.sqlalchemy.org/
- React Query: https://tanstack.com/query/latest
- Video.js: https://videojs.com/
- Celery: https://docs.celeryq.dev/

**Services:**
- Cloudflare R2: https://www.cloudflare.com/products/r2/
- PostgreSQL: https://www.postgresql.org/
- Redis: https://redis.io/

**Tools:**
- yt-dlp: https://github.com/yt-dlp/yt-dlp
- FFmpeg: https://ffmpeg.org/

---

**Last Updated:** February 17, 2026
**Version:** 1.0
**Status:** Ready for Implementation
