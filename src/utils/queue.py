import logging

from sqlalchemy.orm import Session

from src.models.jobs import Job, JobStatus, utc_now
from src.utils.celery import PROCESS_JOB_TASK_NAME, celery_app

logger = logging.getLogger(__name__)


class EnqueueError(Exception):
    def __init__(self, job_id):
        self.job_id = job_id
        super().__init__(f"Could not enqueue job {job_id}")


def enqueue_job(db: Session, job: Job) -> None:
    # Save queued first so a fast worker can already find the row.
    job.status = JobStatus.QUEUED
    job.next_retry_at = None
    db.commit()

    try:
        celery_app.send_task(
            PROCESS_JOB_TASK_NAME,
            args=[str(job.id)],
            task_id=str(job.id),
            ignore_result=True,
        )
    except Exception as exc:
        logger.exception("Could not enqueue job %s", job.id)
        job.status = JobStatus.FAILED
        job.last_error = f"Could not enqueue job: {exc}"[:2000]
        job.finished_at = utc_now()
        db.commit()
        raise EnqueueError(job.id) from exc

    # The worker may have changed the row already.
    db.refresh(job)
