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
    
    # Reliability
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1, 
    task_reject_on_worker_lost=True,
    
    # Time Limits for AI tasks
    task_time_limit=600, 
    task_soft_time_limit=540,
    
    # Retries
    task_default_retry_delay=30,
    task_max_retries=3,
    
    # Routing
    task_routes={
        "app.tasks.process_document_pipeline": {"queue": "documents"},
    },
    
    # Expiry
    result_expires=86400,
)

# Debug logging for workers if enabled in .env
if settings.DEBUG:
    celery_app.conf.update(worker_log_level="DEBUG")