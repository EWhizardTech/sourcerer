from celery import Celery
from app.core.config import settings


celery = Celery(
    "sourcerer",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_BACKEND_URL,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
)

celery.autodiscover_tasks(["app.workers"])
