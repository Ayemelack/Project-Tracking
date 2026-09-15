from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.models import (
    Expense,
    Estimate,
    EstimateLineItem,
    FundAllocation,
)
from app.schemas.schemas import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseDetailResponse,
    ExpenseSummary,
    ExpenseCategoryItem,
    ExpenseAllocationItem,
    ExpenseBudgetComparisonItem,
    MAX_EXPENSE_AMOUNT,
)
from app.repositories.expense_repository import expense_repo
from app.repositories.fund_repository import (
    fund_allocation_repo,
    fund_audit_repo,
)
from app.services import fund_service
from app.services.storage_service import storage_service


ZERO = Decimal("0.00")


def money(value) -> Decimal:
    return fund_service.money(value)


def spent_per_allocation(db: Session) -> dict[UUID, Decimal]:
    return expense_repo.spent_total_per_allocation(db)


def _estimate_title(db: Session, estimate_id: UUID | None) -> str | None:
    if not estimate_id:
        return None
    estimate = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    return estimate.title if estimate else None


def _require_estimate(db: Session, estimate_id: UUID) -> Estimate:
    estimate = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    return estimate


def _require_allocation(db: Session, allocation_id: UUID) -> FundAllocation:
    allocation = fund_allocation_repo.get_by_id(db, allocation_id)
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    return allocation


def resolve_purchase_amount(data: ExpenseCreate) -> Decimal:
    """Backend is the only authority on financial totals."""
    has_quantity = data.quantity is not None
    has_unit_price = data.unit_price is not None

    if has_quantity or has_unit_price:
        if not (has_quantity and has_unit_price):
            raise HTTPException(
                status_code=422,
                detail="Quantity and unit price must both be provided when recording purchase information.",
            )
        raw = data.quantity * data.unit_price
        if raw > MAX_EXPENSE_AMOUNT:
            raise HTTPException(
                status_code=422,
                detail=f"Calculated total from quantity and unit price ({raw}) exceeds the supported maximum.",
            )
        computed = raw.quantize(Decimal("0.01"))
        if data.amount is not None and money(data.amount) != computed:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Calculated total from quantity and unit price is {computed}, which does not match "
                    f"the provided amount of {money(data.amount)}. The backend calculates totals, so "
                    f"please correct the amount or remove it."
                ),
            )
        return computed

    if data.amount is None:
        raise HTTPException(
            status_code=422,
            detail="An amount is required unless quantity and unit price are provided.",
        )
    return money(data.amount)


def allocation_spent(db: Session, allocation_id: UUID) -> Decimal:
    return money(expense_repo.spent_total_per_allocation(db).get(allocation_id, ZERO))


def allocation_remaining_amount(db: Session, allocation: FundAllocation) -> Decimal:
    return money(allocation.amount) - allocation_spent(db, allocation.id)


def create_expense(db: Session, data: ExpenseCreate) -> Expense:
    estimate_id = data.estimate_id

    if data.allocation_id:
        allocation = _require_allocation(db, data.allocation_id)
        if allocation.status == "cancelled":
            raise HTTPException(
                status_code=409,
                detail="Expenses cannot be linked to a cancelled allocation.",
            )
        receipt_currency = allocation.fund_receipt.currency if allocation.fund_receipt else None
        if receipt_currency and data.currency.upper() != receipt_currency.upper():
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Expense currency {data.currency.upper()} does not match the "
                    f"allocation currency {receipt_currency.upper()}."
                ),
            )
        if estimate_id is None and allocation.estimate_id:
            estimate_id = allocation.estimate_id

    if estimate_id:
        _require_estimate(db, estimate_id)

    if data.estimate_line_item_id:
        item = db.query(EstimateLineItem).filter(EstimateLineItem.id == data.estimate_line_item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Estimate line item not found")
        if estimate_id and item.estimate_id != estimate_id:
            raise HTTPException(
                status_code=422,
                detail="The estimate line item does not belong to the linked estimate.",
            )
        if estimate_id is None:
            estimate_id = item.estimate_id

    amount = resolve_purchase_amount(data)

    authorized_excess = False
    if data.allocation_id:
        remaining = allocation_remaining_amount(db, allocation)
        if amount > remaining:
            if not data.authorized_by:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Expense of {amount} exceeds the remaining allocation of "
                        f"{remaining}. Provide authorized_by to record an explicitly "
                        f"authorized expense, or reduce the amount."
                    ),
                )
            authorized_excess = True

    entity = Expense(
        project=data.project,
        expense_date=data.expense_date,
        amount=amount,
        description=data.description,
        category=data.category,
        estimate_id=estimate_id,
        estimate_line_item_id=data.estimate_line_item_id,
        allocation_id=data.allocation_id,
        supplier=data.supplier,
        payment_method=data.payment_method,
        reference=data.reference,
        purpose=data.purpose,
        responsible_person=data.responsible_person,
        notes=data.notes,
        currency=data.currency.upper(),
        quantity=data.quantity,
        unit=data.unit,
        unit_price=data.unit_price,
        authorized_by=data.authorized_by,
        authorization_reason=data.authorization_reason,
        status="recorded",
    )
    expense = expense_repo.create(db, entity)
    fund_audit_repo.log(
        db,
        entity_type="expense",
        entity_id=expense.id,
        action="created",
        new_value=(
            f"amount={expense.amount}, currency={expense.currency}, "
            f"expense_date={expense.expense_date}, allocation_id={expense.allocation_id}, "
            f"estimate_id={expense.estimate_id}"
        ),
    )
    if authorized_excess:
        fund_audit_repo.log(
            db,
            entity_type="expense",
            entity_id=expense.id,
            action="authorized_excess",
            new_value=(
                f"amount={expense.amount}, remaining_allocation={remaining}, "
                f"authorized_by={data.authorized_by}"
            ),
            reason=data.authorization_reason,
        )
    return expense


