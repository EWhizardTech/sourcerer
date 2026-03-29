from celery import Celery

celery = Celery(
    "sourcerer",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1",
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
)

if __name__ == "__main__":
    celery.start()
