# server/app/services/job_manager.py
import os, tempfile, threading, uuid, time, shutil
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional
import yt_dlp

from .ytdlp_service import _cookies_for  # reuse your cookies helper
from .ytdlp_service import _normalize_youtube_url  # normalize YT watch URLs to single video
from ..config import settings

# Use persistent downloads directory from config or fallback to ./downloads
# Convert to absolute path to handle both Docker and local environments
DOWNLOADS_DIR = os.path.abspath(getattr(settings, 'YTDLP_OUTPUT_PATH', './downloads'))
# Ensure the directory exists
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
print(f"[INFO] Job manager using downloads directory: {DOWNLOADS_DIR}")

@dataclass
class Job:
    id: str
    url: str
    format_string: str
    title: Optional[str] = None
    ext: Optional[str] = None
    status: str = "queued"              # queued|downloading|paused|merging|done|error|canceled
    progress: float = 0.0               # 0..1
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    speed_bps: Optional[float] = None
    eta_seconds: Optional[int] = None
    filename: Optional[str] = None
    tmpdir: str = field(default_factory=lambda: "")  # Will be set in __post_init__
    error: Optional[str] = None

    # control flags
    _pause_req: bool = False
    _cancel_req: bool = False

    def __post_init__(self):
        """Create tmpdir in persistent downloads directory."""
        if not self.tmpdir:
            self.tmpdir = tempfile.mkdtemp(prefix=f"mdjob_{self.id}_", dir=DOWNLOADS_DIR)

# in-memory store
_JOBS: Dict[str, Job] = {}
_LOCK = threading.Lock()

class _StopForPause(Exception): pass
class _StopForCancel(Exception): pass

def _ydl_opts_for(job: Job):
    # Prefer mp4 container if codecs allow
    opts = {
        "format": job.format_string,
        "outtmpl": os.path.join(job.tmpdir, "%(title)s.%(ext)s"),
        "continuedl": True,
        "noprogress": False,
        "quiet": True,
        "nocheckcertificate": True,
        "cachedir": False,
        "merge_output_format": "mp4",
        # Ensure we don't enumerate entire playlists when a watch URL has &list=
        "noplaylist": True,
        "playlist_items": "1",
        # Performance optimizations
        "concurrent_fragments": 16,        # Increased from 8 to 16 for faster parallel downloads
        "fragment_retries": 10,            # More retries for unstable connections
        "file_access_retries": 10,
        "socket_timeout": 60,              # Longer timeout for large files
        "retries": 10,                     # More retries for reliability
        "http_chunk_size": 10485760,       # 10MB chunks for better throughput
        "buffersize": 8192,                # Larger buffer size
        "throttledratelimit": None,        # No rate limit (use full bandwidth)
    }
    cookies = _cookies_for(job.url)
    if cookies:
        opts["cookiefile"] = cookies
    return opts

def _progress_hook(job: Job):
    def hook(d):
        # d['status'] in {'downloading','finished'}
        with _LOCK:
            if job._cancel_req: raise _StopForCancel()
            if job._pause_req:  raise _StopForPause()

            st = d.get("status")
            if st == "downloading":
                job.status = "downloading"
                
                # Use yt-dlp's reported values directly - they handle multi-stream progress correctly
                job.downloaded_bytes = int(d.get("downloaded_bytes") or 0)
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                if total:
                    job.total_bytes = int(total)
                
                # Calculate progress based on current values
                if job.total_bytes and job.total_bytes > 0:
                    job.progress = max(0.0, min(1.0, job.downloaded_bytes / job.total_bytes))
                
                job.speed_bps = d.get("speed") or None
                job.eta_seconds = int(d.get("eta")) if d.get("eta") is not None else None
                fn = d.get("filename") or d.get("tmpfilename")
                if fn: job.filename = fn
            elif st == "finished":
                job.status = "merging"  # yt-dlp is about to post-process
                # Don't update size during merge - keep the last download size
                # The final size will be set after yt-dlp completes
                fn = d.get("filename")
                if fn: job.filename = fn
    return hook

