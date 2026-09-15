from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.ratelimit import rate_limiter
from app.models.models import User
from app.schemas.schemas import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseDetailResponse,
    ExpenseListResponse,
    ExpenseSummary,
    UpdateAllocationStatus,
)
from app.repositories.expense_repository import expense_repo
from app.services import expense_service
from app.services.storage_service import path_suffix_mime
from app.api.v1.dependencies import get_current_user, require_writer, require_admin

router = APIRouter()

EVIDENCE_UPLOAD_USER_LIMIT = 10
EVIDENCE_UPLOAD_WINDOW_SECONDS = 60
EVIDENCE_UPLOAD_RATE_LIMITED_MESSAGE = "Too many uploads. Please try again shortly."


def _expense_or_404(db: Session, expense_id: UUID):
    expense = expense_repo.get_by_id(db, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@router.get("", response_model=ExpenseListResponse)
def list_expenses(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    expenses = expense_repo.get_all(db, skip=skip, limit=limit)
    total = expense_repo.get_count(db)
    return ExpenseListResponse(
        expenses=[
            expense_service.build_expense_response(expense)
            for expense in expenses
        ],
        total=total,
        summary=expense_service.get_expense_summary(db),
    )


@router.post("", response_model=ExpenseResponse, status_code=201)
def create_expense(data: ExpenseCreate, db: Session = Depends(get_db), current_user: User = Depends(require_writer)):
    return expense_service.build_expense_response(expense_service.create_expense(db, data))


@router.get("/summary", response_model=ExpenseSummary)
def expense_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return expense_service.get_expense_summary(db)


@router.get("/{expense_id}", response_model=ExpenseDetailResponse)
def get_expense(
    expense_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return expense_service.build_expense_detail(db, _expense_or_404(db, expense_id))


@router.patch("/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: UUID,
    data: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_writer),
):
    return expense_service.build_expense_response(expense_service.update_expense(db, expense_id, data))


@router.post("/{expense_id}/reverse", response_model=ExpenseResponse)
def reverse_expense(
    expense_id: UUID,
    data: UpdateAllocationStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    reason = data.reason if data else None
    return expense_service.build_expense_response(
        expense_service.reverse_expense(db, expense_id, reason=reason)
    )


@router.post("/{expense_id}/evidence", response_model=ExpenseResponse)
def upload_expense_evidence(
    expense_id: UUID,
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
    return expense_service.build_expense_response(
        expense_service.attach_expense_evidence(db, expense_id, file)
    )


@router.get("/{expense_id}/evidence")
def download_expense_evidence(expense_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    path, original = expense_service.expense_evidence_file_path(db, expense_id)
    return FileResponse(
        path,
        filename=original,
        media_type=path_suffix_mime(path),
    )


@router.delete("/{expense_id}/evidence", response_model=ExpenseResponse)
def delete_expense_evidence(expense_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return expense_service.build_expense_response(
        expense_service.clear_expense_evidence(db, expense_id)
    )