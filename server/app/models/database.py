"""SQLAlchemy database models for the media library."""

from sqlalchemy import (
    Column, String, Integer, BigInteger, DateTime, Boolean,
    Text, Float, ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, DeclarativeBase
import uuid
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Media(Base):
    __tablename__ = "media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Video Information
    title = Column(String(500), nullable=False)
    description = Column(Text)
    duration = Column(Integer)  # seconds
    thumbnail_url = Column(Text)

    # File Information
    video_url = Column(Text, nullable=False)
    file_size = Column(BigInteger)  # bytes
    format = Column(String(50))    # mp4, webm, etc.
    resolution = Column(String(20))  # 1080p, 720p, etc.
    codec = Column(String(50))

    # Source Information
    source_url = Column(Text, nullable=False)
    source_platform = Column(String(50))  # youtube, instagram, facebook, twitter
    source_id = Column(String(255))       # Original video ID from platform
    uploader = Column(String(255))
    upload_date = Column(DateTime)

    # Metadata
    tags = Column(ARRAY(String), default=list)
    category = Column(String(100))
    language = Column(String(10))

    # System Fields
    added_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    file_status = Column(String(20), default="processing")  # processing, available, error

    # Stats
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)

    # Relationships
    watch_progress = relationship("WatchProgress", back_populates="media", cascade="all, delete-orphan")
    collection_items = relationship("CollectionItem", back_populates="media", cascade="all, delete-orphan")
    download_job = relationship("DownloadJob", back_populates="media", uselist=False)

    __table_args__ = (
        UniqueConstraint("source_platform", "source_id", name="unique_source"),
    )


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
    user_id = Column(UUID(as_uuid=True), nullable=True)  # NULL for single-user mode

    # Progress
    current_time = Column(Integer, nullable=False, default=0)  # seconds
    duration = Column(Integer, nullable=False, default=0)      # total duration
    progress = Column(Float, default=0.0)  # percentage (0-100)
    completed = Column(Boolean, default=False)

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    last_watched = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    media = relationship("Media", back_populates="watch_progress")

    __table_args__ = (
        UniqueConstraint("media_id", "user_id", name="unique_user_media"),
    )


class DownloadJob(Base):
    __tablename__ = "download_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Job Information
    url = Column(Text, nullable=False)
    format_string = Column(String(100))
    status = Column(String(20), nullable=False, default="queued")  # queued, downloading, processing, completed, failed

    # Progress
    progress = Column(Float, default=0.0)
    downloaded_bytes = Column(BigInteger, default=0)
    total_bytes = Column(BigInteger, nullable=True)
    speed_bps = Column(BigInteger, nullable=True)
    eta_seconds = Column(Integer, nullable=True)

    # Result
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="SET NULL"), nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Extra data
    temp_file_path = Column(Text, nullable=True)
    yt_metadata = Column(JSONB, nullable=True)

    # Relationships
    media = relationship("Media", back_populates="download_job")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    usage_count = Column(Integer, default=0)
    created_date = Column(DateTime, default=datetime.utcnow)
