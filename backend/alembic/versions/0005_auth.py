"""Add Stage A authentication tables (users, projects, user_projects)

Revision ID: 0005_auth
Revises: 0004_schedule
Create Date: 2026-09-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "0005_auth"
down_revision = "0004_schedule"
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return inspect(bind).has_table(name)


def upgrade() -> None:
    if not _table_exists("users"):
        op.create_table(
            "users",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("username", sa.String(100), nullable=False),
            sa.Column("full_name", sa.String(300), nullable=False),
            sa.Column("password_hash", sa.String(500), nullable=False),
            sa.Column("role", sa.String(20), nullable=True, server_default="member"),
            sa.Column("status", sa.String(20), nullable=True, server_default="active"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("username", name="uq_users_username"),
        )
    if not _table_exists("projects"):
        op.create_table(
            "projects",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("name", sa.String(300), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("name", name="uq_projects_name"),
        )
    if not _table_exists("user_projects"):
        op.create_table(
            "user_projects",
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "project_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("projects.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    indexes = {i["name"] for i in inspect(op.get_bind()).get_indexes("users")}
    if "ix_users_username" in indexes:
        op.drop_index("ix_users_username", table_name="users")
    op.create_index("ix_users_username", "users", ["username"])


def downgrade() -> None:
    if _table_exists("user_projects"):
        op.drop_table("user_projects")
    if _table_exists("projects"):
        op.drop_table("projects")
    if _table_exists("users"):
        op.drop_index("ix_users_username", table_name="users")
        op.drop_table("users")