import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum as SqlEnum,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB

from src.utils.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


TERMINAL_STATUSES = {JobStatus.SUCCEEDED, JobStatus.FAILED}


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("attempts >= 0", name="ck_jobs_attempts_non_negative"),
        CheckConstraint(
            "max_retries >= 0", name="ck_jobs_max_retries_non_negative"
        ),
        CheckConstraint(
            "retry_backoff_seconds >= 1",
            name="ck_jobs_retry_backoff_positive",
        ),
        Index("ix_jobs_status_created_at", "status", "created_at"),
        Index("ix_jobs_created_at", "created_at"),
    )

    id = Column(Uuid(), primary_key=True, default=uuid.uuid4)
    job_type = Column(String(50), nullable=False)

    payload = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    result = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

    status = Column(
        SqlEnum(
            JobStatus,
            name="job_status",
            native_enum=False,
            length=20,
            values_callable=lambda status_enum: [
                status.value for status in status_enum
            ],
            create_constraint=True,
        ),
        nullable=False,
        default=JobStatus.PENDING,
    )

    attempts = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    retry_backoff_seconds = Column(Integer, nullable=False, default=5)

    last_error = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
