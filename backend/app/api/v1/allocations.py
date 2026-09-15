from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.ratelimit import rate_limiter
from app.models.models import User
from app.schemas.schemas import UpdateAllocationStatus, FundAllocationResponse, AllocationExpenseListResponse
from app.repositories.fund_repository import fund_allocation_repo
from app.services import fund_service, expense_service
from app.services.storage_service import path_suffix_mime
from app.api.v1.dependencies import get_current_user, require_writer, require_admin

router = APIRouter()

EVIDENCE_UPLOAD_USER_LIMIT = 10
EVIDENCE_UPLOAD_WINDOW_SECONDS = 60
EVIDENCE_UPLOAD_RATE_LIMITED_MESSAGE = "Too many uploads. Please try again shortly."


def _allocation_or_404(db: Session, allocation_id: UUID):
    allocation = fund_allocation_repo.get_by_id(db, allocation_id)
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    return allocation


@router.get("", response_model=AllocationExpenseListResponse)
def list_allocations(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allocations = fund_allocation_repo.get_all(db, skip=skip, limit=limit)
    spent_per_allocation = expense_service.spent_per_allocation(db)
    items = []
    for allocation in allocations:
        spent = expense_service.money(spent_per_allocation.get(allocation.id))
        items.append(
            {
                "allocation_id": allocation.id,
                "allocation_purpose": allocation.purpose,
                "allocation_category": allocation.category,
                "estimate_title": expense_service._estimate_title(db, allocation.estimate_id),
                "allocated_amount": expense_service.money(allocation.amount),
                "spent_amount": spent,
                "remaining_amount": expense_service.money(allocation.amount) - spent,
                "currency": (
                    allocation.fund_receipt.currency if allocation.fund_receipt else "FCFA"
                ),
            }
        )
    return AllocationExpenseListResponse(allocations=items, total=len(items))


@router.get("/{allocation_id}", response_model=FundAllocationResponse)
def get_allocation(
    allocation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return fund_service.build_allocation_response(db, _allocation_or_404(db, allocation_id))


@router.post("/{allocation_id}/cancel", response_model=FundAllocationResponse)
def cancel_allocation(
    allocation_id: UUID,
    data: UpdateAllocationStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    reason = data.reason if data else None
    allocation = fund_service.cancel_allocation(db, allocation_id, reason=reason)
    return fund_service.build_allocation_response(db, allocation)


@router.post("/{allocation_id}/evidence", response_model=FundAllocationResponse)
def upload_allocation_evidence(
    allocation_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_writer),
):
    if not rate_limiter.allow(
        f"evidence-upload:{current_user.username}",
        EVIDENCE_UPLOAD_USER_LIMIT,
        EVIDENCE_UPLOAD_WINDOW_SECONDS,
    ):
        raise HTTPException(status_code=429, detail=EVIDENCE_UPLOAD_RATE_LIMITED_MESSAGE)
    return fund_service.attach_allocation_evidence(db, allocation_id, file)


@router.get("/{allocation_id}/evidence")
def download_allocation_evidence(
    allocation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    path, original = fund_service.evidence_file_path(db, None, allocation_id=allocation_id)
    return FileResponse(
        path,
        filename=original,
        media_type=path_suffix_mime(path),
    )


@router.delete("/{allocation_id}/evidence", response_model=FundAllocationResponse)
def delete_allocation_evidence(
    allocation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return fund_service.clear_allocation_evidence(db, allocation_id)
