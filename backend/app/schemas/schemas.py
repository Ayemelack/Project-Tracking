from datetime import datetime, date
from decimal import Decimal
import unicodedata
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal, Optional


class EstimateLineItemBase(BaseModel):
    item_number: Optional[str] = None
    category: Optional[str] = None
    description: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_cost: Optional[float] = None
    total_cost: Optional[float] = None
    source_page: Optional[int] = None
    section_total_type: Optional[str] = None


class EstimateLineItemCreate(EstimateLineItemBase):
    pass


class EstimateLineItemUpdate(BaseModel):
    item_number: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_cost: Optional[float] = None
    total_cost: Optional[float] = None
    source_page: Optional[int] = None
    section_total_type: Optional[str] = None


class EstimateLineItemResponse(EstimateLineItemBase):
    id: UUID
    estimate_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EstimateBase(BaseModel):
    title: str
    project_name: Optional[str] = None
    reference_number: Optional[str] = None
    contractor: Optional[str] = None
    client: Optional[str] = None
    currency: str = "FCFA"
    notes: Optional[str] = None


class EstimateCreate(EstimateBase):
    line_items: list[EstimateLineItemBase] = []


class EstimateUpdate(BaseModel):
    title: Optional[str] = None
    project_name: Optional[str] = None
    reference_number: Optional[str] = None
    contractor: Optional[str] = None
    client: Optional[str] = None
    currency: Optional[str] = None
    notes: Optional[str] = None

    model_config = {"extra": "forbid"}


class EstimateResponse(EstimateBase):
    id: UUID
    original_filename: str
    status: str
    total_estimated_amount: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EstimateDetailResponse(EstimateResponse):
    line_items: list[EstimateLineItemResponse] = []


class EstimateListResponse(BaseModel):
    estimates: list[EstimateResponse]
    total: int


class ExtractionResult(BaseModel):
    estimate: EstimateBase
    line_items: list[EstimateLineItemBase]
    warnings: list[str] = []
    extraction_notes: list[str] = []


class UploadResponse(BaseModel):
    id: UUID
    filename: str
    status: str
    message: str


class HealthResponse(BaseModel):
    status: str
    version: str


# ---------------------------------------------------------------------------
# Phase 2 — Project Funding & Money Allocation
# ---------------------------------------------------------------------------

SUPPORTED_CURRENCIES = {"FCFA", "XAF"}

