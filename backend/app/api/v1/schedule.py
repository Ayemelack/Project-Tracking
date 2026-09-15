from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import User
from app.schemas.schemas import (
    ActivityCreate,
    ActivityUpdate,
    ActivityResponse,
    ActivityListResponse,
    ActivitySummaryResponse,
    MilestoneCreate,
    MilestoneUpdate,
    MilestoneResponse,
    MilestoneListResponse,
)
from app.repositories.activity_repository import activity_repo
from app.services import activity_service
from app.api.v1.dependencies import get_current_user, require_writer

router = APIRouter()


@router.get("", response_model=ActivityListResponse)
def list_activities(
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
    project_stage: str | None = None,
    project: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    activities = activity_repo.get_all(
        db, skip=skip, limit=limit, status=status, project_stage=project_stage, project=project
    )
    total = activity_repo.get_count(
        db, status=status, project_stage=project_stage, project=project
    )
    return ActivityListResponse(
        activities=[activity_service.build_activity_response(db, a) for a in activities],
        total=total,
        summary=activity_service.get_activity_summary(db),
    )


@router.post("", response_model=ActivityResponse, status_code=201)
def create_activity(
    data: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_writer),
):
    return activity_service.build_activity_response(
        db, activity_service.create_activity(db, data)
    )


@router.get("/summary", response_model=ActivitySummaryResponse)
def activity_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return activity_service.get_activity_summary(db)


# ---------------------------------------------------------------------------
# Milestones (declared before /{activity_id} so the paths never collide)
# ---------------------------------------------------------------------------

@router.get("/milestones", response_model=MilestoneListResponse)
def list_milestones(
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
    project: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    milestones = activity_repo.list_milestones(
        db, skip=skip, limit=limit, status=status, project=project
    )
    total = activity_repo.milestone_count(db, status=status, project=project)
    return MilestoneListResponse(
        milestones=[activity_service.build_milestone_response(db, m) for m in milestones],
        total=total,
    )


@router.post("/milestones", response_model=MilestoneResponse, status_code=201)
def create_milestone(
    data: MilestoneCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_writer),
):
    return activity_service.build_milestone_response(
        db, activity_service.create_milestone(db, data)
    )


@router.get("/milestones/{milestone_id}", response_model=MilestoneResponse)
def get_milestone(
    milestone_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return activity_service.build_milestone_response(
        db, activity_service.get_milestone_or_404(db, milestone_id)
    )


@router.patch("/milestones/{milestone_id}", response_model=MilestoneResponse)
def update_milestone(
    milestone_id: UUID,
    data: MilestoneUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_writer),
):
    return activity_service.build_milestone_response(
        db, activity_service.update_milestone(db, milestone_id, data)
    )


# ---------------------------------------------------------------------------
# Activities by id
# ---------------------------------------------------------------------------

@router.get("/{activity_id}", response_model=ActivityResponse)
def get_activity(
    activity_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return activity_service.build_activity_response(
        db, activity_service.get_activity_or_404(db, activity_id)
    )


@router.patch("/{activity_id}", response_model=ActivityResponse)
def update_activity(
    activity_id: UUID,
    data: ActivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_writer),
):
    return activity_service.build_activity_response(
        db, activity_service.update_activity(db, activity_id, data)
    )