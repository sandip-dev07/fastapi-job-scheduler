import uuid

from sqlalchemy import select

from src.models.jobs import Job, JobStatus
from src.utils.db import Session
from src.utils.handlers import JobContext, flaky_job
from src.utils.retry import calculate_retry_delay
from src.utils.tasks import process_job


def test_retry_delay_doubles_and_is_capped():
    assert calculate_retry_delay(5, 1, 300) == 5
    assert calculate_retry_delay(5, 2, 300) == 10
    assert calculate_retry_delay(5, 3, 300) == 20
    assert calculate_retry_delay(5, 9, 300) == 300


def test_flaky_handler_eventually_succeeds():
    context = JobContext(job_id=uuid.uuid4(), attempt=2)
    result = flaky_job({"fail_until_attempt": 2}, context)
    assert result["attempt"] == 2
    assert result["message"] == "Flaky job recovered"


def test_process_job_success_updates_database():
    with Session() as db:
        job = Job(
            job_type="add",
            payload={"a": 4, "b": 6},
            status=JobStatus.QUEUED,
            max_retries=2,
            retry_backoff_seconds=1,
        )
        db.add(job)
        db.commit()
        job_id = job.id

    returned = process_job.apply(args=[str(job_id)]).get()

    assert returned["sum"] == 10
    with Session() as db:
        stored = db.scalar(select(Job).where(Job.id == job_id))
        assert stored.status == JobStatus.SUCCEEDED
        assert stored.attempts == 1
        assert stored.result["sum"] == 10
        assert stored.last_error is None
        assert stored.started_at is not None
        assert stored.finished_at is not None
        assert stored.next_retry_at is None


def test_process_job_final_failure_when_retries_are_exhausted():
    with Session() as db:
        job = Job(
            job_type="always_fail",
            payload={"message": "expected test failure"},
            status=JobStatus.QUEUED,
            max_retries=0,
            retry_backoff_seconds=1,
        )
        db.add(job)
        db.commit()
        job_id = job.id

    result = process_job.apply(args=[str(job_id)]).get()

    assert result is None
    with Session() as db:
        stored = db.scalar(select(Job).where(Job.id == job_id))
        assert stored.status == JobStatus.FAILED
        assert stored.attempts == 1
        assert stored.last_error == "expected test failure"
        assert stored.finished_at is not None
        assert stored.next_retry_at is None


def test_process_job_skips_terminal_job():
    with Session() as db:
        job = Job(
            job_type="add",
            payload={"a": 1, "b": 1},
            status=JobStatus.SUCCEEDED,
            attempts=1,
            result={"sum": 2},
            max_retries=1,
            retry_backoff_seconds=1,
        )
        db.add(job)
        db.commit()
        job_id = job.id

    assert process_job.apply(args=[str(job_id)]).get() is None
    with Session() as db:
        stored = db.scalar(select(Job).where(Job.id == job_id))
        assert stored.status == JobStatus.SUCCEEDED
        assert stored.attempts == 1