def update_expense(db: Session, expense_id: UUID, data: ExpenseUpdate) -> Expense:
    expense = expense_repo.get_by_id(db, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if expense.status == "reversed":
        raise HTTPException(
            status_code=409,
            detail="A reversed expense cannot be edited. Record a correction instead.",
        )

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No editable fields provided.")

    updated = expense_repo.update(db, expense, update_data)
    fund_audit_repo.log(
        db,
        entity_type="expense",
        entity_id=expense.id,
        action="updated",
        new_value=", ".join(f"{k}={v}" for k, v in update_data.items()),
    )
    return updated


def reverse_expense(db: Session, expense_id: UUID, reason: str | None = None) -> Expense:
    expense = expense_repo.get_by_id(db, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if expense.status != "recorded":
        raise HTTPException(status_code=409, detail="Expense is not in a reversible state")

    fund_audit_repo.log(
        db,
        entity_type="expense",
        entity_id=expense.id,
        action="reversed",
        field_name="status",
        old_value=str(expense.amount),
        new_value="0.00",
        reason=reason,
    )
    reversed_expense = expense_repo.set_status(db, expense, "reversed")
    return reversed_expense


# ---------------------------------------------------------------------------
# Responses & financial calculations
# ---------------------------------------------------------------------------

def build_expense_response(expense: Expense) -> ExpenseResponse:
    return ExpenseResponse.model_validate(expense)


def build_expense_detail(db: Session, expense: Expense) -> ExpenseDetailResponse:
    detail = ExpenseDetailResponse.model_validate(expense)
    detail.estimate_title = _estimate_title(db, expense.estimate_id)
    if expense.estimate_line_item_id:
        item = db.query(EstimateLineItem).filter(EstimateLineItem.id == expense.estimate_line_item_id).first()
        detail.estimate_item_description = item.description if item else None
    if expense.allocation_id:
        allocation = db.query(FundAllocation).filter(FundAllocation.id == expense.allocation_id).first()
        if allocation:
            detail.allocation_purpose = allocation.purpose
            detail.allocation_category = allocation.category
            detail.allocation_currency = (
                allocation.fund_receipt.currency if allocation.fund_receipt else "FCFA"
            )
            detail.allocation_spent_amount = allocation_spent(db, allocation.id)
            detail.allocation_remaining_amount = allocation_remaining_amount(db, allocation)
    return detail


def build_budget_comparison(db: Session) -> list[ExpenseBudgetComparisonItem]:
    confirmed = db.query(Estimate).filter(Estimate.status == "confirmed").all()
    if not confirmed:
        return []

    spent_by_estimate = expense_repo.spent_total_per_estimate(db)
    # Expenses that carry no direct estimate link but belong to an allocation
    # whose estimate matches. Expenses created through an allocation always get
    # an estimate_id, so this never double counts.
    unclaimed_per_allocation = expense_repo.spent_total_per_allocation_without_estimate(db)

    allocations_by_estimate: dict[UUID, list[UUID]] = {}
    allocations = (
        db.query(FundAllocation)
        .filter(FundAllocation.status == "allocated", FundAllocation.estimate_id.isnot(None))
        .all()
    )
    for allocation in allocations:
        allocations_by_estimate.setdefault(allocation.estimate_id, []).append(allocation.id)

    items: list[ExpenseBudgetComparisonItem] = []
    for estimate in confirmed:
        actual = money(spent_by_estimate.get(estimate.id, ZERO))
        for allocation_id in allocations_by_estimate.get(estimate.id, []):
            actual += money(unclaimed_per_allocation.get(allocation_id, ZERO))

        if actual <= ZERO:
            continue

        estimated = money(estimate.total_estimated_amount)
        variance = estimated - actual
        if actual > estimated:
            status = "OVER ESTIMATE"
        elif actual == estimated:
            status = "ON BUDGET"
        else:
            status = "UNDER ESTIMATE"

        items.append(
            ExpenseBudgetComparisonItem(
                estimate_id=estimate.id,
                estimate_title=estimate.title,
                estimated_amount=estimated,
                actual_expenditure=actual,
                variance_amount=variance,
                status=status,
                currency=estimate.currency or "FCFA",
            )
        )
    return items


def get_expense_summary(db: Session) -> ExpenseSummary:
    total_expenses = money(expense_repo.total_recorded(db))

    by_category = [
        ExpenseCategoryItem(category=category or "Uncategorized", total=money(total))
        for category, total in expense_repo.totals_by_category(db)
    ]

    spent_per_allocation = expense_repo.spent_total_per_allocation(db)
    allocated_allocations = (
        db.query(FundAllocation).filter(FundAllocation.status == "allocated").all()
    )

    allocation_breakdown: list[ExpenseAllocationItem] = []
    allocations_by_id: dict[UUID, FundAllocation] = {}
    for allocation in allocated_allocations:
        allocations_by_id[allocation.id] = allocation
        spent = money(spent_per_allocation.get(allocation.id, ZERO))
        remaining = money(allocation.amount) - spent
        allocation_breakdown.append(
            ExpenseAllocationItem(
                allocation_id=allocation.id,
                allocation_purpose=allocation.purpose,
                allocation_category=allocation.category,
                estimate_title=_estimate_title(db, allocation.estimate_id),
                allocated_amount=money(allocation.amount),
                spent_amount=spent,
                remaining_amount=remaining,
                currency=(
                    allocation.fund_receipt.currency if allocation.fund_receipt else "FCFA"
                ),
            )
        )

    authorized_excess_total = ZERO
    for expense in expense_repo.each_recorded(db):
        if expense.allocation_id and expense.authorized_by:
            allocation = allocations_by_id.get(expense.allocation_id)
            if allocation and expense.amount > money(allocation.amount):
                authorized_excess_total += expense.amount - money(allocation.amount)

    return ExpenseSummary(
        total_expenses=total_expenses,
        total_authorized_excess=money(authorized_excess_total),
        by_category=by_category,
        allocation_breakdown=allocation_breakdown,
        budget_comparison=build_budget_comparison(db),
    )


# ---------------------------------------------------------------------------
# Supporting evidence (reuses Phase 1/2 storage architecture)
# ---------------------------------------------------------------------------

def _save_evidence(file: UploadFile) -> tuple[str, str, str, int]:
    content = fund_service._validate_evidence_file(file)
    original_filename, stored_filename = storage_service.save_bytes(file.filename or "evidence", content)
    return original_filename, stored_filename, file.content_type or "", len(content)


def attach_expense_evidence(db: Session, expense_id: UUID, file: UploadFile) -> Expense:
    expense = expense_repo.get_by_id(db, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    original, stored, mime, size = _save_evidence(file)
    expense.evidence_filename = stored
    expense.evidence_original_filename = original
    expense.evidence_mime_type = mime
    expense.evidence_size = size
    expense = expense_repo.update(db, expense, {
        "evidence_filename": stored,
        "evidence_original_filename": original,
        "evidence_mime_type": mime,
        "evidence_size": size,
    })
    fund_audit_repo.log(
        db,
        entity_type="expense",
        entity_id=expense.id,
        action="evidence_attached",
        new_value=original,
    )
    return expense


def clear_expense_evidence(db: Session, expense_id: UUID) -> Expense:
    expense = expense_repo.get_by_id(db, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    previous = expense.evidence_original_filename
    expense = expense_repo.update(db, expense, {
        "evidence_filename": None,
        "evidence_original_filename": None,
        "evidence_mime_type": None,
        "evidence_size": None,
    })
    fund_audit_repo.log(
        db,
        entity_type="expense",
        entity_id=expense.id,
        action="evidence_removed",
        old_value=previous,
    )
    return expense


def expense_evidence_file_path(db: Session, expense_id: UUID) -> tuple[Path, str]:
    expense = expense_repo.get_by_id(db, expense_id)
    if not expense or not expense.evidence_filename:
        raise HTTPException(status_code=404, detail="No evidence attached to this expense")
    return storage_service.get_file_path(expense.evidence_filename), expense.evidence_original_filename or expense.evidence_filename