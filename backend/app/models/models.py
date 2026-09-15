import uuid
from datetime import datetime, date, timezone
from sqlalchemy import (
    Column, String, Text, Numeric, ForeignKey, DateTime, Integer, Date
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Estimate(Base):
    __tablename__ = "estimates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    project_name = Column(String(500), nullable=True)
    reference_number = Column(String(200), nullable=True)
    contractor = Column(String(500), nullable=True)
    client = Column(String(500), nullable=True)
    currency = Column(String(50), default="FCFA")
    original_filename = Column(String(500), nullable=False)
    stored_filename = Column(String(500), nullable=False)
    status = Column(String(50), default="extracted")  # extracted, confirmed, rejected
    total_estimated_amount = Column(Numeric(15, 2), default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    line_items = relationship("EstimateLineItem", back_populates="estimate", cascade="all, delete-orphan")


class EstimateLineItem(Base):
    __tablename__ = "estimate_line_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estimate_id = Column(UUID(as_uuid=True), ForeignKey("estimates.id", ondelete="CASCADE"), nullable=False)
    item_number = Column(String(50), nullable=True)
    category = Column(String(300), nullable=True)
    description = Column(Text, nullable=False)
    quantity = Column(Numeric(12, 2), nullable=True)
    unit = Column(String(50), nullable=True)
    unit_cost = Column(Numeric(15, 2), nullable=True)
    total_cost = Column(Numeric(15, 2), nullable=True)
    source_page = Column(Integer, nullable=True)
    section_total_type = Column(String(50), nullable=True)  # material, labour, section_total, grand_total
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    estimate = relationship("Estimate", back_populates="line_items")


class FundReceipt(Base):
    __tablename__ = "fund_receipts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estimate_id = Column(UUID(as_uuid=True), ForeignKey("estimates.id", ondelete="SET NULL"), nullable=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(50), default="FCFA")
    received_date = Column(Date, nullable=False)
    source = Column(String(500), nullable=False)
    reference = Column(String(200), nullable=True)
    purpose = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(50), default="recorded")  # recorded
    evidence_filename = Column(String(500), nullable=True)
    evidence_original_filename = Column(String(500), nullable=True)
    evidence_mime_type = Column(String(255), nullable=True)
    evidence_size = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    estimate = relationship("Estimate", foreign_keys=[estimate_id])
    allocations = relationship("FundAllocation", back_populates="fund_receipt", cascade="all, delete-orphan")


class FundAllocation(Base):
    __tablename__ = "fund_allocations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_receipt_id = Column(UUID(as_uuid=True), ForeignKey("fund_receipts.id", ondelete="CASCADE"), nullable=False)
    estimate_id = Column(UUID(as_uuid=True), ForeignKey("estimates.id", ondelete="SET NULL"), nullable=True)
    category = Column(String(300), nullable=True)
    amount = Column(Numeric(15, 2), nullable=False)
    purpose = Column(Text, nullable=True)
    responsible_person = Column(String(500), nullable=True)
    allocation_date = Column(Date, default=lambda: date.today(), nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(50), default="allocated")  # allocated, cancelled
    evidence_filename = Column(String(500), nullable=True)
    evidence_original_filename = Column(String(500), nullable=True)
    evidence_mime_type = Column(String(255), nullable=True)
    evidence_size = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    fund_receipt = relationship("FundReceipt", back_populates="allocations")
    estimate = relationship("Estimate", foreign_keys=[estimate_id])


class FundAuditLog(Base):
    __tablename__ = "fund_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(100), nullable=False)  # fund_receipt, fund_allocation, expense
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(String(50), nullable=False)  # created, cancelled, reversed, updated
    field_name = Column(String(200), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    created_by = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project = Column(String(500), nullable=True)
    expense_date = Column(Date, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(300), nullable=True)

    # Traceability: Estimate -> Allocation -> Expense -> Evidence
    estimate_id = Column(UUID(as_uuid=True), ForeignKey("estimates.id", ondelete="SET NULL"), nullable=True)
    estimate_line_item_id = Column(UUID(as_uuid=True), ForeignKey("estimate_line_items.id", ondelete="SET NULL"), nullable=True)
    allocation_id = Column(UUID(as_uuid=True), ForeignKey("fund_allocations.id", ondelete="SET NULL"), nullable=True)

    supplier = Column(String(500), nullable=True)
    payment_method = Column(String(50), nullable=True)
    reference = Column(String(200), nullable=True)
    purpose = Column(Text, nullable=True)
    responsible_person = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)

    currency = Column(String(50), default="FCFA")

    # Purchase information. When quantity and unit price are both present the
    # backend computes the total; a client-supplied total is never trusted.
    quantity = Column(Numeric(12, 2), nullable=True)
    unit = Column(String(50), nullable=True)
    unit_price = Column(Numeric(15, 2), nullable=True)

    # Explicit authorization to exceed the remaining allocation (never silent).
    authorized_by = Column(String(500), nullable=True)
    authorization_reason = Column(Text, nullable=True)

    status = Column(String(50), default="recorded")  # recorded, reversed
    evidence_filename = Column(String(500), nullable=True)
    evidence_original_filename = Column(String(500), nullable=True)
    evidence_mime_type = Column(String(255), nullable=True)
    evidence_size = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    estimate = relationship("Estimate", foreign_keys=[estimate_id])
    estimate_line_item = relationship("EstimateLineItem", foreign_keys=[estimate_line_item_id])
    allocation = relationship("FundAllocation", foreign_keys=[allocation_id])


class Resource(Base):
    """A material/resource master record linked to the project estimate."""

    __tablename__ = "resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project = Column(String(500), nullable=True)
    name = Column(String(500), nullable=False)
    category = Column(String(300), nullable=True)
    unit = Column(String(50), nullable=True)
    currency = Column(String(50), default="FCFA")

    # Optional Phase 1 connections.
    estimate_id = Column(UUID(as_uuid=True), ForeignKey("estimates.id", ondelete="SET NULL"), nullable=True)
    estimate_line_item_id = Column(UUID(as_uuid=True), ForeignKey("estimate_line_items.id", ondelete="SET NULL"), nullable=True)

    # Budget where known. Never overwritten by movements.
    budgeted_quantity = Column(Numeric(12, 2), nullable=True)
    budgeted_cost = Column(Numeric(15, 2), nullable=True)

    notes = Column(Text, nullable=True)
    status = Column(String(50), default="active")  # active, inactive
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    estimate = relationship("Estimate", foreign_keys=[estimate_id])
    estimate_line_item = relationship("EstimateLineItem", foreign_keys=[estimate_line_item_id])
    movements = relationship("ResourceMovement", back_populates="resource", cascade="all, delete-orphan")


class ResourceMovement(Base):
    """A traceable movement in the resource ledger.

    Movement types:
      purchase   : quantity bought (not yet on site). Unit cost / total cost.
      delivery   : quantity received on site. Must not exceed what was purchased.
      usage      : quantity consumed. Must not exceed the available balance.
      adjustment : signed correction to the available balance. Negative values
                   require explicit authorization. Every adjustment needs a reason.
    """

    __tablename__ = "resource_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("resources.id", ondelete="CASCADE"), nullable=False)
    movement_type = Column(String(50), nullable=False)  # purchase, delivery, usage, adjustment

    # Signed quantity. Purchase/delivery/usage are positive; adjustment can be +/-
    quantity = Column(Numeric(12, 2), nullable=False)
    movement_date = Column(Date, default=lambda: date.today(), nullable=False)

    # Purchase financial details (backend computes total = quantity * unit_cost).
    unit_cost = Column(Numeric(15, 2), nullable=True)
    total_cost = Column(Numeric(15, 2), nullable=True)

    # Links
    expense_id = Column(UUID(as_uuid=True), ForeignKey("expenses.id", ondelete="SET NULL"), nullable=True)
    # For a delivery: the purchase movement this delivery is related to (optional).
    related_purchase_movement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("resource_movements.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Purchase / delivery fields
    supplier = Column(String(500), nullable=True)
    reference = Column(String(200), nullable=True)
    receiver = Column(String(500), nullable=True)

    # Usage fields
    project_stage = Column(String(300), nullable=True)
    activity = Column(Text, nullable=True)

    responsible_person = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)

    # Explicit authorization (never silent).
    authorized_by = Column(String(500), nullable=True)
    authorization_reason = Column(Text, nullable=True)

    evidence_filename = Column(String(500), nullable=True)
    evidence_original_filename = Column(String(500), nullable=True)
    evidence_mime_type = Column(String(255), nullable=True)
    evidence_size = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    resource = relationship("Resource", back_populates="movements")
    expense = relationship("Expense", foreign_keys=[expense_id])


class Activity(Base):
    """A scheduled project activity/task tracked for progress and delay."""

    __tablename__ = "activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project = Column(String(500), nullable=True)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    # Links works to an existing estimate/project stage (Phase 1).
    project_stage = Column(String(300), nullable=True)
    estimate_id = Column(UUID(as_uuid=True), ForeignKey("estimates.id", ondelete="SET NULL"), nullable=True)

    planned_start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)
    actual_start_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)

    # not_started, in_progress, completed, delayed, blocked, cancelled
    status = Column(String(50), default="not_started")
    progress_percentage = Column(Integer, default=0)

    responsible_person = Column(String(500), nullable=True)

    # Delay tracking. The reason is recorded by a user; delay itself is always
    # derived from the schedule dates, never guessed.
    delay_reason = Column(String(300), nullable=True)
    delay_reason_detail = Column(Text, nullable=True)

    # Resource/schedule dependency recorded by the user (e.g. "Cement").
    resource_dependency = Column(String(500), nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    estimate = relationship("Estimate", foreign_keys=[estimate_id])


USER_ROLES = ("administrator", "member", "viewer")
ACCOUNT_STATUSES = ("active", "inactive")


class User(Base):
    """An authenticated account. One session controls access to all records."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(300), nullable=False)
    password_hash = Column(String(500), nullable=False)
    role = Column(String(20), default="member")   # administrator, member, viewer
    status = Column(String(20), default="active")  # active, inactive
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    projects = relationship("Project", secondary="user_projects", back_populates="users")


class Project(Base):
    """A construction project shared by its members."""

    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(300), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    users = relationship("User", secondary="user_projects", back_populates="projects")


class UserProject(Base):
    """Membership join between a user and a project."""

    __tablename__ = "user_projects"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Milestone(Base):
    """An important project milestone with planned/actual dates and status."""

    __tablename__ = "milestones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project = Column(String(500), nullable=True)
    name = Column(String(500), nullable=False)
    estimate_id = Column(UUID(as_uuid=True), ForeignKey("estimates.id", ondelete="SET NULL"), nullable=True)
    planned_date = Column(Date, nullable=True)
    actual_date = Column(Date, nullable=True)
    status = Column(String(50), default="pending")  # pending, completed, missed
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    estimate = relationship("Estimate", foreign_keys=[estimate_id])
