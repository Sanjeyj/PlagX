"""
Celery worker tasks for background plagiarism processing.
"""

from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "plagx_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_plagiarism_check_task(self, document_id: str):
    """Celery task to run plagiarism check asynchronously."""
    import asyncio
    from app.api.documents import run_plagiarism_check_bg

    try:
        self.update_state(state="PROGRESS", meta={"progress": 0, "stage": "Starting"})
        asyncio.run(run_plagiarism_check_bg(document_id))
        return {"status": "completed", "document_id": document_id}
    except Exception as exc:
        self.retry(exc=exc)
