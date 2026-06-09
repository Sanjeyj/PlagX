import os
from celery import Celery

# Redis URL from environment or default to local
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery Application
celery_app = Celery(
    "plagx_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks.plagiarism_tasks"]
)

# Enterprise configuration
celery_app.conf.update(
    task_acks_late=True,                 # Don't acknowledge task until it finishes
    worker_prefetch_multiplier=1,        # Only fetch 1 task at a time (prevents heavy tasks from starving others)
    task_track_started=True,             # Track when task actually starts
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    
    # Task Routes - Send heavy tasks to dedicated queues
    task_routes={
        "app.tasks.plagiarism_tasks.pdf_generation_task": {"queue": "pdf"},
        "app.tasks.plagiarism_tasks.embedding_generation_task": {"queue": "embeddings"},
        "app.tasks.plagiarism_tasks.*": {"queue": "celery"}  # default queue for extraction/scoring
    },
    
    # Task Expiration (prevent dead jobs from clogging queue forever)
    task_time_limit=1800,                # Hard kill at 30 mins
    task_soft_time_limit=1700,           # Soft kill at 28 mins
)
