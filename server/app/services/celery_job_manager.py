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
        'PAUSED': 'paused',
    }
    return mapping.get(celery_state, 'queued')


def _get_job_from_task(task_id: str) -> Job:
    """Retrieve job information from Celery task and Redis metadata."""
    task = _get_celery_task(task_id)

    # Get metadata from Redis
    job_key = f"job:{task_id}"
    job_data = redis_client.hgetall(job_key)

    if not job_data:
        # Job metadata not found - job might have been deleted/expired
        # Return minimal job with placeholder URL to avoid validation errors
        return Job(
            id=task_id,
            url="https://example.com/deleted",
            format_string="unknown",
            status="error",
            error="Job metadata not found (expired or deleted)"
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
        # Check if this is a paused task (error message will contain "paused by user")
        error_msg = str(task.info) if task.info else ""
        if "paused by user" in error_msg.lower():
            job.status = 'paused'
            # Get paused tmpdir from Redis
            paused_tmpdir = redis_client.hget(job_key, 'paused_tmpdir')
            if paused_tmpdir:
                job.tmpdir = paused_tmpdir
        else:
            job.status = 'error'
            job.error = error_msg

    elif task.state == 'PAUSED':
        info = task.info or {}
        job.status = 'paused'
        job.tmpdir = info.get('tmpdir')

    # Check for manual pause flag even if task is still running
    pause_key = f"job:{task_id}:pause"
    if redis_client.exists(pause_key) and job.status not in ('done', 'error', 'canceled'):
        job.status = 'paused'

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
    """Pause job by setting a flag in Redis."""
    # Set pause flag in Redis
    pause_key = f"job:{job_id}:pause"
    redis_client.set(pause_key, "1", ex=86400)  # Expire after 24 hours

    job = get_job(job_id)
    job.status = 'paused'

    # Note: The actual pausing happens in the task when it checks this flag
    # For running tasks, they will pause on next progress update
    print(f"[INFO] Pause requested for job {job_id}")
    return job


def resume_job(job_id: str) -> Job:
    """Resume a paused job by removing the pause flag."""
    # Remove pause flag from Redis
    pause_key = f"job:{job_id}:pause"
    redis_client.delete(pause_key)

    job = get_job(job_id)

    # If job was actually paused/stopped, we need to restart it
    if job.status in ('paused', 'canceled'):
        # Get job metadata
        job_key = f"job:{job_id}"
        job_data = redis_client.hgetall(job_key)

        if job_data:
            # Restart the download task with same parameters
            task = download_media.apply_async(
                args=[
                    job_data.get('url'),
                    job_data.get('format_string'),
                    job_data.get('title'),
                    job_data.get('ext')
                ],
                task_id=job_id  # Reuse same task ID
            )
            job.status = 'queued'
            print(f"[INFO] Resuming job {job_id}")

    return job


def cancel_job(job_id: str) -> Job:
    """Cancel a running job."""
    # Set cancel flag in Redis
    cancel_key = f"job:{job_id}:cancel"
    redis_client.set(cancel_key, "1", ex=86400)  # Expire after 24 hours

    # Also revoke the Celery task
    task = _get_celery_task(job_id)
    task.revoke(terminate=True)  # Terminate the task

    job = get_job(job_id)
    job.status = 'canceled'
    print(f"[INFO] Canceled job {job_id}")
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


def delete_job(job_id: str) -> None:
    """Delete a job from Redis and revoke its Celery task."""
    # Revoke the Celery task if still running
    task = _get_celery_task(job_id)
    task.revoke(terminate=True)

    # Delete all Redis keys for this job
    job_key = f"job:{job_id}"
    pause_key = f"job:{job_id}:pause"
    cancel_key = f"job:{job_id}:cancel"

    redis_client.delete(job_key, pause_key, cancel_key)
    redis_client.srem('jobs:all', job_id)

    print(f"[INFO] Deleted job {job_id} from Redis")
