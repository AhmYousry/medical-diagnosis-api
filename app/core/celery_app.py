from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "medical_diagnosis",
    broker=settings.celery_broker_url or settings.redis_url,
    backend=settings.celery_result_backend or settings.redis_url,
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
    task_soft_time_limit=settings.celery_task_soft_time_limit,
    task_time_limit=settings.celery_task_time_limit,
    task_routes={
        "app.modules.predictions.tasks.run_prediction": {"queue": "predictions"},
    },
)

celery_app.autodiscover_tasks(["app.modules.predictions"])
