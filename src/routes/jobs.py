import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.interfaces.jobs import (
    IJobCreate,
    IJobListData,
    IJobResponse,
    IJobsListResponse,
    IJobType,
    IJobTypesResponse,
)
from src.models.jobs import TERMINAL_STATUSES, Job as JobModel, JobStatus
from src.utils.db import get_db
from src.utils.handlers import JOB_HANDLERS
from src.utils.queue import EnqueueError, enqueue_job

jobs_router = APIRouter(prefix="/jobs", tags=["Jobs"])


@jobs_router.get("/types", response_model=IJobTypesResponse)
def get_job_types():
    data = [
        IJobType(name=name, description=definition.description)
        for name, definition in sorted(JOB_HANDLERS.items())
    ]
    return {
        "message": "Job types fetched successfully",
        "data": data,
    }


@jobs_router.post(
    "/create",
    response_model=IJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_job(body: IJobCreate, db: Session = Depends(get_db)):
    if body.job_type not in JOB_HANDLERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported job type '{body.job_type}'",
        )

    job = JobModel(**body.model_dump(), status=JobStatus.PENDING)

    try:
        db.add(job)
        db.commit()
        db.refresh(job)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create job",
        )

    try:
        enqueue_job(db, job)
    except EnqueueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Job was saved but Redis did not accept it",
                "job_id": str(exc.job_id),
            },
        )

    return {
        "message": "Job created successfully",
        "data": job,
    }


@jobs_router.get("/", response_model=IJobsListResponse)
def get_jobs(
    status_filter: JobStatus | None = Query(
        default=None,
        alias="status",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(JobModel)

    if status_filter is not None:
        query = query.filter(JobModel.status == status_filter)

    total = query.count()
    jobs = (
        query.order_by(JobModel.created_at.desc(), JobModel.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "message": "Jobs fetched successfully",
        "data": IJobListData(
            items=jobs,
            total=total,
            page=page,
            page_size=page_size,
            pages=math.ceil(total / page_size) if total else 0,
        ),
    }


@jobs_router.get("/{job_id}", response_model=IJobResponse)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = db.query(JobModel).filter(JobModel.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return {
        "message": "Job fetched successfully",
        "data": job,
    }


@jobs_router.post(
    "/{job_id}/retry",
    response_model=IJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = db.query(JobModel).filter(JobModel.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.status != JobStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed jobs can be retried",
        )

    job.status = JobStatus.PENDING
    job.attempts = 0
    job.result = None
    job.last_error = None
    job.started_at = None
    job.finished_at = None
    job.next_retry_at = None

    try:
        db.commit()
        db.refresh(job)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry job",
        )

    try:
        enqueue_job(db, job)
    except EnqueueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Job was saved but Redis did not accept it",
                "job_id": str(exc.job_id),
            },
        )

    return {
        "message": "Job retried successfully",
        "data": job,
    }


@jobs_router.delete("/{job_id}")
def delete_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = db.query(JobModel).filter(JobModel.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.status not in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a job while it is still active",
        )

    try:
        db.delete(job)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete job",
        )

    return {"message": "Job deleted successfully"}
