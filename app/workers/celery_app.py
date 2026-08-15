import os

from celery import Celery

from app.core.config import settings

celery = Celery(
    "sourcerer",
    broker=settings.CELERY_BROKER_URL,
    # Disable backend to bypass connection issues (tracking is handled in tasks)
    backend=None,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    broker_connection_retry_on_startup=True,
    task_ignore_result=True,  # Global ignore as we use a separate tracking DB
)

# Celery's default prefork pool relies on billiard process primitives that are
# unstable on Windows. Use a single-process pool for local Windows development.
if os.name == "nt":
    celery.conf.update(
        worker_pool="solo",
        worker_concurrency=1,
        worker_prefetch_multiplier=1,
    )

celery.autodiscover_tasks(["app.workers"])
