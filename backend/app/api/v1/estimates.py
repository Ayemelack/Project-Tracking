import os
from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.logging import logger
from app.models.models import User
from app.schemas.schemas import (
    EstimateResponse, EstimateDetailResponse, EstimateListResponse,
    EstimateCreate, EstimateUpdate, UploadResponse, ExtractionResult,
    EstimateLineItemUpdate,
)
from app.services.storage_service import storage_service
from app.services.pdf_extraction_service import pdf_extraction_service
from app.repositories.estimate_repository import estimate_repo, line_item_repo
from app.api.v1.dependencies import get_current_user, require_writer, require_admin

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_estimate(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_writer),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ('.pdf',):
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Only PDF files are accepted.")

    content = await file.read()
    if len(content) > settings.UPLOAD_MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.UPLOAD_MAX_SIZE // (1024*1024)}MB."
        )

    await file.seek(0)
    original_filename, stored_filename = await storage_service.save_upload(file)

    file_path = storage_service.get_file_path(stored_filename)

    try:
        extraction_result: ExtractionResult = pdf_extraction_service.extract_from_pdf(str(file_path))
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise HTTPException(status_code=422, detail=f"Failed to process PDF: {str(e)}")

    estimate_create = EstimateCreate(
        title=extraction_result.estimate.title,
        project_name=extraction_result.estimate.project_name,
        reference_number=extraction_result.estimate.reference_number,
        contractor=extraction_result.estimate.contractor,
        client=extraction_result.estimate.client,
        currency=extraction_result.estimate.currency,
        line_items=extraction_result.line_items,
    )

    db_estimate = estimate_repo.create(db, estimate_create, stored_filename, original_filename)

    return UploadResponse(
        id=db_estimate.id,
        filename=original_filename,
        status="extracted",
        message=f"Estimate uploaded and processed. {len(extraction_result.line_items)} line items extracted.",
    )


@router.get("", response_model=EstimateListResponse)
def list_estimates(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    estimates = estimate_repo.get_all(db, skip=skip, limit=limit)
    total = estimate_repo.get_count(db)
    return EstimateListResponse(estimates=estimates, total=total)


@router.get("/{estimate_id}", response_model=EstimateDetailResponse)
def get_estimate(
    estimate_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    estimate = estimate_repo.get_by_id(db, estimate_id)
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    return estimate


@router.put("/{estimate_id}", response_model=EstimateResponse)
def update_estimate(
    estimate_id: UUID,
    data: EstimateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_writer),
):
    estimate = estimate_repo.update(db, estimate_id, data)
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    return estimate


@router.post("/{estimate_id}/confirm", response_model=EstimateResponse)
def confirm_estimate(
    estimate_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    estimate = estimate_repo.update_status(db, estimate_id, "confirmed")
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    return estimate


@router.delete("/{estimate_id}")
def delete_estimate(
    estimate_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    success = estimate_repo.delete(db, estimate_id)
    if not success:
        raise HTTPException(status_code=404, detail="Estimate not found")
    return {"message": "Estimate deleted"}


@router.put("/{estimate_id}/items/{item_id}", response_model=dict)
def update_line_item(
    estimate_id: UUID,
    item_id: UUID,
    data: EstimateLineItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_writer),
):
    item = line_item_repo.get_by_id(db, item_id)
    if not item or item.estimate_id != estimate_id:
        raise HTTPException(status_code=404, detail="Line item not found")

    updated = line_item_repo.update(db, item_id, data)
    estimate_repo.recalculate_total(db, estimate_id)
    return {"message": "Line item updated", "item_id": str(updated.id)}


@router.post("/{estimate_id}/items")
def add_line_item(
    estimate_id: UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_writer),
):
    from app.schemas.schemas import EstimateLineItemCreate
    estimate = estimate_repo.get_by_id(db, estimate_id)
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")

    item_data = EstimateLineItemCreate(**data)
    item = line_item_repo.create(db, estimate_id, item_data)
    estimate_repo.recalculate_total(db, estimate_id)
    return {"message": "Line item added", "item_id": str(item.id)}


@router.delete("/{estimate_id}/items/{item_id}")
def delete_line_item(
    estimate_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    item = line_item_repo.get_by_id(db, item_id)
    if not item or item.estimate_id != estimate_id:
        raise HTTPException(status_code=404, detail="Line item not found")

    line_item_repo.delete(db, item_id)
    estimate_repo.recalculate_total(db, estimate_id)
    return {"message": "Line item deleted"}
