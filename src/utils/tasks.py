"""Celery task that runs a job and updates its database row."""

import json
import logging
from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select

from src.models.jobs import TERMINAL_STATUSES, Job, JobStatus, utc_now
from src.utils.celery import PROCESS_JOB_TASK_NAME, celery_app
from src.utils.configs import settings
from src.utils.db import Session
from src.utils.handlers import JobContext, get_handler
from src.utils.retry import calculate_retry_delay

logger = logging.getLogger(__name__)


def _error_text(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    return message[:2000]


@celery_app.task(
    bind=True,
    name=PROCESS_JOB_TASK_NAME,
    acks_late=True,
    max_retries=None,
)
def process_job(self, job_id: str) -> dict[str, Any] | None:
    try:
        job_uuid = UUID(job_id)
    except (ValueError, AttributeError):
        logger.error("Received an invalid job id: %r", job_id)
        return None

    # Mark the attempt as running before calling the handler.
    with Session() as db:
        job = db.scalar(
            select(Job).where(Job.id == job_uuid).with_for_update()
        )
        if job is None:
            logger.warning("Job %s no longer exists", job_uuid)
            return None
        if job.status in TERMINAL_STATUSES:
            logger.info(
                "Skipping job %s because it is already %s",
                job_uuid,
                job.status.value,
            )
            return None

        attempt = job.attempts + 1
        job.attempts = attempt
        job.status = JobStatus.RUNNING
        job.started_at = job.started_at or utc_now()
        job.finished_at = None
        job.next_retry_at = None
        job.result = None
        db.commit()

        job_type = job.job_type
        payload = dict(job.payload or {})
        max_retries = job.max_retries
        retry_backoff_seconds = job.retry_backoff_seconds

    logger.info(
        "Running job %s (type=%s, attempt=%s/%s)",
        job_uuid,
        job_type,
        attempt,
        max_retries + 1,
    )

    try:
        handler = get_handler(job_type)
        result = handler(
            payload,
            JobContext(job_id=job_uuid, attempt=attempt),
        )
        if not isinstance(result, dict):
            result = {"result": result}

        # Fail here if the handler returned something JSONB cannot store.
        json.dumps(result)
    except Exception as exc:
        error = _error_text(exc)
        logger.exception("Job %s failed on attempt %s", job_uuid, attempt)

        should_retry = attempt <= max_retries
        retry_delay = (
            calculate_retry_delay(
                retry_backoff_seconds,
                attempt,
                settings.MAX_RETRY_BACKOFF_SECONDS,
            )
            if should_retry
            else None
        )

        with Session() as db:
            job = db.scalar(
                select(Job).where(Job.id == job_uuid).with_for_update()
            )
            if job is None or job.status in TERMINAL_STATUSES:
                logger.info(
                    "Job %s was removed or finished elsewhere; not updating",
                    job_uuid,
                )
                return None

            job.last_error = error
            if should_retry:
                job.status = JobStatus.RETRYING
                job.next_retry_at = utc_now() + timedelta(seconds=retry_delay)
            else:
                job.status = JobStatus.FAILED
                job.finished_at = utc_now()
                job.next_retry_at = None
            db.commit()

        if retry_delay is not None:
            logger.warning(
                "Retrying job %s in %s seconds (attempt %s failed)",
                job_uuid,
                retry_delay,
                attempt,
            )
            raise self.retry(exc=exc, countdown=retry_delay)

        logger.error("Job %s failed permanently", job_uuid)
        return None

    with Session() as db:
        job = db.scalar(
            select(Job).where(Job.id == job_uuid).with_for_update()
        )
        if job is None:
            logger.warning(
                "Job %s was deleted before its result could be saved",
                job_uuid,
            )
            return None
        if job.status in TERMINAL_STATUSES:
            logger.info(
                "Job %s is already terminal; ignoring this result",
                job_uuid,
            )
            return None

        job.status = JobStatus.SUCCEEDED
        job.result = result
        job.last_error = None
        job.finished_at = utc_now()
        job.next_retry_at = None
        db.commit()

    logger.info("Job %s succeeded", job_uuid)
    return result
