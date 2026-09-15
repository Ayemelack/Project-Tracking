"""Add Phase 3 expense tracking table (expenses)

Revision ID: 0002_expenses
Revises: 0001_funding
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_expenses"
down_revision = "0001_funding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project", sa.String(500), nullable=True),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(300), nullable=True),
        sa.Column("estimate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("estimates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("estimate_line_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("estimate_line_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("allocation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fund_allocations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("supplier", sa.String(500), nullable=True),
        sa.Column("payment_method", sa.String(50), nullable=True),
        sa.Column("reference", sa.String(200), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("responsible_person", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("currency", sa.String(50), nullable=True, server_default="FCFA"),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("unit_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("authorized_by", sa.String(500), nullable=True),
        sa.Column("authorization_reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=True, server_default="recorded"),
        sa.Column("evidence_filename", sa.String(500), nullable=True),
        sa.Column("evidence_original_filename", sa.String(500), nullable=True),
        sa.Column("evidence_mime_type", sa.String(255), nullable=True),
        sa.Column("evidence_size", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_expenses_allocation_id", "expenses", ["allocation_id"])
    op.create_index("ix_expenses_estimate_id", "expenses", ["estimate_id"])
    op.create_index("ix_expenses_date", "expenses", ["expense_date"])


def downgrade() -> None:
    op.drop_index("ix_expenses_date", table_name="expenses")
    op.drop_index("ix_expenses_estimate_id", table_name="expenses")
    op.drop_index("ix_expenses_allocation_id", table_name="expenses")
    op.drop_table("expenses")