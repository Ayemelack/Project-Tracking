from decimal import Decimal
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.models import Resource, ResourceMovement, Estimate, EstimateLineItem, Expense
from app.schemas.schemas import (
    ResourceCreate,
    ResourcePurchaseCreate,
    ResourceDeliveryCreate,
    ResourceUsageCreate,
    ResourceAdjustmentCreate,
    ResourceResponse,
    ResourceDetailResponse,
    ResourceMovementResponse,
    ResourceExpenseInfo,
)
from app.repositories.resource_repository import resource_repo
from app.repositories.expense_repository import expense_repo
from app.services import fund_service
from app.services.expense_service import _estimate_title
from app.services.storage_service import storage_service


ZERO = Decimal("0.00")


def money(value) -> Decimal:
    return fund_service.money(value)


def qty(value) -> Decimal:
    if value is None:
        return ZERO
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _require_resource(db: Session, resource_id: UUID) -> Resource:
    resource = resource_repo.get_by_id(db, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource


def _estimate_item_description(db: Session, item_id: UUID | None) -> str | None:
    if not item_id:
        return None
    item = db.query(EstimateLineItem).filter(EstimateLineItem.id == item_id).first()
    return item.description if item else None


# ---------------------------------------------------------------------------
# Resource master record
# ---------------------------------------------------------------------------

def create_resource(db: Session, data: ResourceCreate) -> Resource:
    estimate_id = data.estimate_id

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

    if estimate_id:
        estimate = db.query(Estimate).filter(Estimate.id == estimate_id).first()
        if not estimate:
            raise HTTPException(status_code=404, detail="Estimate not found")

    resource = Resource(
        project=data.project,
        name=data.name,
        category=data.category,
        unit=data.unit,
        currency=data.currency.upper(),
        estimate_id=estimate_id,
        estimate_line_item_id=data.estimate_line_item_id,
        budgeted_quantity=data.budgeted_quantity,
        budgeted_cost=data.budgeted_cost,
        notes=data.notes,
        status="active",
    )
    return resource_repo.create(db, resource)


# ---------------------------------------------------------------------------
# Movement rules
# ---------------------------------------------------------------------------

def _movement_date(data) -> date:
    if getattr(data, "movement_date", None) is not None:
        return data.movement_date
    return datetime.now(timezone.utc).date()


def _require_purchase_expense(db: Session, expense_id: UUID, resource: Resource, quantity: Decimal, unit_cost: Decimal):
    expense = expense_repo.get_by_id(db, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    if expense.status == "reversed":
        raise HTTPException(
            status_code=409,
            detail="A reversed expense cannot be linked to a resource purchase.",
        )
    if expense.currency.upper() != resource.currency.upper():
        raise HTTPException(
            status_code=422,
            detail=(
                f"Expense currency {expense.currency.upper()} does not match the "
                f"resource currency {resource.currency.upper()}."
            ),
        )
    # The financial record and the resource record must tell the same story.
    if expense.quantity is not None and qty(expense.quantity) != qty(quantity):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Expense quantity is {qty(expense.quantity)} but the resource "
                f"purchase records {qty(quantity)}. They must match."
            ),
        )
    if expense.unit_price is not None and money(expense.unit_price) != money(unit_cost):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Expense unit price is {money(expense.unit_price)} but the resource "
                f"purchase records {money(unit_cost)}. They must match."
            ),
        )


def create_purchase(db: Session, resource_id: UUID, data: ResourcePurchaseCreate) -> ResourceMovement:
    resource = _lock_resource(db, resource_id)

    total_cost = money(qty(data.quantity) * money(data.unit_cost))
    if data.expense_id:
        _require_purchase_expense(db, data.expense_id, resource, data.quantity, data.unit_cost)

    movement = ResourceMovement(
        resource_id=resource.id,
        movement_type="purchase",
        quantity=qty(data.quantity),
        movement_date=_movement_date(data),
        unit_cost=money(data.unit_cost),
        total_cost=total_cost,
        expense_id=data.expense_id,
        supplier=data.supplier,
        reference=data.reference,
        responsible_person=data.responsible_person,
        notes=data.notes,
    )
    return resource_repo.create_movement(db, movement)


