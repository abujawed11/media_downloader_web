"""Storage service for videos and thumbnails (local filesystem or S3-compatible)."""

import os
import re
import shutil
from typing import Optional, Callable
from ..config import settings


def _slugify(text: str, max_len: int = 60) -> str:
    """Convert a title to a URL/filename-safe slug.

    'POCO X8 Pro India Launch, PlayStation 6 Delayed?' → 'POCO-X8-Pro-India-Launch-PlayStation-6-Delayed'
    """
    # Drop non-ASCII characters (handles Hindi, emoji, etc.)
    text = text.encode("ascii", "ignore").decode("ascii")
    # Replace any run of non-alphanumeric chars (except hyphens) with a hyphen
    text = re.sub(r"[^\w]+", "-", text.strip())
    # Collapse multiple hyphens
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:max_len].strip("-")


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

    async def upload_video(
        self,
        local_file_path: str,
        media_id: str,
        progress_callback: Optional[Callable[[int], None]] = None,
        title: Optional[str] = None,
    ) -> str:
        """Upload video file to storage and return the URL/path.

        The stored key format is:  videos/{uuid}_{slug}.ext
        e.g. videos/0c015cac-2b22-4b77-bc08_POCO-X8-Pro-India-Launch.mp4

        progress_callback(percent: int) is called periodically during uploads.
        """
        _, ext = os.path.splitext(local_file_path)
        ext = ext or ".mp4"
        slug = _slugify(title) if title else ""
        object_name = f"{media_id}_{slug}" if slug else media_id
        filename = f"videos/{object_name}{ext}"

        if self.storage_type == "s3":
            file_size = os.path.getsize(local_file_path)
            bytes_done = 0
            last_reported = [-1]  # mutable closure cell

            def _boto3_callback(chunk: int) -> None:
                nonlocal bytes_done
                bytes_done += chunk
                if progress_callback and file_size > 0:
                    percent = min(int(bytes_done / file_size * 100), 99)
                    # Only fire every 5 % to avoid flooding Redis
                    rounded = (percent // 5) * 5
                    if rounded != last_reported[0]:
                        last_reported[0] = rounded
                        progress_callback(rounded)

            self.s3_client.upload_file(
                local_file_path,
                self.bucket_name,
                filename,
                ExtraArgs={"ContentType": "video/mp4"},
                Callback=_boto3_callback,
            )
            if progress_callback:
                progress_callback(100)
            if settings.CDN_URL:
                return f"{settings.CDN_URL.rstrip('/')}/{filename}"
            return f"{settings.S3_ENDPOINT_URL.rstrip('/')}/{self.bucket_name}/{filename}"
        else:
            dest_path = os.path.join(self.local_storage_path, filename)
            # Chunked copy so we can report progress for local storage too
            file_size = os.path.getsize(local_file_path)
            bytes_done = 0
            chunk_size = 4 * 1024 * 1024  # 4 MB
            last_reported = [-1]
            with open(local_file_path, "rb") as src, open(dest_path, "wb") as dst:
                while True:
                    chunk = src.read(chunk_size)
                    if not chunk:
                        break
                    dst.write(chunk)
                    bytes_done += len(chunk)
                    if progress_callback and file_size > 0:
                        percent = min(int(bytes_done / file_size * 100), 99)
                        rounded = (percent // 5) * 5
                        if rounded != last_reported[0]:
                            last_reported[0] = rounded
                            progress_callback(rounded)
            if progress_callback:
                progress_callback(100)
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

    def get_signed_url(
        self,
        file_url: str,
        expiration: int = 3600,
        force_download: bool = False,
        download_filename: Optional[str] = None,
    ) -> str:
        """Generate a signed URL for S3 files (returns original URL for local storage).

        force_download=True adds ResponseContentDisposition: attachment so R2/S3
        sends the file as a download rather than streaming it inline.
        download_filename overrides the filename shown in the browser's save dialog.
        """
        if self.storage_type == "s3":
            key = self._extract_key(file_url)
            params: dict = {"Bucket": self.bucket_name, "Key": key}
            if force_download:
                fname = download_filename or key.split("/")[-1]
                params["ResponseContentDisposition"] = f'attachment; filename="{fname}"'
                params["ResponseContentType"] = "application/octet-stream"
            return self.s3_client.generate_presigned_url(
                "get_object",
                Params=params,
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
