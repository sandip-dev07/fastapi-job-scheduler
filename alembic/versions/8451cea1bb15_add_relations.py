"""add relations

Revision ID: 8451cea1bb15
Revises: 1fafaa40313d
Create Date: 2026-07-27 13:13:48.395603

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8451cea1bb15'
down_revision: Union[str, Sequence[str], None] = '1fafaa40313d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    user_id_type = bind.execute(
        sa.text(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'id'
            """
        )
    ).scalar()

    tasks_user_id_exists = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'tasks' AND column_name = 'user_id'
            """
        )
    ).scalar()

    if user_id_type == "uuid":
        op.execute("CREATE SEQUENCE IF NOT EXISTS users_id_int_seq")
        op.add_column("users", sa.Column("id_int", sa.Integer(), nullable=True))
        op.execute("ALTER TABLE users ALTER COLUMN id_int SET DEFAULT nextval('users_id_int_seq')")
        op.execute("UPDATE users SET id_int = nextval('users_id_int_seq') WHERE id_int IS NULL")
        op.alter_column("users", "id_int", existing_type=sa.Integer(), nullable=False)
        op.drop_constraint("users_pkey", "users", type_="primary")
        op.drop_index(op.f("ix_users_id"), table_name="users")
        op.drop_column("users", "id")
        op.alter_column("users", "id_int", new_column_name="id", existing_type=sa.Integer())
        op.create_primary_key("users_pkey", "users", ["id"])
        op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
        op.execute("ALTER SEQUENCE users_id_int_seq OWNED BY users.id")
        op.execute("SELECT setval('users_id_int_seq', COALESCE((SELECT MAX(id) FROM users), 1), true)")

    if not tasks_user_id_exists:
        op.add_column("tasks", sa.Column("user_id", sa.Integer(), nullable=True))
        op.create_index(op.f("ix_tasks_user_id"), "tasks", ["user_id"], unique=False)
        op.create_foreign_key(
            "tasks_user_id_fkey",
            "tasks",
            "users",
            ["user_id"],
            ["id"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("tasks_user_id_fkey", "tasks", type_="foreignkey")
    op.drop_index(op.f("ix_tasks_user_id"), table_name="tasks")
    op.drop_column("tasks", "user_id")