def _run_job(job: Job):
    try:
        ydl_opts = _ydl_opts_for(job)
        ydl_opts["progress_hooks"] = [_progress_hook(job)]
        # Normalize YouTube URLs so a watch URL with playlist params doesn't trigger full playlist
        url = _normalize_youtube_url(job.url)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # best guess at final filename
            if isinstance(info, dict):
                fn = info.get("_filename") or job.filename
                if fn: job.filename = fn
        with _LOCK:
            job.status = "done"
            job.progress = 1.0
            job.speed_bps = 0
            job.eta_seconds = 0
            
            # Update final file size from actual downloaded file
            final_file_found = False
            
            # Try the recorded filename first
            if job.filename and os.path.isfile(job.filename):
                final_size = os.path.getsize(job.filename)
                print(f"[DEBUG] Final file found: {job.filename}, Size: {final_size} bytes")
                job.downloaded_bytes = final_size
                job.total_bytes = final_size
                final_file_found = True
            else:
                # Search for any video file in the temp directory (merged file)
                import glob
                if hasattr(job, 'tmpdir') and job.tmpdir and os.path.isdir(job.tmpdir):
                    # Look for common video extensions
                    patterns = ['*.mp4', '*.mkv', '*.webm', '*.avi', '*.mov', '*.m4a', '*.mp3']
                    for pattern in patterns:
                        files = glob.glob(os.path.join(job.tmpdir, pattern))
                        if files:
                            # Get the largest file (likely the merged result)
                            largest_file = max(files, key=os.path.getsize)
                            final_size = os.path.getsize(largest_file)
                            print(f"[DEBUG] Found merged file: {largest_file}, Size: {final_size} bytes")
                            job.filename = largest_file
                            job.downloaded_bytes = final_size
                            job.total_bytes = final_size
                            final_file_found = True
                            break
                
                if not final_file_found:
                    print(f"[DEBUG] Final file not found: {job.filename}, tmpdir: {getattr(job, 'tmpdir', 'None')}")
    except _StopForPause:
        with _LOCK:
            job.status = "paused"
    except _StopForCancel:
        # delete temp files
        try:
            shutil.rmtree(job.tmpdir, ignore_errors=True)
        finally:
            with _LOCK:
                job.status = "canceled"
                job.error = None
    except Exception as e:
        with _LOCK:
            job.status = "error"
            job.error = str(e)

def start_job(url: str, format_string: str, title: Optional[str]=None, ext: Optional[str]=None) -> Job:
    job = Job(id=str(uuid.uuid4()), url=url, format_string=format_string, title=title, ext=ext)
    with _LOCK:
        _JOBS[job.id] = job
    print(f"[DEBUG] Starting job {job.id} - Download directory: {job.tmpdir}")
    t = threading.Thread(target=_run_job, args=(job,), daemon=True)
    t.start()
    return job

def pause_job(job_id: str) -> Job:
    with _LOCK:
        job = _JOBS[job_id]
        if job.status == "downloading":
            job._pause_req = True
    return job

def resume_job(job_id: str) -> Job:
    with _LOCK:
        job = _JOBS[job_id]
        # clear pause & restart thread; yt-dlp will continue partial files
        job._pause_req = False
        job._cancel_req = False
        job.status = "queued"
    t = threading.Thread(target=_run_job, args=(job,), daemon=True)
    t.start()
    return job

def cancel_job(job_id: str) -> Job:
    with _LOCK:
        job = _JOBS[job_id]
        if job.status in ("downloading","queued","paused","merging"):
            job._cancel_req = True
    return job

def get_job(job_id: str) -> Job:
    with _LOCK: return _JOBS[job_id]

def list_jobs():
    with _LOCK: return list(_JOBS.values())

def delete_job(job_id: str) -> None:
    """Delete a job from the in-memory store."""
    with _LOCK:
        if job_id in _JOBS:
            del _JOBS[job_id]
        else:
            raise KeyError(f"Job {job_id} not found")
