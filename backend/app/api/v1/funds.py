from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import User
from app.schemas.schemas import (
    FundReceiptCreate,
    FundReceiptResponse,
    FundReceiptListResponse,
    FundReceiptDetailResponse,
    FundAllocationCreate,
    FundAllocationResponse,
    AllocationListResponse,
    FundingSummary,
)
from app.repositories.fund_repository import (
    fund_receipt_repo,
    fund_allocation_repo,
)
from app.services import fund_service
from app.services.storage_service import path_suffix_mime
from app.api.v1.dependencies import get_current_user, require_writer, require_admin

router = APIRouter()


@router.get("", response_model=FundReceiptListResponse)
def list_funds(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    receipts = fund_receipt_repo.get_all(db, skip=skip, limit=limit)
    total = fund_receipt_repo.get_count(db)
    allocated_map = fund_receipt_repo.allocated_total_per_receipt(db)
    items = [
        fund_service.build_receipt_summary(receipt, allocated_map.get(receipt.id))
        for receipt in receipts
    ]
    return FundReceiptListResponse(
        receipts=items,
        total=total,
        summary=fund_service.get_funding_summary(db),
    )


@router.post("", response_model=FundReceiptResponse, status_code=201)
def create_fund_receipt(
    data: FundReceiptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_writer),
):
    return fund_service.create_fund_receipt(db, data)


@router.get("/summary", response_model=FundingSummary)
def funding_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return fund_service.get_funding_summary(db)


@router.get("/{fund_id}/allocations", response_model=AllocationListResponse)
def list_allocations(
    fund_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    receipt = _receipt_or_404(db, fund_id)
    allocations = fund_allocation_repo.get_by_receipt(db, fund_id)
    allocated = fund_allocation_repo.get_active_allocated_total(db, fund_id)
    return AllocationListResponse(
        allocations=[
            fund_service.build_allocation_response(db, a)
            for a in allocations
        ],
        total=len(allocations),
        allocated_amount=allocated,
        unallocated_amount=fund_service.money(receipt.amount) - fund_service.money(allocated),
    )


@router.post("/{fund_id}/allocations", response_model=FundAllocationResponse, status_code=201)
def create_allocation(
    fund_id: UUID,
    data: FundAllocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_writer),
):
    allocation = fund_service.create_allocation(db, fund_id, data)
    return fund_service.build_allocation_response(db, allocation)


@router.get("/{fund_id}", response_model=FundReceiptDetailResponse)
def get_fund_receipt(
    fund_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    receipt = _receipt_or_404(db, fund_id)
    allocations = fund_allocation_repo.get_by_receipt(db, receipt.id)
    allocated = fund_allocation_repo.get_active_allocated_total(db, receipt.id)

    detail = FundReceiptDetailResponse.model_validate(receipt)
    detail.allocated_amount = allocated
    detail.unallocated_amount = fund_service.money(receipt.amount) - fund_service.money(allocated)
    detail.allocations = [
        fund_service.build_allocation_response(db, a)
        for a in allocations
    ]
    return detail


@router.post("/{fund_id}/evidence", response_model=FundReceiptResponse)
def upload_receipt_evidence(
    fund_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_writer),
):
    return fund_service.attach_receipt_evidence(db, fund_id, file)


@router.get("/{fund_id}/evidence")
def download_receipt_evidence(fund_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    path, original = fund_service.evidence_file_path(db, fund_id)
    return FileResponse(
        path,
        filename=original,
        media_type=path_suffix_mime(path),
    )


@router.delete("/{fund_id}/evidence", response_model=FundReceiptResponse)
def delete_receipt_evidence(fund_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return fund_service.clear_receipt_evidence(db, fund_id)


def _receipt_or_404(db: Session, fund_id: UUID):
    receipt = fund_receipt_repo.get_by_id(db, fund_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Fund receipt not found")
    return receipt