"""Add Phase 2 funding tables (fund_receipts, fund_allocations, fund_audit_logs)

Revision ID: 0001_funding
Revises:
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_funding"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fund_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("estimate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("estimates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("currency", sa.String(50), nullable=True, server_default="FCFA"),
        sa.Column("received_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(500), nullable=False),
        sa.Column("reference", sa.String(200), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=True, server_default="recorded"),
        sa.Column("evidence_filename", sa.String(500), nullable=True),
        sa.Column("evidence_original_filename", sa.String(500), nullable=True),
        sa.Column("evidence_mime_type", sa.String(255), nullable=True),
        sa.Column("evidence_size", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "fund_allocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("fund_receipt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fund_receipts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("estimate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("estimates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category", sa.String(300), nullable=True),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("responsible_person", sa.String(500), nullable=True),
        sa.Column("allocation_date", sa.Date(), nullable=False, server_default=sa.func.current_date()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=True, server_default="allocated"),
        sa.Column("evidence_filename", sa.String(500), nullable=True),
        sa.Column("evidence_original_filename", sa.String(500), nullable=True),
        sa.Column("evidence_mime_type", sa.String(255), nullable=True),
        sa.Column("evidence_size", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "fund_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("field_name", sa.String(200), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_fund_allocations_receipt_id", "fund_allocations", ["fund_receipt_id"])
    op.create_index("ix_fund_audit_entity", "fund_audit_logs", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("ix_fund_audit_entity", table_name="fund_audit_logs")
    op.drop_index("ix_fund_allocations_receipt_id", table_name="fund_allocations")
    op.drop_table("fund_audit_logs")
    op.drop_table("fund_allocations")
    op.drop_table("fund_receipts")