def _lock_resource(db: Session, resource_id: UUID) -> Resource:
    resource = resource_repo.get_by_id_for_update(db, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource


def _current_totals(db: Session, resource_id: UUID) -> dict[str, Decimal]:
    totals = resource_repo.quantity_totals(db, resource_id)
    return {
        "purchased": qty(totals.get("purchase")),
        "delivered": qty(totals.get("delivery")),
        "used": qty(totals.get("usage")),
        "adjustments": qty(totals.get("adjustment")),
    }


def create_delivery(db: Session, resource_id: UUID, data: ResourceDeliveryCreate) -> ResourceMovement:
    resource = _lock_resource(db, resource_id)
    totals = _current_totals(db, resource_id)

    if data.linked_purchase_movement_id:
        purchase = resource_repo.movement_by_id(db, data.linked_purchase_movement_id)
        if not purchase or purchase.movement_type != "purchase" or purchase.resource_id != resource.id:
            raise HTTPException(
                status_code=422,
                detail="The linked purchase does not exist or is not a purchase of this resource.",
            )

    purchased = totals["purchased"]
    delivered = totals["delivered"]
    after_delivery = delivered + qty(data.quantity)
    if after_delivery > purchased:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Delivery of {qty(data.quantity)} would make the delivered quantity "
                f"{after_delivery}, which exceeds the purchased quantity of {purchased}. "
                f"Deliveries cannot exceed purchases. Record an explicit adjustment only "
                f"if extra materials (e.g. donated stock) genuinely arrived on site."
            ),
        )

    movement = ResourceMovement(
        resource_id=resource.id,
        movement_type="delivery",
        quantity=qty(data.quantity),
        movement_date=_movement_date(data),
        related_purchase_movement_id=data.linked_purchase_movement_id,
        supplier=data.supplier,
        reference=data.reference,
        receiver=data.receiver,
        responsible_person=data.responsible_person,
        notes=data.notes,
    )
    return resource_repo.create_movement(db, movement)


def create_usage(db: Session, resource_id: UUID, data: ResourceUsageCreate) -> ResourceMovement:
    resource = _lock_resource(db, resource_id)
    totals = _current_totals(db, resource_id)

    # Available = Delivered + Adjustments - Recorded Usage
    available = totals["delivered"] + totals["adjustments"] - totals["used"]
    after_usage = available - qty(data.quantity)
    if after_usage < ZERO:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Usage of {qty(data.quantity)} exceeds the available quantity of {available}. "
                f"Usage cannot make the remaining quantity negative. Record an explicit "
                f"adjustment only if legitimate additional stock was found on site."
            ),
        )

    movement = ResourceMovement(
        resource_id=resource.id,
        movement_type="usage",
        quantity=qty(data.quantity),
        movement_date=_movement_date(data),
        project_stage=data.project_stage,
        activity=data.activity,
        responsible_person=data.responsible_person,
        notes=data.notes,
    )
    return resource_repo.create_movement(db, movement)


def create_adjustment(db: Session, resource_id: UUID, data: ResourceAdjustmentCreate) -> ResourceMovement:
    resource = _lock_resource(db, resource_id)
    totals = _current_totals(db, resource_id)

    adjustment_qty = qty(data.quantity)

    # Positive adjustments (found/donated stock) must have a reason that explains them.
    # Negative adjustments reduce stock and are the explicit authorized process.
    if adjustment_qty < ZERO:
        if not data.authorized_by or not data.authorization_reason:
            raise HTTPException(
                status_code=422,
                detail=(
                    "A negative adjustment reduces stock and requires explicit authorization: "
                    "provide both authorized_by and authorization_reason."
                ),
            )
    if not data.notes:
        raise HTTPException(
            status_code=422,
            detail="Every adjustment must state a reason in the notes field.",
        )

    available = totals["delivered"] + totals["adjustments"] - totals["used"]
    after = available + adjustment_qty
    if after < ZERO:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Adjustment of {adjustment_qty} would make the available quantity "
                f"negative ({after}). The available balance is {available}."
            ),
        )

    movement = ResourceMovement(
        resource_id=resource.id,
        movement_type="adjustment",
        quantity=adjustment_qty,
        movement_date=_movement_date(data),
        responsible_person=data.responsible_person,
        notes=data.notes,
        authorized_by=data.authorized_by,
        authorization_reason=data.authorization_reason,
    )
    return resource_repo.create_movement(db, movement)


# ---------------------------------------------------------------------------
# Computed positions from the ledger
# ---------------------------------------------------------------------------

