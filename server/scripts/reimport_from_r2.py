"""
Re-import media records from R2 bucket into PostgreSQL.

Run this when your database is empty but files still exist in R2.

Usage:
    cd server
    python -m scripts.reimport_from_r2
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime

# Add server root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import boto3
from botocore.config import Config
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.database import Media, Base


async def reimport():
    # Connect to S3/R2
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL or None,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name=settings.S3_REGION,
    )

    # List all video objects in the bucket
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=settings.S3_BUCKET_NAME, Prefix="videos/")

    video_objects = []
    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.endswith("/"):  # skip folder markers
                video_objects.append(obj)

    print(f"Found {len(video_objects)} video(s) in R2 bucket")

    if not video_objects:
        print("No videos found. Check your R2 credentials and bucket name.")
        return

    # Connect to PostgreSQL
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        for obj in video_objects:
            key = obj["Key"]  # e.g. videos/uuid_slug.mp4
            filename = key.split("/")[-1]  # uuid_slug.mp4
            name_no_ext = filename.rsplit(".", 1)[0]  # uuid_slug

            # Extract UUID from filename (first 36 chars)
            try:
                media_uuid = uuid.UUID(name_no_ext[:36])
            except ValueError:
                # Filename doesn't start with UUID - generate a new one
                media_uuid = uuid.uuid4()

            # Build the URL
            if settings.CDN_URL:
                video_url = f"{settings.CDN_URL.rstrip('/')}/{key}"
            else:
                video_url = f"{settings.S3_ENDPOINT_URL.rstrip('/')}/{settings.S3_BUCKET_NAME}/{key}"

            # Skip if already exists
            existing = await db.get(Media, media_uuid)
            if existing:
                print(f"  SKIP (exists): {filename}")
                continue

            # Extract human-readable title from slug part
            slug_part = name_no_ext[37:] if len(name_no_ext) > 37 else filename  # after uuid_
            title = slug_part.replace("-", " ").strip() or filename

            # Check for a corresponding thumbnail
            thumbnail_url = None
            try:
                thumb_key = f"thumbnails/{media_uuid}.jpg"
                s3.head_object(Bucket=settings.S3_BUCKET_NAME, Key=thumb_key)
                if settings.CDN_URL:
                    thumbnail_url = f"{settings.CDN_URL.rstrip('/')}/{thumb_key}"
                else:
                    thumbnail_url = f"{settings.S3_ENDPOINT_URL.rstrip('/')}/{settings.S3_BUCKET_NAME}/{thumb_key}"
            except Exception:
                pass  # no thumbnail, that's fine

            media = Media(
                id=media_uuid,
                title=title,
                video_url=video_url,
                thumbnail_url=thumbnail_url,
                file_size=obj.get("Size"),
                file_status="available",
                added_date=obj.get("LastModified", datetime.utcnow()).replace(tzinfo=None),
                view_count=0,
                like_count=0,
                source_url="",  # unknown after re-import
            )
            db.add(media)
            print(f"  IMPORT: {title[:60]}")

        await db.commit()

    print("\nDone! Restart your backend and check /library.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(reimport())
