"""Create the jobs table.

Revision ID: 0001_create_jobs
Revises:
Create Date: 2026-11-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_create_jobs"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    job_status = sa.Enum(
        "pending",
        "queued",
        "running",
        "retrying",
        "succeeded",
        "failed",
        name="job_status",
        native_enum=False,
        length=20,
        create_constraint=True,
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "status",
            job_status,
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "attempts",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "max_retries",
            sa.Integer(),
            server_default=sa.text("3"),
            nullable=False,
        ),
        sa.Column(
            "retry_backoff_seconds",
            sa.Integer(),
            server_default=sa.text("5"),
            nullable=False,
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "next_retry_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "attempts >= 0", name="ck_jobs_attempts_non_negative"
        ),
        sa.CheckConstraint(
            "max_retries >= 0", name="ck_jobs_max_retries_non_negative"
        ),
        sa.CheckConstraint(
            "retry_backoff_seconds >= 1",
            name="ck_jobs_retry_backoff_positive",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_jobs_status_created_at",
        "jobs",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_jobs_created_at",
        "jobs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_created_at", table_name="jobs")
    op.drop_index("ix_jobs_status_created_at", table_name="jobs")
    op.drop_table("jobs")
