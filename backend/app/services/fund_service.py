from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.models.models import FundReceipt, FundAllocation, Estimate
from app.schemas.schemas import (
    FundReceiptCreate,
    FundReceiptResponse,
    FundReceiptSummaryItem,
    FundAllocationCreate,
    FundAllocationResponse,
    FundingSummary,
)
from app.repositories.fund_repository import (
    fund_receipt_repo,
    fund_allocation_repo,
    fund_audit_repo,
)
from app.services.storage_service import storage_service


ZERO = Decimal("0.00")

ALLOWED_EVIDENCE_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif"}
ALLOWED_EVIDENCE_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
}


def money(value: Decimal | int | float | None) -> Decimal:
    if value is None:
        return ZERO
    return Decimal(str(value)).quantize(Decimal("0.01"))


def receipt_available_amount(db: Session, receipt: FundReceipt) -> Decimal:
    allocated = fund_allocation_repo.get_active_allocated_total(db, receipt.id)
    return money(receipt.amount) - money(allocated)


def _estimate_title(db: Session, estimate_id: UUID | None) -> str | None:
    if not estimate_id:
        return None
    estimate = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    return estimate.title if estimate else None


def build_allocation_response(db: Session, allocation: FundAllocation) -> FundAllocationResponse:
    response = FundAllocationResponse.model_validate(allocation)
    response.currency = allocation.fund_receipt.currency if allocation.fund_receipt else "FCFA"
    response.estimate_title = _estimate_title(db, allocation.estimate_id)
    return response


def build_receipt_summary(receipt: FundReceipt, allocated: Decimal | None = None) -> FundReceiptSummaryItem:
    allocated_amount = money(allocated if allocated is not None else None)
    item = FundReceiptSummaryItem.model_validate(receipt)
    item.allocated_amount = allocated_amount
    item.unallocated_amount = money(receipt.amount) - allocated_amount
    return item


def get_funding_summary(db: Session) -> FundingSummary:
    approved = db.query(func.sum(Estimate.total_estimated_amount)).filter(
        Estimate.status == "confirmed"
    ).scalar() or ZERO

    total_received = (
        db.query(func.sum(FundReceipt.amount)).scalar() or ZERO
    )

    total_allocated = (
        db.query(func.sum(FundAllocation.amount))
        .filter(FundAllocation.status == "allocated")
        .scalar()
        or ZERO
    )

    approved = money(approved)
    total_received = money(total_received)
    total_allocated = money(total_allocated)
    total_unallocated = total_received - total_allocated

    coverage = None
    if approved > ZERO:
        coverage = round(float((total_received / approved) * 100), 2)

    return FundingSummary(
        approved_estimated_amount=approved,
        total_received=total_received,
        total_allocated=total_allocated,
        total_unallocated=total_unallocated,
        funding_coverage_percentage=coverage,
    )


def create_fund_receipt(db: Session, data: FundReceiptCreate) -> FundReceipt:
    if data.estimate_id:
        _require_estimate(db, data.estimate_id)
    receipt = fund_receipt_repo.create(db, data)
    fund_audit_repo.log(
        db,
        entity_type="fund_receipt",
        entity_id=receipt.id,
        action="created",
        new_value=(
            f"amount={receipt.amount}, currency={receipt.currency}, "
            f"source={receipt.source}, received_date={receipt.received_date}"
        ),
    )
    logger.info(f"Fund receipt created: {receipt.id} amount={receipt.amount}")
    return receipt


def _require_estimate(db: Session, estimate_id: UUID) -> Estimate:
    estimate = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    return estimate


def create_allocation(
    db: Session,
    receipt_id: UUID,
    data: FundAllocationCreate,
) -> FundAllocation:
    receipt = fund_receipt_repo.get_by_id(db, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Fund receipt not found")

    if data.estimate_id:
        _require_estimate(db, data.estimate_id)

    available = receipt_available_amount(db, receipt)
    if data.amount > available:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Allocation of {data.amount} exceeds available funds. "
                f"Available: {available}"
            ),
        )

    allocation = fund_allocation_repo.create(db, receipt_id, data)
    fund_audit_repo.log(
        db,
        entity_type="fund_allocation",
        entity_id=allocation.id,
        action="created",
        new_value=(
            f"amount={allocation.amount}, fund_receipt={receipt_id}, "
            f"estimate_id={allocation.estimate_id}, category={allocation.category or ''}"
        ),
    )
    logger.info(f"Allocation created: {allocation.id} amount={allocation.amount}")
    return allocation


def cancel_allocation(
    db: Session,
    allocation_id: UUID,
    reason: str | None = None,
) -> FundAllocation:
    allocation = fund_allocation_repo.get_by_id(db, allocation_id)
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")

    if allocation.status == "cancelled":
        raise HTTPException(status_code=409, detail="Allocation is already cancelled")

    fund_audit_repo.log(
        db,
        entity_type="fund_allocation",
        entity_id=allocation.id,
        action="cancelled",
        field_name="status",
        old_value=str(allocation.amount),
        new_value="0.00",
        reason=reason,
    )
    cancelled = fund_allocation_repo.cancel(db, allocation)
    logger.info(f"Allocation cancelled: {allocation.id}")
    return cancelled


