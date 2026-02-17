"""Celery application configuration for async job processing."""
from celery import Celery
from app.config import settings

# Create Celery app
celery_app = Celery(
    "media_downloader",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"]  # Auto-discover tasks
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3000,  # 50 minutes soft limit
    worker_prefetch_multiplier=1,  # Take one task at a time
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (prevent memory leaks)
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,
    result_expires=86400,  # Results expire after 24 hours
)

# Task routes - use default 'celery' queue for simplicity
# celery_app.conf.task_routes = {
#     "app.tasks.download_media": {"queue": "downloads"},
# }
