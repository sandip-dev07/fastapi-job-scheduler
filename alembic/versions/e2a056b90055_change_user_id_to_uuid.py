"""change user id to uuid

Revision ID: e2a056b90055
Revises: dc454679308a
Create Date: 2026-07-24 01:10:27.052425

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2a056b90055'
down_revision: Union[str, Sequence[str], None] = 'dc454679308a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.add_column(
        "users",
        sa.Column("id_uuid", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
    )
    op.add_column(
        "tasks",
        sa.Column("user_id_uuid", sa.UUID(), nullable=True),
    )

    op.execute(
        """
        UPDATE tasks
        SET user_id_uuid = users.id_uuid
        FROM users
        WHERE tasks.user_id = users.id
        """
    )

    op.drop_constraint("tasks_user_id_fkey", "tasks", type_="foreignkey")
    op.drop_index(op.f("ix_tasks_user_id"), table_name="tasks")
    op.drop_constraint("users_pkey", "users", type_="primary")
    op.drop_index(op.f("ix_users_id"), table_name="users")

    op.drop_column("tasks", "user_id")
    op.alter_column(
        "tasks",
        "user_id_uuid",
        new_column_name="user_id",
        existing_type=sa.UUID(),
        nullable=False,
    )

    op.drop_column("users", "id")
    op.alter_column(
        "users",
        "id_uuid",
        new_column_name="id",
        existing_type=sa.UUID(),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )

    op.create_primary_key("users_pkey", "users", ["id"])
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_tasks_user_id"), "tasks", ["user_id"], unique=False)
    op.create_foreign_key("tasks_user_id_fkey", "tasks", "users", ["user_id"], ["id"])


def downgrade() -> None:
    """Downgrade schema."""
    raise NotImplementedError("Downgrade from UUID IDs back to INTEGER IDs is not supported.")