def computed_position(db: Session, resource: Resource) -> dict:
    totals = _current_totals(db, resource.id)
    purchased = totals["purchased"]
    delivered = totals["delivered"]
    used = totals["used"]
    adjustments = totals["adjustments"]

    # Available = Delivered + Adjustments - Recorded Usage
    remaining = delivered + adjustments - used
    pending_delivery = purchased - delivered
    total_purchase_cost = money(resource_repo.purchase_cost_total(db, resource.id))

    cost_variance = None
    if resource.budgeted_cost is not None:
        cost_variance = money(resource.budgeted_cost) - total_purchase_cost

    return {
        "purchased_quantity": money(purchased),
        "delivered_quantity": money(delivered),
        "used_quantity": money(used),
        "adjustment_quantity": money(adjustments),
        "remaining_quantity": money(remaining),
        "pending_delivery_quantity": money(pending_delivery),
        "total_purchase_cost": total_purchase_cost,
        "cost_variance": cost_variance,
    }


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

def build_resource_response(db: Session, resource: Resource) -> ResourceResponse:
    response = ResourceResponse.model_validate(resource)
    response.estimate_title = _estimate_title(db, resource.estimate_id)
    response.estimate_item_description = _estimate_item_description(db, resource.estimate_line_item_id)
    response.__dict__.update(computed_position(db, resource))
    return response


def build_movement_response(db: Session, movement: ResourceMovement) -> ResourceMovementResponse:
    response = ResourceMovementResponse.model_validate(movement)
    if movement.expense_id:
        expense = db.query(Expense).filter(Expense.id == movement.expense_id).first()
        response.expense_description = expense.description if expense else None
    return response


def build_resource_detail(db: Session, resource: Resource) -> ResourceDetailResponse:
    response = ResourceDetailResponse.model_validate(resource)
    response.estimate_title = _estimate_title(db, resource.estimate_id)
    response.estimate_item_description = _estimate_item_description(db, resource.estimate_line_item_id)
    response.__dict__.update(computed_position(db, resource))
    response.movements = [build_movement_response(db, m) for m in resource_repo.movements(db, resource.id)]

    related_expenses: list[ResourceExpenseInfo] = []
    seen: set[UUID] = set()
    expense_ids = [
        m.expense_id for m in resource_repo.movements(db, resource.id) if m.expense_id
    ]
    for expense_id in expense_ids:
        if expense_id in seen:
            continue
        seen.add(expense_id)
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if expense:
            related_expenses.append(
                ResourceExpenseInfo(
                    id=expense.id,
                    expense_date=expense.expense_date,
                    amount=money(expense.amount),
                    description=expense.description,
                    reference=expense.reference,
                    currency=expense.currency or "FCFA",
                )
            )
    response.related_expenses = related_expenses
    return response


# ---------------------------------------------------------------------------
# Supporting evidence (reuses the shared storage architecture)
# ---------------------------------------------------------------------------

def attach_movement_evidence(db: Session, resource_id: UUID, movement_id: UUID, file: UploadFile) -> ResourceMovement:
    movement = resource_repo.movement_by_id(db, movement_id)
    if not movement or movement.resource_id != UUID(str(resource_id)):
        raise HTTPException(status_code=404, detail="Movement not found")

    content = fund_service._validate_evidence_file(file)
    original, stored = storage_service.save_bytes(file.filename or "evidence", content)
    mime = file.content_type or ""
    size = len(content)

    movement.evidence_filename = stored
    movement.evidence_original_filename = original
    movement.evidence_mime_type = mime
    movement.evidence_size = size
    db.commit()
    db.refresh(movement)
    return movement


def clear_movement_evidence(db: Session, resource_id: UUID, movement_id: UUID) -> ResourceMovement:
    movement = resource_repo.movement_by_id(db, movement_id)
    if not movement or movement.resource_id != UUID(str(resource_id)):
        raise HTTPException(status_code=404, detail="Movement not found")

    movement.evidence_filename = None
    movement.evidence_original_filename = None
    movement.evidence_mime_type = None
    movement.evidence_size = None
    db.commit()
    db.refresh(movement)
    return movement


def movement_evidence_file_path(db: Session, resource_id: UUID, movement_id: UUID) -> tuple[Path, str]:
    movement = resource_repo.movement_by_id(db, movement_id)
    if not movement or movement.resource_id != UUID(str(resource_id)) or not movement.evidence_filename:
        raise HTTPException(status_code=404, detail="No evidence attached to this movement")
    return (
        storage_service.get_file_path(movement.evidence_filename),
        movement.evidence_original_filename or movement.evidence_filename,
    )