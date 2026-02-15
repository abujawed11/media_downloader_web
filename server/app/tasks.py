"""Celery tasks for media downloading."""
import os
import tempfile
import shutil
from typing import Optional
import yt_dlp
from celery import Task
from celery.utils.log import get_task_logger

from .celery_app import celery_app
from .services.ytdlp_service import _cookies_for, _normalize_youtube_url

logger = get_task_logger(__name__)


class DownloadTask(Task):
    """Custom task class with callbacks for progress tracking."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails."""
        logger.error(f"Task {task_id} failed: {exc}")
        # You can add custom failure handling here

    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds."""
        logger.info(f"Task {task_id} completed successfully")


@celery_app.task(bind=True, base=DownloadTask, name="app.tasks.download_media")
def download_media(
    self,
    url: str,
    format_string: str,
    title: Optional[str] = None,
    ext: Optional[str] = None
) -> dict:
    """
    Download media using yt-dlp.

    Args:
        url: Media URL to download
        format_string: Format specification (e.g., "137+140" or "best")
        title: Optional custom title
        ext: Optional file extension

    Returns:
        dict with download results
    """
    task_id = self.request.id
    logger.info(f"Starting download task {task_id} for URL: {url}")

    # Create temporary directory in /app/downloads (Docker volume)
    downloads_dir = "/app/downloads"
    os.makedirs(downloads_dir, exist_ok=True)
    tmpdir = tempfile.mkdtemp(prefix=f"md_{task_id}_", dir=downloads_dir)

    try:
        # Normalize YouTube URLs
        url = _normalize_youtube_url(url)

        # Configure yt-dlp options
        ydl_opts = {
            "format": format_string,
            "outtmpl": os.path.join(tmpdir, "%(title)s.%(ext)s"),
            "continuedl": True,
            "noprogress": False,
            "quiet": False,
            "nocheckcertificate": True,
            "cachedir": False,
            "merge_output_format": "mp4",
            "noplaylist": True,
            "playlist_items": "1",

            # Performance optimizations
            "concurrent_fragments": 16,
            "fragment_retries": 10,
            "file_access_retries": 10,
            "socket_timeout": 60,
            "retries": 10,
            "http_chunk_size": 10485760,  # 10MB chunks
            "buffersize": 8192,
            "throttledratelimit": None,
        }

        # Add cookies if available
        cookies = _cookies_for(url)
        if cookies:
            ydl_opts["cookiefile"] = cookies

        # Progress hook to update task state
        def progress_hook(d):
            if d['status'] == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                speed = d.get('speed', 0)
                eta = d.get('eta', 0)

                if total > 0:
                    progress = (downloaded / total) * 100
                else:
                    progress = 0

                # Update Celery task state
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'status': 'downloading',
                        'progress': progress,
                        'downloaded_bytes': downloaded,
                        'total_bytes': total,
                        'speed_bps': speed,
                        'eta_seconds': eta,
                    }
                )
                logger.info(f"Task {task_id}: {progress:.1f}% complete")

            elif d['status'] == 'finished':
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'status': 'merging',
                        'progress': 95,
                    }
                )
                logger.info(f"Task {task_id}: Download finished, merging...")

        ydl_opts["progress_hooks"] = [progress_hook]

        # Download the media
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # Get the downloaded file path
            filename = None
            if isinstance(info, dict):
                filename = info.get("_filename")

            # If filename not found, search in temp directory
            if not filename or not os.path.isfile(filename):
                import glob
                patterns = ['*.mp4', '*.mkv', '*.webm', '*.avi', '*.mov', '*.m4a', '*.mp3']
                for pattern in patterns:
                    files = glob.glob(os.path.join(tmpdir, pattern))
                    if files:
                        filename = max(files, key=os.path.getsize)
                        break

            if not filename or not os.path.isfile(filename):
                raise RuntimeError("Download completed but file not found")

            file_size = os.path.getsize(filename)

            logger.info(f"Task {task_id}: Download complete - {filename} ({file_size} bytes)")

            return {
                'status': 'done',
                'filename': filename,
                'tmpdir': tmpdir,
                'title': title or info.get('title', 'Unknown'),
                'ext': ext or os.path.splitext(filename)[1].lstrip('.'),
                'file_size': file_size,
            }

    except Exception as e:
        logger.error(f"Task {task_id} failed: {str(e)}")
        # Clean up on error
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except:
            pass
        raise
