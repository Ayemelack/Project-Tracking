from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.ratelimit import rate_limiter
from app.models.models import User
from app.schemas.schemas import (
    ResourceCreate,
    ResourceResponse,
    ResourceDetailResponse,
    ResourceListResponse,
    ResourcePurchaseCreate,
    ResourceDeliveryCreate,
    ResourceUsageCreate,
    ResourceAdjustmentCreate,
    ResourceMovementResponse,
)
from app.repositories.resource_repository import resource_repo
from app.services import resource_service
from app.services.storage_service import path_suffix_mime
from app.api.v1.dependencies import get_current_user, require_writer, require_admin

router = APIRouter()

EVIDENCE_UPLOAD_USER_LIMIT = 10
EVIDENCE_UPLOAD_WINDOW_SECONDS = 60
EVIDENCE_UPLOAD_RATE_LIMITED_MESSAGE = "Too many uploads. Please try again shortly."


@router.get("", response_model=ResourceListResponse)
def list_resources(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resources = resource_repo.get_all(db, skip=skip, limit=limit)
    total = resource_repo.get_count(db)
    return ResourceListResponse(
        resources=[resource_service.build_resource_response(db, r) for r in resources],
        total=total,
    )


@router.post("", response_model=ResourceResponse, status_code=201)
def create_resource(data: ResourceCreate, db: Session = Depends(get_db), current_user: User = Depends(require_writer)):
    resource = resource_service.create_resource(db, data)
    return resource_service.build_resource_response(db, resource)


@router.get("/{resource_id}", response_model=ResourceDetailResponse)
def get_resource(
    resource_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resource = resource_repo.get_by_id(db, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource_service.build_resource_detail(db, resource)


@router.post("/{resource_id}/purchases", response_model=ResourceMovementResponse, status_code=201)
def record_purchase(
    resource_id: UUID,
    data: ResourcePurchaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_writer),
):
    return resource_service.build_movement_response(
        db, resource_service.create_purchase(db, resource_id, data)
    )


@router.post("/{resource_id}/deliveries", response_model=ResourceMovementResponse, status_code=201)
def record_delivery(
    resource_id: UUID,
    data: ResourceDeliveryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_writer),
):
    return resource_service.build_movement_response(
        db, resource_service.create_delivery(db, resource_id, data)
    )


@router.post("/{resource_id}/usage", response_model=ResourceMovementResponse, status_code=201)
def record_usage(
    resource_id: UUID,
    data: ResourceUsageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_writer),
):
    return resource_service.build_movement_response(
        db, resource_service.create_usage(db, resource_id, data)
    )


@router.post("/{resource_id}/adjustments", response_model=ResourceMovementResponse, status_code=201)
def record_adjustment(
    resource_id: UUID,
    data: ResourceAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_writer),
):
    return resource_service.build_movement_response(
        db, resource_service.create_adjustment(db, resource_id, data)
    )


@router.post("/{resource_id}/movements/{movement_id}/evidence", response_model=ResourceMovementResponse)
def upload_movement_evidence(
    resource_id: UUID,
    movement_id: UUID,
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
    return resource_service.build_movement_response(
        db, resource_service.attach_movement_evidence(db, resource_id, movement_id, file)
    )


@router.get("/{resource_id}/movements/{movement_id}/evidence")
def download_movement_evidence(
    resource_id: UUID,
    movement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    path, original = resource_service.movement_evidence_file_path(db, resource_id, movement_id)
    return FileResponse(path, filename=original, media_type=path_suffix_mime(path))


@router.delete("/{resource_id}/movements/{movement_id}/evidence", response_model=ResourceMovementResponse)
def delete_movement_evidence(
    resource_id: UUID,
    movement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return resource_service.build_movement_response(
        db, resource_service.clear_movement_evidence(db, resource_id, movement_id)
    )