class FundReceiptCreate(BaseModel):
    amount: Decimal = Field(
        gt=0,
        le=Decimal("9999999999999.99"),
        max_digits=15,
        decimal_places=2,
        description="Amount received (positive, up to 2 decimal places).",
    )
    currency: str = Field(default="FCFA", max_length=10)
    received_date: date
    source: str = Field(min_length=1, max_length=500)
    reference: Optional[str] = Field(default=None, max_length=200)
    purpose: str = Field(min_length=1, max_length=1000)
    notes: Optional[str] = Field(default=None, max_length=2000)
    estimate_id: Optional[UUID] = None

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, v: str) -> str:
        normalized = v.strip().upper()
        if normalized not in SUPPORTED_CURRENCIES:
            raise ValueError(
                f"Unsupported currency '{v}'. Supported currencies: {', '.join(sorted(SUPPORTED_CURRENCIES))}."
            )
        return normalized

    @field_validator("source", "purpose")
    @classmethod
    def _strip_required_text(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("This field is required.")
        return trimmed

    @field_validator("reference", "notes")
    @classmethod
    def _strip_optional_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed or None


class FundReceiptResponse(BaseModel):
    id: UUID
    estimate_id: Optional[UUID] = None
    amount: Decimal
    currency: str
    received_date: date
    source: str
    reference: Optional[str] = None
    purpose: Optional[str] = None
    notes: Optional[str] = None
    status: str
    evidence_filename: Optional[str] = None
    evidence_original_filename: Optional[str] = None
    evidence_mime_type: Optional[str] = None
    evidence_size: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FundReceiptSummaryItem(FundReceiptResponse):
    allocated_amount: Decimal = Decimal("0.00")
    unallocated_amount: Decimal = Decimal("0.00")


class FundingSummary(BaseModel):
    approved_estimated_amount: Decimal = Decimal("0.00")
    total_received: Decimal = Decimal("0.00")
    total_allocated: Decimal = Decimal("0.00")
    total_unallocated: Decimal = Decimal("0.00")
    funding_coverage_percentage: Optional[float] = None


class FundReceiptListResponse(BaseModel):
    receipts: list[FundReceiptSummaryItem] = []
    total: int
    summary: FundingSummary


class FundAllocationCreate(BaseModel):
    amount: Decimal = Field(gt=0, description="Allocation amount (positive).")
    estimate_id: Optional[UUID] = None
    category: Optional[str] = Field(default=None, max_length=300)
    purpose: Optional[str] = None
    responsible_person: Optional[str] = Field(default=None, max_length=500)
    allocation_date: Optional[date] = None
    notes: Optional[str] = None


class FundAllocationResponse(BaseModel):
    id: UUID
    fund_receipt_id: UUID
    estimate_id: Optional[UUID] = None
    estimate_title: Optional[str] = None
    category: Optional[str] = None
    amount: Decimal
    purpose: Optional[str] = None
    responsible_person: Optional[str] = None
    allocation_date: date
    notes: Optional[str] = None
    status: str
    currency: str = "FCFA"
    evidence_filename: Optional[str] = None
    evidence_original_filename: Optional[str] = None
    evidence_mime_type: Optional[str] = None
    evidence_size: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AllocationListResponse(BaseModel):
    allocations: list[FundAllocationResponse] = []
    total: int
    allocated_amount: Decimal = Decimal("0.00")
    unallocated_amount: Decimal = Decimal("0.00")


class FundReceiptDetailResponse(FundReceiptResponse):
    allocated_amount: Decimal = Decimal("0.00")
    unallocated_amount: Decimal = Decimal("0.00")
    allocations: list[FundAllocationResponse] = []


class FundAuditLogResponse(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    action: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    reason: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateAllocationStatus(BaseModel):
    reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Phase 3 — Expense & Purchase Tracking
# ---------------------------------------------------------------------------

SUPPORTED_PAYMENT_METHODS = {"CASH", "BANK_TRANSFER", "CHEQUE", "MOBILE_MONEY", "CARD", "OTHER"}

MAX_EXPENSE_AMOUNT = Decimal("9999999999999.99")


class ExpenseCreate(BaseModel):
    amount: Optional[Decimal] = Field(
        default=None,
        gt=0,
        le=MAX_EXPENSE_AMOUNT,
        max_digits=15,
        decimal_places=2,
        description="Total expense. If quantity and unit price are provided the backend calculates and enforces this total.",
    )
    expense_date: date
    description: str = Field(min_length=1, max_length=2000)
    project: Optional[str] = Field(default=None, max_length=500)
    category: Optional[str] = Field(default=None, max_length=300)
    estimate_id: Optional[UUID] = None
    estimate_line_item_id: Optional[UUID] = None
    allocation_id: Optional[UUID] = None
    supplier: Optional[str] = Field(default=None, max_length=500)
    payment_method: Optional[str] = Field(default=None, max_length=50)
    reference: Optional[str] = Field(default=None, max_length=200)
    purpose: Optional[str] = Field(default=None, max_length=1000)
    responsible_person: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=2000)
    currency: str = Field(default="FCFA", max_length=10)
    quantity: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    unit: Optional[str] = Field(default=None, max_length=50)
    unit_price: Optional[Decimal] = Field(default=None, gt=0, max_digits=15, decimal_places=2)
    authorized_by: Optional[str] = Field(default=None, max_length=500)
    authorization_reason: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, v: str) -> str:
        normalized = v.strip().upper()
        if normalized not in SUPPORTED_CURRENCIES:
            raise ValueError(
                f"Unsupported currency '{v}'. Supported currencies: {', '.join(sorted(SUPPORTED_CURRENCIES))}."
            )
        return normalized

    @field_validator("payment_method")
    @classmethod
    def _validate_payment_method(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        normalized = v.strip().upper()
        if normalized not in SUPPORTED_PAYMENT_METHODS:
            raise ValueError(
                f"Unsupported payment method '{v}'. Supported: {', '.join(sorted(SUPPORTED_PAYMENT_METHODS))}."
            )
        return normalized

    @field_validator("description")
    @classmethod
    def _strip_required_description(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Description is required.")
        return trimmed

    @field_validator("project", "category", "supplier", "reference", "purpose", "responsible_person", "notes", "unit", "authorized_by", "authorization_reason")
    @classmethod
    def _strip_optional_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed or None


class ExpenseResponse(BaseModel):
    id: UUID
    project: Optional[str] = None
    expense_date: date
    amount: Decimal
    description: str
    category: Optional[str] = None
    estimate_id: Optional[UUID] = None
    estimate_line_item_id: Optional[UUID] = None
    allocation_id: Optional[UUID] = None
    supplier: Optional[str] = None
    payment_method: Optional[str] = None
    reference: Optional[str] = None
    purpose: Optional[str] = None
    responsible_person: Optional[str] = None
    notes: Optional[str] = None
    currency: str = "FCFA"
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    unit_price: Optional[Decimal] = None
    authorized_by: Optional[str] = None
    authorization_reason: Optional[str] = None
    status: str
    evidence_filename: Optional[str] = None
    evidence_original_filename: Optional[str] = None
    evidence_mime_type: Optional[str] = None
    evidence_size: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExpenseDetailResponse(ExpenseResponse):
    estimate_title: Optional[str] = None
    estimate_item_description: Optional[str] = None
    allocation_purpose: Optional[str] = None
    allocation_category: Optional[str] = None
    allocation_currency: Optional[str] = None
    allocation_remaining_amount: Optional[Decimal] = None
    allocation_spent_amount: Optional[Decimal] = None


class ExpenseUpdate(BaseModel):
    # Only non-financial metadata can be edited. Financial values (amount,
    # purchase details, date, links, currency, status) require an explicit
    # reversal + re-entry so history is preserved.
    description: Optional[str] = Field(default=None, min_length=1, max_length=2000)
    project: Optional[str] = Field(default=None, max_length=500)
    category: Optional[str] = Field(default=None, max_length=300)
    supplier: Optional[str] = Field(default=None, max_length=500)
    payment_method: Optional[str] = Field(default=None, max_length=50)
    reference: Optional[str] = Field(default=None, max_length=200)
    purpose: Optional[str] = Field(default=None, max_length=1000)
    responsible_person: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=2000)

    model_config = {"extra": "forbid"}

    @field_validator("payment_method")
    @classmethod
    def _validate_payment_method(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        normalized = v.strip().upper()
        if normalized not in SUPPORTED_PAYMENT_METHODS:
            raise ValueError(
                f"Unsupported payment method '{v}'. Supported: {', '.join(sorted(SUPPORTED_PAYMENT_METHODS))}."
            )
        return normalized

    @field_validator("description")
    @classmethod
    def _strip_required_description(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Description is required.")
        return trimmed

    @field_validator("project", "category", "supplier", "reference", "purpose", "responsible_person", "notes")
    @classmethod
    def _strip_optional_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed or None


class ExpenseCategoryItem(BaseModel):
    category: str
    total: Decimal = Decimal("0.00")


class ExpenseAllocationItem(BaseModel):
    allocation_id: UUID
    allocation_purpose: Optional[str] = None
    allocation_category: Optional[str] = None
    estimate_title: Optional[str] = None
    allocated_amount: Decimal = Decimal("0.00")
    spent_amount: Decimal = Decimal("0.00")
    remaining_amount: Decimal = Decimal("0.00")
    currency: str = "FCFA"


class ExpenseBudgetComparisonItem(BaseModel):
    estimate_id: UUID
    estimate_title: str
    estimated_amount: Decimal = Decimal("0.00")
    actual_expenditure: Decimal = Decimal("0.00")
    variance_amount: Decimal = Decimal("0.00")
    status: str
    currency: str = "FCFA"


class ExpenseSummary(BaseModel):
    total_expenses: Decimal = Decimal("0.00")
    total_authorized_excess: Decimal = Decimal("0.00")
    by_category: list[ExpenseCategoryItem] = []
    allocation_breakdown: list[ExpenseAllocationItem] = []
    budget_comparison: list[ExpenseBudgetComparisonItem] = []


class ExpenseListResponse(BaseModel):
    expenses: list[ExpenseResponse] = []
    total: int
    summary: ExpenseSummary


class AllocationExpenseListResponse(BaseModel):
    allocations: list[ExpenseAllocationItem] = []
    total: int


# ---------------------------------------------------------------------------
# Phase 4 — Material & Resource Accountability
# ---------------------------------------------------------------------------

RESOURCE_MOVEMENT_TYPES = {"purchase", "delivery", "usage", "adjustment"}

MAX_RESOURCE_QUANTITY = Decimal("9999999999.99")
MAX_RESOURCE_COST = Decimal("9999999999999.99")


class ResourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    project: Optional[str] = Field(default=None, max_length=500)
    category: Optional[str] = Field(default=None, max_length=300)
    unit: Optional[str] = Field(default=None, max_length=50)
    currency: str = Field(default="FCFA", max_length=10)
    estimate_id: Optional[UUID] = None
    estimate_line_item_id: Optional[UUID] = None
    budgeted_quantity: Optional[Decimal] = Field(
        default=None, gt=0, le=MAX_RESOURCE_QUANTITY, max_digits=12, decimal_places=2
    )
    budgeted_cost: Optional[Decimal] = Field(
        default=None, gt=0, le=MAX_RESOURCE_COST, max_digits=15, decimal_places=2
    )
    notes: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, v: str) -> str:
        normalized = v.strip().upper()
        if normalized not in SUPPORTED_CURRENCIES:
            raise ValueError(
                f"Unsupported currency '{v}'. Supported currencies: {', '.join(sorted(SUPPORTED_CURRENCIES))}."
            )
        return normalized

    @field_validator("name")
    @classmethod
    def _name_required(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Resource name is required.")
        return trimmed

    @field_validator("project", "category", "unit", "notes")
    @classmethod
    def _strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed or None


class ResourceQuantityMixin(BaseModel):
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2)

    @field_validator("quantity")
    @classmethod
    def _quantity_bounds(cls, v: Decimal) -> Decimal:
        if v > MAX_RESOURCE_QUANTITY:
            raise ValueError(f"Quantity exceeds the supported maximum ({MAX_RESOURCE_QUANTITY}).")
        return v


class ResourceMovementCommon(BaseModel):
    movement_date: Optional[date] = None
    supplier: Optional[str] = Field(default=None, max_length=500)
    reference: Optional[str] = Field(default=None, max_length=200)
    responsible_person: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("supplier", "reference", "responsible_person", "notes")
    @classmethod
    def _strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed or None


class ResourcePurchaseCreate(ResourceQuantityMixin, ResourceMovementCommon):
    unit_cost: Decimal = Field(gt=0, le=MAX_RESOURCE_COST, max_digits=15, decimal_places=2)
    expense_id: Optional[UUID] = None

    @field_validator("unit_cost")
    @classmethod
    def _cost_bounds(cls, v: Decimal) -> Decimal:
        return v


class ResourceDeliveryCreate(ResourceQuantityMixin, ResourceMovementCommon):
    linked_purchase_movement_id: Optional[UUID] = None
    receiver: Optional[str] = Field(default=None, max_length=500)


class ResourceUsageCreate(ResourceQuantityMixin, ResourceMovementCommon):
    project_stage: Optional[str] = Field(default=None, max_length=300)
    activity: Optional[str] = Field(default=None, max_length=2000)


class ResourceAdjustmentCreate(ResourceMovementCommon):
    # Signed quantity: positive adds stock, negative removes it. Zero is invalid.
    quantity: Decimal = Field(max_digits=12, decimal_places=2)
    authorized_by: Optional[str] = Field(default=None, max_length=500)
    authorization_reason: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("quantity")
    @classmethod
    def _quantity_nonzero(cls, v: Decimal) -> Decimal:
        if v == 0:
            raise ValueError("Adjustment quantity cannot be zero.")
        if abs(v) > MAX_RESOURCE_QUANTITY:
            raise ValueError(
                f"Adjustment quantity exceeds the supported maximum ({MAX_RESOURCE_QUANTITY})."
            )
        return v

    @field_validator("authorized_by", "authorization_reason")
    @classmethod
    def _strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed or None


class ResourceMovementResponse(BaseModel):
    id: UUID
    resource_id: UUID
    movement_type: str
    quantity: Decimal
    movement_date: date
    unit_cost: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    expense_id: Optional[UUID] = None
    expense_description: Optional[str] = None
    related_purchase_movement_id: Optional[UUID] = None
    supplier: Optional[str] = None
    reference: Optional[str] = None
    receiver: Optional[str] = None
    project_stage: Optional[str] = None
    activity: Optional[str] = None
    responsible_person: Optional[str] = None
    notes: Optional[str] = None
    authorized_by: Optional[str] = None
    authorization_reason: Optional[str] = None
    evidence_filename: Optional[str] = None
    evidence_original_filename: Optional[str] = None
    evidence_mime_type: Optional[str] = None
    evidence_size: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResourceResponse(BaseModel):
    id: UUID
    project: Optional[str] = None
    name: str
    category: Optional[str] = None
    unit: Optional[str] = None
    currency: str = "FCFA"
    estimate_id: Optional[UUID] = None
    estimate_title: Optional[str] = None
    estimate_line_item_id: Optional[UUID] = None
    estimate_item_description: Optional[str] = None
    budgeted_quantity: Optional[Decimal] = None
    budgeted_cost: Optional[Decimal] = None
    notes: Optional[str] = None
    status: str = "active"
    # Computed from the movement ledger (never stored/typed by users).
    purchased_quantity: Decimal = Decimal("0.00")
    delivered_quantity: Decimal = Decimal("0.00")
    used_quantity: Decimal = Decimal("0.00")
    adjustment_quantity: Decimal = Decimal("0.00")
    remaining_quantity: Decimal = Decimal("0.00")
    pending_delivery_quantity: Decimal = Decimal("0.00")
    total_purchase_cost: Decimal = Decimal("0.00")
    cost_variance: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResourceExpenseInfo(BaseModel):
    id: UUID
    expense_date: date
    amount: Decimal
    description: str
    reference: Optional[str] = None
    currency: str = "FCFA"


class ResourceDetailResponse(ResourceResponse):
    movements: list[ResourceMovementResponse] = []
    related_expenses: list[ResourceExpenseInfo] = []


class ResourceListResponse(BaseModel):
    resources: list[ResourceResponse] = []
    total: int


# ---------------------------------------------------------------------------
# Phase 5 — Project Schedule, Progress & Delay Tracking
# ---------------------------------------------------------------------------

ACTIVITY_STATUSES = {"not_started", "in_progress", "completed", "delayed", "blocked", "cancelled"}
MILESTONE_STATUSES = {"pending", "completed", "missed"}


def _validate_date_range(start: Optional[date], end: Optional[date]) -> None:
    if start is not None and end is not None and end < start:
        raise ValueError("The end date cannot be before the start date.")


def _validate_progress(value: int) -> int:
    if value < 0 or value > 100:
        raise ValueError("Progress percentage must be between 0 and 100.")
    return value


class ActivityBase(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    project: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = Field(default=None, max_length=4000)
    project_stage: Optional[str] = Field(default=None, max_length=300)
    estimate_id: Optional[UUID] = None
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    status: str = Field(default="not_started", max_length=50)
    progress_percentage: int = Field(default=0)
    responsible_person: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=4000)
    delay_reason: Optional[str] = Field(default=None, max_length=300)
    delay_reason_detail: Optional[str] = Field(default=None, max_length=4000)
    resource_dependency: Optional[str] = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def _name_required(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Activity name is required.")
        return trimmed

    @field_validator("status")
    @classmethod
    def _status_allowed(cls, v: str) -> str:
        normalized = v.strip().lower().replace(" ", "_")
        if normalized not in ACTIVITY_STATUSES:
            raise ValueError(
                f"Invalid activity status '{v}'. Allowed: {', '.join(sorted(ACTIVITY_STATUSES))}."
            )
        return normalized

    @field_validator("progress_percentage")
    @classmethod
    def _progress_bounds(cls, v: int) -> int:
        return _validate_progress(v)

    @field_validator(
        "project", "description", "project_stage", "responsible_person", "notes",
        "delay_reason", "delay_reason_detail", "resource_dependency",
    )
    @classmethod
    def _strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed or None

    @model_validator(mode="after")
    def _dates_ordered(self):
        _validate_date_range(self.planned_start_date, self.planned_end_date)
        _validate_date_range(self.actual_start_date, self.actual_end_date)
        return self


class ActivityCreate(ActivityBase):
    pass


class ActivityUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=500)
    project: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = Field(default=None, max_length=4000)
    project_stage: Optional[str] = Field(default=None, max_length=300)
    estimate_id: Optional[UUID] = None
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=50)
    progress_percentage: Optional[int] = Field(default=None)
    responsible_person: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=4000)
    delay_reason: Optional[str] = Field(default=None, max_length=300)
    delay_reason_detail: Optional[str] = Field(default=None, max_length=4000)
    resource_dependency: Optional[str] = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def _name_required(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Activity name cannot be empty.")
        return trimmed

    @field_validator("status")
    @classmethod
    def _status_allowed(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        normalized = v.strip().lower().replace(" ", "_")
        if normalized not in ACTIVITY_STATUSES:
            raise ValueError(
                f"Invalid activity status '{v}'. Allowed: {', '.join(sorted(ACTIVITY_STATUSES))}."
            )
        return normalized

    @field_validator("progress_percentage")
    @classmethod
    def _progress_bounds(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return None
        return _validate_progress(v)

    @field_validator(
        "project", "description", "project_stage", "responsible_person", "notes",
        "delay_reason", "delay_reason_detail", "resource_dependency",
    )
    @classmethod
    def _strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed or None

    @model_validator(mode="after")
    def _dates_ordered(self):
        _validate_date_range(self.planned_start_date, self.planned_end_date)
        _validate_date_range(self.actual_start_date, self.actual_end_date)
        return self


class ActivityResponse(ActivityBase):
    id: UUID
    estimate_title: Optional[str] = None
    # Computed from schedule dates (never stored/typed by users).
    is_delayed: bool = False
    delay_days: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ActivitySummaryResponse(BaseModel):
    total_activities: int
    total_completed: int
    total_in_progress: int
    total_delayed: int
    total_blocked: int
    total_not_started: int
    total_cancelled: int
    # Simple average of activity progress_percentage excluding cancelled
    # activities. This is an indicative figure, not an earned-value measure.
    overall_progress: Optional[float] = None
    progress_calculation: str = (
        "Simple average of activity progress_percentage across all activities "
        "excluding cancelled activities. This is an indicative figure, not an "
        "earned-value measurement."
    )


class ActivityListResponse(BaseModel):
    activities: list[ActivityResponse] = []
    total: int
    summary: Optional[ActivitySummaryResponse] = None


class MilestoneBase(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    project: Optional[str] = Field(default=None, max_length=500)
    estimate_id: Optional[UUID] = None
    planned_date: Optional[date] = None
    actual_date: Optional[date] = None
    status: str = Field(default="pending", max_length=50)
    notes: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("name")
    @classmethod
    def _name_required(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Milestone name is required.")
        return trimmed

    @field_validator("status")
    @classmethod
    def _status_allowed(cls, v: str) -> str:
        normalized = v.strip().lower()
        if normalized not in MILESTONE_STATUSES:
            raise ValueError(
                f"Invalid milestone status '{v}'. Allowed: {', '.join(sorted(MILESTONE_STATUSES))}."
            )
        return normalized

    @field_validator("project", "notes")
    @classmethod
    def _strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed or None


class MilestoneCreate(MilestoneBase):
    pass


class MilestoneUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=500)
    project: Optional[str] = Field(default=None, max_length=500)
    estimate_id: Optional[UUID] = None
    planned_date: Optional[date] = None
    actual_date: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("name")
    @classmethod
    def _name_required(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Milestone name cannot be empty.")
        return trimmed

    @field_validator("status")
    @classmethod
    def _status_allowed(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        normalized = v.strip().lower()
        if normalized not in MILESTONE_STATUSES:
            raise ValueError(
                f"Invalid milestone status '{v}'. Allowed: {', '.join(sorted(MILESTONE_STATUSES))}."
            )
        return normalized

    @field_validator("project", "notes")
    @classmethod
    def _strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed or None


class MilestoneResponse(MilestoneBase):
    id: UUID
    estimate_title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MilestoneListResponse(BaseModel):
    milestones: list[MilestoneResponse] = []
    total: int


# ---------------------------------------------------------------------------
# Stage A: Authentication, users, roles and project membership
# ---------------------------------------------------------------------------

USER_ROLES = ("administrator", "member", "viewer")
ACCOUNT_STATUSES = ("active", "inactive")


def _is_valid_full_name(value: str) -> bool:
    """Accept letters, spaces, hyphens, apostrophes, periods and combining marks.

    Rejects empty values and meaningless input such as '12345' or '123 John'.
    """
    if not value:
        return False
    has_letter = False
    for ch in value:
        if ch.isalpha():
            has_letter = True
        elif ch in " -.'’" or unicodedata.category(ch).startswith("M"):
            continue
        else:
            return False
    return has_letter


_USERNAME_SEPARATORS = "._-"
_EMAIL_LOCAL_SYMBOLS = "._-"


def _is_valid_email(value: str) -> bool:
    """Structural email check for email-shaped identifiers (e.g. jane@x.com).

    Usernames that happen to look like email addresses are validated as emails
    so malformed values such as 'abc@', '@example', '@@' or 'a@b@c' are rejected.
    """
    if value.count("@") != 1:
        return False
    local, _, domain = value.partition("@")
    if not local or not domain:
        return False
    if local[0] in "._" or local[-1] in "._":
        return False
    if ".." in local or ".." in domain:
        return False
    if not all(ch.isalnum() or ch in _EMAIL_LOCAL_SYMBOLS for ch in local):
        return False
    labels = domain.split(".")
    if len(labels) < 2:
        return False
    for label in labels:
        if not label or len(label) > 63:
            return False
        if label[0] == "-" or label[-1] == "-":
            return False
        if not all(ch.isalnum() or ch == "-" for ch in label):
            return False
    return True


def _is_valid_username_or_email(value: str) -> bool:
    """Return True for a valid username or a valid email address.

    Username policy (2-100 chars): letters/digits/underscore/hyphen/period, at
    least one alphanumeric character, no leading/trailing separators and no
    consecutive separators. Values containing '@' must be structurally valid
    email addresses.
    """
    if not (2 <= len(value) <= 100):
        return False
    if any(ch.isspace() for ch in value):
        return False
    if "@" in value:
        return _is_valid_email(value)
    if not any(ch.isalnum() for ch in value):
        return False
    if value[0] in _USERNAME_SEPARATORS or value[-1] in _USERNAME_SEPARATORS:
        return False
    for i in range(len(value) - 1):
        if value[i] in _USERNAME_SEPARATORS and value[i + 1] in _USERNAME_SEPARATORS:
            return False
    return all(ch.isalnum() or ch in _USERNAME_SEPARATORS for ch in value)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class UserPublic(BaseModel):
    id: UUID
    username: str
    full_name: str
    role: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class UserCreateAdmin(BaseModel):
    username: str = Field(min_length=2, max_length=100)
    full_name: str = Field(min_length=1, max_length=300)
    password: str = Field(min_length=8, max_length=200)
    role: str = "member"

    @field_validator("username")
    @classmethod
    def _username_clean(cls, v: str) -> str:
        trimmed = v.strip().lower()
        if not trimmed:
            raise ValueError("Username cannot be empty.")
        if not _is_valid_username_or_email(trimmed):
            raise ValueError("Please enter a valid username or email.")
        return trimmed

    @field_validator("full_name")
    @classmethod
    def _full_name_clean(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Full name cannot be empty.")
        if not _is_valid_full_name(trimmed):
            raise ValueError("Please enter a valid full name.")
        return trimmed

    @field_validator("role")
    @classmethod
    def _role_allowed(cls, v: str) -> str:
        normalized = v.strip().lower()
        if normalized not in USER_ROLES:
            raise ValueError(
                f"Invalid role '{v}'. Allowed: {', '.join(sorted(USER_ROLES))}."
            )
        return normalized


class UserRegister(BaseModel):
    username: str = Field(min_length=2, max_length=100)
    full_name: str = Field(min_length=1, max_length=300)
    password: str = Field(min_length=8, max_length=200)
    confirm_password: str = Field(min_length=1, max_length=200)
    admin_registration_secret: Optional[str] = Field(default=None, max_length=200)

    # Reject unknown fields (e.g. role, is_admin) so a client can never request
    # privilege escalation. Role is always decided server-side.
    model_config = {"extra": "forbid"}

    @field_validator("username")
    @classmethod
    def _username_clean(cls, v: str) -> str:
        trimmed = v.strip().lower()
        if not trimmed:
            raise ValueError("Username cannot be empty.")
        if not _is_valid_username_or_email(trimmed):
            raise ValueError("Please enter a valid username or email.")
        return trimmed

    @field_validator("full_name")
    @classmethod
    def _full_name_clean(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Full name cannot be empty.")
        if not _is_valid_full_name(trimmed):
            raise ValueError("Please enter a valid full name.")
        return trimmed

    @field_validator("confirm_password")
    @classmethod
    def _passwords_match(cls, v: str, info) -> str:
        password = info.data.get("password")
        if password and v != password:
            raise ValueError("Passwords do not match.")
        return v


class RegisterResponse(BaseModel):
    message: str
    user: UserPublic


class AuthStatusResponse(BaseModel):
    has_users: bool


class PasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=200)
    confirm_password: str = Field(min_length=1, max_length=200)

    # Reject unknown fields so a client can never attach extra data (for
    # example a target user id) to a reset request.
    model_config = {"extra": "forbid"}

    @field_validator("confirm_password")
    @classmethod
    def _passwords_match(cls, v: str, info) -> str:
        new_password = info.data.get("new_password")
        if new_password and v != new_password:
            raise ValueError("Passwords do not match.")
        return v


class PasswordResetResponse(BaseModel):
    message: str


class UserUpdateAdmin(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=300)
    password: Optional[str] = Field(default=None, min_length=8, max_length=200)
    role: Optional[str] = None
    status: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def _full_name_clean_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Full name cannot be empty.")
        if not _is_valid_full_name(trimmed):
            raise ValueError("Please enter a valid full name.")
        return trimmed

    @field_validator("role")
    @classmethod
    def _role_allowed_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        normalized = v.strip().lower()
        if normalized not in USER_ROLES:
            raise ValueError(
                f"Invalid role '{v}'. Allowed: {', '.join(sorted(USER_ROLES))}."
            )
        return normalized

    @field_validator("status")
    @classmethod
    def _status_allowed(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        normalized = v.strip().lower()
        if normalized not in ACCOUNT_STATUSES:
            raise ValueError(
                f"Invalid account status '{v}'. Allowed: {', '.join(sorted(ACCOUNT_STATUSES))}."
            )
        return normalized


class UserListResponse(BaseModel):
    users: list[UserPublic] = []
    total: int


class ProjectPublic(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    description: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def _name_clean(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Project name cannot be empty.")
        return trimmed


class ProjectListResponse(BaseModel):
    projects: list[ProjectPublic] = []
    total: int


class MeResponse(BaseModel):
    user: UserPublic
    projects: list[ProjectPublic] = []


# ---------------------------------------------------------------------------
# Stage B: Assistant
# ---------------------------------------------------------------------------

class AssistantReference(BaseModel):
    """A record the reply is based on, so the user can navigate straight to it."""

    entity_type: str  # estimate, fund_receipt, fund_allocation, expense, resource, activity, milestone
    entity_id: UUID
    label: str
    href: str  # frontend route, e.g. "/estimates/<id>"


class AssistantAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)

    @field_validator("question")
    @classmethod
    def _question_clean(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Question cannot be empty.")
        return trimmed


class AssistantReply(BaseModel):
    intent: str
    reply: str
    references: list[AssistantReference] = []


class AssistantStreamEvent(BaseModel):
    """Time-ordered event produced while an answer is generated.

    - status: progress note (thinking / consulting the records)
    - tool: a controlled backend tool is being executed
    - delta: a chunk of the answer text (streamed, never artificially delayed)
    - done: final event carrying the structured reply + record references
    - error: a professional error message; the interaction is over after it
    """

    type: Literal["status", "tool", "delta", "done", "error"]
    text: Optional[str] = None
    tool: Optional[str] = None
    intent: Optional[str] = None
    references: list[AssistantReference] = []


class AssistantAttentionItem(BaseModel):
    """A fact computed from live records that may deserve attention."""

    kind: str
    message: str
    references: list[AssistantReference] = []


class AssistantBriefing(BaseModel):
    """Pre-chat context for the AI Project Employee, computed from live data.

    Greeting and project identity come from the authenticated session and the
    actual project record, never from hard-coded values. Attention items are
    computed from the same database the user can read.
    """

    greeting: str
    project_name: Optional[str] = None
    attention: list[AssistantAttentionItem] = []
    suggestions: list[str] = []
