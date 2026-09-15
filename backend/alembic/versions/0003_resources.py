"""Add Phase 4 material & resource accountability tables
(resources, resource_movements)

Revision ID: 0003_resources
Revises: 0002_expenses
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_resources"
down_revision = "0002_expenses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project", sa.String(500), nullable=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("category", sa.String(300), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("currency", sa.String(50), nullable=True, server_default="FCFA"),
        sa.Column("estimate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("estimates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("estimate_line_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("estimate_line_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("budgeted_quantity", sa.Numeric(12, 2), nullable=True),
        sa.Column("budgeted_cost", sa.Numeric(15, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=True, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "resource_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("movement_type", sa.String(50), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("movement_date", sa.Date(), nullable=False, server_default=sa.func.current_date()),
        sa.Column("unit_cost", sa.Numeric(15, 2), nullable=True),
        sa.Column("total_cost", sa.Numeric(15, 2), nullable=True),
        sa.Column("expense_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("expenses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("related_purchase_movement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resource_movements.id", ondelete="SET NULL"), nullable=True),
        sa.Column("supplier", sa.String(500), nullable=True),
        sa.Column("reference", sa.String(200), nullable=True),
        sa.Column("receiver", sa.String(500), nullable=True),
        sa.Column("project_stage", sa.String(300), nullable=True),
        sa.Column("activity", sa.Text(), nullable=True),
        sa.Column("responsible_person", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("authorized_by", sa.String(500), nullable=True),
        sa.Column("authorization_reason", sa.Text(), nullable=True),
        sa.Column("evidence_filename", sa.String(500), nullable=True),
        sa.Column("evidence_original_filename", sa.String(500), nullable=True),
        sa.Column("evidence_mime_type", sa.String(255), nullable=True),
        sa.Column("evidence_size", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_resource_movements_resource_id", "resource_movements", ["resource_id"])
    op.create_index("ix_resource_movements_type", "resource_movements", ["movement_type"])


def downgrade() -> None:
    op.drop_index("ix_resource_movements_type", table_name="resource_movements")
    op.drop_index("ix_resource_movements_resource_id", table_name="resource_movements")
    op.drop_table("resource_movements")
    op.drop_table("resources")