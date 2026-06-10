# app/celery_app.py
from celery import Celery
from app.config import settings

celery_app = Celery(
    "auditbot",
    broker=settings.REDIS_URL.get_secret_value(),
    backend=settings.REDIS_URL.get_secret_value(),
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Reliability settings
    task_track_started=True,
    task_acks_late=True,  # only ack after successful finish
    worker_prefetch_multiplier=1,  # one task per worker at a time — fair dispatch
    task_reject_on_worker_lost=True,  # re-queue if worker crashes mid-task
    # Retry defaults
    task_default_retry_delay=30,  # seconds between retries
    task_max_retries=3,
    # Routing
    task_routes={
        "app.tasks.process_document_pipeline": {"queue": "documents"},
    },
    # Result expiry — keep results for 24 hours
    result_expires=86400,
)
