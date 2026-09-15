"""Add Phase 5 project schedule, progress & delay tracking tables
(activities, milestones)

Revision ID: 0004_schedule
Revises: 0003_resources
Create Date: 2026-09-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_schedule"
down_revision = "0003_resources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project", sa.String(500), nullable=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("project_stage", sa.String(300), nullable=True),
        sa.Column("estimate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("estimates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("planned_start_date", sa.Date(), nullable=True),
        sa.Column("planned_end_date", sa.Date(), nullable=True),
        sa.Column("actual_start_date", sa.Date(), nullable=True),
        sa.Column("actual_end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(50), nullable=True, server_default="not_started"),
        sa.Column("progress_percentage", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("responsible_person", sa.String(500), nullable=True),
        sa.Column("delay_reason", sa.String(300), nullable=True),
        sa.Column("delay_reason_detail", sa.Text(), nullable=True),
        sa.Column("resource_dependency", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_activities_status", "activities", ["status"])
    op.create_index("ix_activities_project_stage", "activities", ["project_stage"])
    op.create_index("ix_activities_estimate_id", "activities", ["estimate_id"])

    op.create_table(
        "milestones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project", sa.String(500), nullable=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("estimate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("estimates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("planned_date", sa.Date(), nullable=True),
        sa.Column("actual_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(50), nullable=True, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_milestones_status", "milestones", ["status"])
    op.create_index("ix_milestones_estimate_id", "milestones", ["estimate_id"])


def downgrade() -> None:
    op.drop_index("ix_milestones_estimate_id", table_name="milestones")
    op.drop_index("ix_milestones_status", table_name="milestones")
    op.drop_table("milestones")
    op.drop_index("ix_activities_estimate_id", table_name="activities")
    op.drop_index("ix_activities_project_stage", table_name="activities")
    op.drop_index("ix_activities_status", table_name="activities")
    op.drop_table("activities")