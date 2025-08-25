# server/app/services/job_manager.py
import os, tempfile, threading, uuid, time, shutil
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional
import yt_dlp

from .ytdlp_service import _cookies_for  # reuse your cookies helper

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
    tmpdir: str = field(default_factory=lambda: tempfile.mkdtemp(prefix="mdjob_"))
    error: Optional[str] = None

    # control flags
    _pause_req: bool = False
    _cancel_req: bool = False

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
                job.downloaded_bytes = int(d.get("downloaded_bytes") or 0)
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                job.total_bytes = int(total) if total else None
                if job.total_bytes:
                    job.progress = max(0.0, min(1.0, job.downloaded_bytes / job.total_bytes))
                job.speed_bps = d.get("speed") or None
                job.eta_seconds = int(d.get("eta")) if d.get("eta") is not None else None
                fn = d.get("filename") or d.get("tmpfilename")
                if fn: job.filename = fn
            elif st == "finished":
                job.status = "merging"  # yt-dlp is about to post-process
                fn = d.get("filename")
                if fn: job.filename = fn
    return hook

def _run_job(job: Job):
    try:
        ydl_opts = _ydl_opts_for(job)
        ydl_opts["progress_hooks"] = [_progress_hook(job)]
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(job.url, download=True)
            # best guess at final filename
            if isinstance(info, dict):
                fn = info.get("_filename") or job.filename
                if fn: job.filename = fn
        with _LOCK:
            job.status = "done"
            job.progress = 1.0
            job.speed_bps = 0
            job.eta_seconds = 0
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
