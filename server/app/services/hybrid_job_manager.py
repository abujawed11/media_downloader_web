"""
Hybrid job manager that uses Celery when available, falls back to threading.
"""
import os
import redis

# Try to detect if Redis is available
def _is_redis_available() -> bool:
    """Check if Redis is accessible."""
    try:
        from ..config import settings
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        r.ping()
        return True
    except Exception as e:
        print(f"[INFO] Redis not available ({e}), using threading fallback")
        return False


# Import the appropriate job manager
USE_CELERY = _is_redis_available()

if USE_CELERY:
    print("[INFO] Using Celery job manager (Redis available)")
    from .celery_job_manager import (
        start_job,
        pause_job,
        resume_job,
        cancel_job,
        get_job,
        list_jobs,
        Job,
    )
else:
    print("[INFO] Using threading job manager (Redis not available)")
    from .job_manager import (
        start_job,
        pause_job,
        resume_job,
        cancel_job,
        get_job,
        list_jobs,
        Job,
    )

# Re-export everything
__all__ = [
    "start_job",
    "pause_job",
    "resume_job",
    "cancel_job",
    "get_job",
    "list_jobs",
    "Job",
]
