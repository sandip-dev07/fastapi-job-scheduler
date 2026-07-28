import logging

from celery import Celery

from src.utils.configs import settings

logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

PROCESS_JOB_TASK_NAME = "src.utils.tasks.process_job"

celery_app = Celery(
    "job_scheduler",
    broker=settings.REDIS_URL,
    include=["src.utils.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # PostgreSQL stores job state; Redis is only the broker.
    task_ignore_result=True,
    # Redeliver a task if its worker dies before acknowledging it.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    # Do not let a Redis outage hold the API request open for too long.
    broker_connection_retry=True,
    broker_connection_max_retries=2,
    broker_transport_options={
        "socket_connect_timeout": 2,
        "socket_timeout": 2,
    },
    task_publish_retry=True,
    task_publish_retry_policy={
        "max_retries": 2,
        "interval_start": 0,
        "interval_step": 0.5,
        "interval_max": 1,
    },
)
