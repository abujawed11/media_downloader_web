"""Job manager using Celery for distributed task processing."""
import redis
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from celery.result import AsyncResult

from ..celery_app import celery_app
from ..config import settings
from ..tasks import download_media


# Redis client for job metadata
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


@dataclass
class Job:
    """Job model matching the original structure."""
    id: str
    url: str
    format_string: str
    title: Optional[str] = None
    ext: Optional[str] = None
    status: str = "queued"
    progress: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    speed_bps: Optional[float] = None
    eta_seconds: Optional[int] = None
    filename: Optional[str] = None
    tmpdir: Optional[str] = None
    error: Optional[str] = None


def _get_celery_task(task_id: str) -> AsyncResult:
    """Get Celery task result."""
    return AsyncResult(task_id, app=celery_app)


def _celery_state_to_job_status(celery_state: str) -> str:
    """Convert Celery task state to job status."""
    mapping = {
        'PENDING': 'queued',
        'STARTED': 'downloading',
        'PROGRESS': 'downloading',
        'SUCCESS': 'done',
        'FAILURE': 'error',
        'RETRY': 'downloading',
        'REVOKED': 'canceled',
    }
    return mapping.get(celery_state, 'queued')


def _get_job_from_task(task_id: str) -> Job:
    """Retrieve job information from Celery task and Redis metadata."""
    task = _get_celery_task(task_id)

    # Get metadata from Redis
    job_key = f"job:{task_id}"
    job_data = redis_client.hgetall(job_key)

    if not job_data:
        # Job metadata not found, create minimal job
        return Job(
            id=task_id,
            url="",
            format_string="",
            status="error",
            error="Job not found"
        )

    # Build job from Redis data
    job = Job(
        id=task_id,
        url=job_data.get('url', ''),
        format_string=job_data.get('format_string', ''),
        title=job_data.get('title'),
        ext=job_data.get('ext'),
        status=_celery_state_to_job_status(task.state),
        progress=0.0,
        downloaded_bytes=0,
        total_bytes=None,
        speed_bps=None,
        eta_seconds=None,
        filename=None,
        tmpdir=None,
        error=None,
    )

    # Update with Celery task info
    if task.state == 'PROGRESS':
        info = task.info or {}
        job.status = info.get('status', 'downloading')
        job.progress = info.get('progress', 0.0) / 100.0  # Convert percentage to 0-1
        job.downloaded_bytes = info.get('downloaded_bytes', 0)
        job.total_bytes = info.get('total_bytes')
        job.speed_bps = info.get('speed_bps')
        job.eta_seconds = info.get('eta_seconds')

    elif task.state == 'SUCCESS':
        result = task.result or {}
        job.status = 'done'
        job.progress = 1.0
        job.filename = result.get('filename')
        job.tmpdir = result.get('tmpdir')
        job.downloaded_bytes = result.get('file_size', 0)
        job.total_bytes = result.get('file_size', 0)

    elif task.state == 'FAILURE':
        job.status = 'error'
        job.error = str(task.info) if task.info else "Unknown error"

    return job


def start_job(url: str, format_string: str, title: Optional[str] = None, ext: Optional[str] = None) -> Job:
    """Start a new download job using Celery."""
    # Submit task to Celery (using default queue)
    task = download_media.apply_async(
        args=[url, format_string, title, ext]
    )

    # Store job metadata in Redis
    job_key = f"job:{task.id}"
    redis_client.hset(job_key, mapping={
        'url': url,
        'format_string': format_string,
        'title': title or '',
        'ext': ext or '',
    })
    redis_client.expire(job_key, 86400)  # Expire after 24 hours

    # Add to job list
    redis_client.sadd('jobs:all', task.id)
    redis_client.expire('jobs:all', 86400)

    return Job(
        id=task.id,
        url=url,
        format_string=format_string,
        title=title,
        ext=ext,
        status='queued',
        progress=0.0,
    )


def pause_job(job_id: str) -> Job:
    """Pause job - Not supported in Celery, return current state."""
    # Celery doesn't support pause/resume natively
    # You would need to implement custom logic in the task
    job = get_job(job_id)
    # For now, just return the current state
    return job


def resume_job(job_id: str) -> Job:
    """Resume job - Not supported in Celery, return current state."""
    # Celery doesn't support pause/resume natively
    job = get_job(job_id)
    return job


def cancel_job(job_id: str) -> Job:
    """Cancel a running job."""
    task = _get_celery_task(job_id)
    task.revoke(terminate=True)  # Terminate the task

    job = get_job(job_id)
    job.status = 'canceled'
    return job


def get_job(job_id: str) -> Job:
    """Get job by ID."""
    return _get_job_from_task(job_id)


def list_jobs() -> List[Job]:
    """List all jobs."""
    job_ids = redis_client.smembers('jobs:all')
    jobs = []

    for job_id in job_ids:
        try:
            job = _get_job_from_task(job_id)
            jobs.append(job)
        except Exception as e:
            print(f"Error loading job {job_id}: {e}")
            continue

    # Sort by ID (newest first)
    jobs.sort(key=lambda j: j.id, reverse=True)
    return jobs
