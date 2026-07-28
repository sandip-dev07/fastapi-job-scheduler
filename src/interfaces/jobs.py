import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.models.jobs import JobStatus
from src.utils.configs import settings


class IJobCreate(BaseModel):
    job_type: str = Field(min_length=1, max_length=50)
    payload: dict[str, Any] = Field(default_factory=dict)
    max_retries: int = Field(
        default=settings.DEFAULT_MAX_RETRIES,
        ge=0,
        le=10,
    )
    retry_backoff_seconds: int = Field(
        default=settings.DEFAULT_RETRY_BACKOFF_SECONDS,
        ge=1,
        le=settings.MAX_RETRY_BACKOFF_SECONDS,
    )


class IJobRead(BaseModel):
    id: uuid.UUID
    job_type: str
    payload: dict[str, Any]
    status: JobStatus
    attempts: int
    max_retries: int
    retry_backoff_seconds: int
    result: dict[str, Any] | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    next_retry_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class IJobResponse(BaseModel):
    message: str
    data: IJobRead


class IJobListData(BaseModel):
    items: list[IJobRead]
    total: int
    page: int
    page_size: int
    pages: int


class IJobsListResponse(BaseModel):
    message: str
    data: IJobListData


class IJobType(BaseModel):
    name: str
    description: str


class IJobTypesResponse(BaseModel):
    message: str
    data: list[IJobType]