# ---------------------------------------------------------------------------
# Supporting evidence (reuses Phase 1 storage architecture)
# ---------------------------------------------------------------------------

def _validate_evidence_file(file: UploadFile) -> bytes:
    original = file.filename or ""
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_EVIDENCE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported evidence file type: {ext}. Allowed: "
                + ", ".join(sorted(ALLOWED_EVIDENCE_EXTENSIONS))
            ),
        )

    content = file.file.read()
    if len(content) > settings.UPLOAD_MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Evidence file too large. Maximum size is "
                f"{settings.UPLOAD_MAX_SIZE // (1024 * 1024)}MB."
            ),
        )
    mime = file.content_type or ""
    if ext == ".pdf" and not mime.startswith("application/pdf"):
        raise HTTPException(status_code=400, detail="Evidence file is not a valid PDF")
    if ext in (".png", ".jpg", ".jpeg", ".webp", ".gif") and not mime.startswith("image/"):
        raise HTTPException(status_code=400, detail="Evidence file is not a valid image")
    return content


def _save_evidence(file: UploadFile) -> tuple[str, str, str, int]:
    content = _validate_evidence_file(file)
    original_filename, stored_filename = storage_service.save_bytes(file.filename or "evidence", content)
    return original_filename, stored_filename, file.content_type or "", len(content)


def attach_receipt_evidence(db: Session, receipt_id: UUID, file: UploadFile) -> FundReceipt:
    receipt = fund_receipt_repo.get_by_id(db, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Fund receipt not found")

    original, stored, mime, size = _save_evidence(file)
    receipt.evidence_filename = stored
    receipt.evidence_original_filename = original
    receipt.evidence_mime_type = mime
    receipt.evidence_size = size
    db.commit()
    db.refresh(receipt)
    fund_audit_repo.log(
        db,
        entity_type="fund_receipt",
        entity_id=receipt.id,
        action="evidence_attached",
        new_value=original,
    )
    return receipt


def clear_receipt_evidence(db: Session, receipt_id: UUID) -> FundReceipt:
    receipt = fund_receipt_repo.get_by_id(db, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Fund receipt not found")

    previous = receipt.evidence_original_filename
    receipt.evidence_filename = None
    receipt.evidence_original_filename = None
    receipt.evidence_mime_type = None
    receipt.evidence_size = None
    db.commit()
    db.refresh(receipt)
    fund_audit_repo.log(
        db,
        entity_type="fund_receipt",
        entity_id=receipt.id,
        action="evidence_removed",
        old_value=previous,
    )
    return receipt


def attach_allocation_evidence(db: Session, allocation_id: UUID, file: UploadFile) -> FundAllocation:
    allocation = fund_allocation_repo.get_by_id(db, allocation_id)
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")

    original, stored, mime, size = _save_evidence(file)
    allocation.evidence_filename = stored
    allocation.evidence_original_filename = original
    allocation.evidence_mime_type = mime
    allocation.evidence_size = size
    db.commit()
    db.refresh(allocation)
    fund_audit_repo.log(
        db,
        entity_type="fund_allocation",
        entity_id=allocation.id,
        action="evidence_attached",
        new_value=original,
    )
    return allocation


def clear_allocation_evidence(db: Session, allocation_id: UUID) -> FundAllocation:
    allocation = fund_allocation_repo.get_by_id(db, allocation_id)
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")

    previous = allocation.evidence_original_filename
    allocation.evidence_filename = None
    allocation.evidence_original_filename = None
    allocation.evidence_mime_type = None
    allocation.evidence_size = None
    db.commit()
    db.refresh(allocation)
    fund_audit_repo.log(
        db,
        entity_type="fund_allocation",
        entity_id=allocation.id,
        action="evidence_removed",
        old_value=previous,
    )
    return allocation


def evidence_file_path(db: Session, receipt_id: UUID, allocation_id: UUID | None = None) -> tuple[Path, str]:
    if allocation_id is not None:
        allocation = fund_allocation_repo.get_by_id(db, allocation_id)
        if not allocation or not allocation.evidence_filename:
            raise HTTPException(status_code=404, detail="No evidence attached to this allocation")
        return storage_service.get_file_path(allocation.evidence_filename), allocation.evidence_original_filename or allocation.evidence_filename

    receipt = fund_receipt_repo.get_by_id(db, receipt_id)
    if not receipt or not receipt.evidence_filename:
        raise HTTPException(status_code=404, detail="No evidence attached to this fund receipt")
    return storage_service.get_file_path(receipt.evidence_filename), receipt.evidence_original_filename or receipt.evidence_filename
