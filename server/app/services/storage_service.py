"""Storage service for videos and thumbnails (local filesystem or S3-compatible)."""

import os
import shutil
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
            import boto3
            from botocore.config import Config

            self.s3_client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT_URL or None,
                aws_access_key_id=settings.S3_ACCESS_KEY_ID,
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
                config=Config(
                    signature_version="s3v4",
                    retries={"max_attempts": 3, "mode": "standard"},
                    connect_timeout=30,
                    read_timeout=300,  # large file uploads need longer timeout
                ),
                region_name=settings.S3_REGION,
                use_ssl=True,
                verify=True,
            )
            self.bucket_name = settings.S3_BUCKET_NAME
        else:
            self.local_storage_path = os.path.abspath(settings.LOCAL_STORAGE_PATH)
            os.makedirs(os.path.join(self.local_storage_path, "videos"), exist_ok=True)
            os.makedirs(os.path.join(self.local_storage_path, "thumbnails"), exist_ok=True)

    async def upload_video(self, local_file_path: str, media_id: str) -> str:
        """Upload video file to storage and return the URL/path."""
        _, ext = os.path.splitext(local_file_path)
        ext = ext or ".mp4"
        filename = f"videos/{media_id}{ext}"

        if self.storage_type == "s3":
            self.s3_client.upload_file(
                local_file_path,
                self.bucket_name,
                filename,
                ExtraArgs={"ContentType": "video/mp4"},
            )
            if settings.CDN_URL:
                return f"{settings.CDN_URL.rstrip('/')}/{filename}"
            return f"{settings.S3_ENDPOINT_URL.rstrip('/')}/{self.bucket_name}/{filename}"
        else:
            dest_path = os.path.join(self.local_storage_path, filename)
            shutil.copy2(local_file_path, dest_path)
            return f"/media-storage/{filename}"

    async def upload_thumbnail(self, local_file_path: str, media_id: str) -> str:
        """Upload thumbnail to storage and return the URL/path."""
        filename = f"thumbnails/{media_id}.jpg"

        if self.storage_type == "s3":
            self.s3_client.upload_file(
                local_file_path,
                self.bucket_name,
                filename,
                ExtraArgs={"ContentType": "image/jpeg"},
            )
            if settings.CDN_URL:
                return f"{settings.CDN_URL.rstrip('/')}/{filename}"
            return f"{settings.S3_ENDPOINT_URL.rstrip('/')}/{self.bucket_name}/{filename}"
        else:
            dest_path = os.path.join(self.local_storage_path, filename)
            shutil.copy2(local_file_path, dest_path)
            return f"/media-storage/{filename}"

    async def delete_file(self, file_url: str):
        """Delete a file from storage."""
        if not file_url:
            return

        if self.storage_type == "s3":
            try:
                key = self._extract_key(file_url)
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            except Exception:
                pass
        else:
            relative = file_url.replace("/media-storage/", "", 1)
            full_path = os.path.join(self.local_storage_path, relative)
            if os.path.exists(full_path):
                os.remove(full_path)

    def get_local_path(self, file_url: str) -> Optional[str]:
        """Convert a /media-storage/ URL to the absolute filesystem path."""
        if self.storage_type != "local":
            return None
        relative = file_url.replace("/media-storage/", "", 1)
        return os.path.join(self.local_storage_path, relative)

    def get_signed_url(self, file_url: str, expiration: int = 3600) -> str:
        """Generate a signed URL for S3 files (returns original URL for local storage)."""
        if self.storage_type == "s3":
            key = self._extract_key(file_url)
            return self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration,
            )
        return file_url

    def _extract_key(self, file_url: str) -> str:
        """
        Extract the S3 object key from a stored URL.
        Works regardless of whether CDN_URL or direct S3 URL was used.
        e.g. 'https://pub-xxx.r2.dev/videos/abc.mp4'  → 'videos/abc.mp4'
             'https://s3.amazonaws.com/bucket/videos/abc.mp4' → 'videos/abc.mp4'
        """
        for prefix in ("/videos/", "/thumbnails/"):
            if prefix in file_url:
                idx = file_url.index(prefix)
                return file_url[idx + 1:]  # strip leading slash → 'videos/abc.mp4'
        # Fallback: everything after the last domain segment
        return file_url.split("/", 3)[-1]
