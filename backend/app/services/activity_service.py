from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import Activity, Milestone, Estimate
from app.repositories.activity_repository import activity_repo
from app.schemas.schemas import (
    ActivityCreate,
    ActivityUpdate,
    ActivityResponse,
    ActivitySummaryResponse,
    MilestoneCreate,
    MilestoneUpdate,
    MilestoneResponse,
    _validate_date_range,
)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _validate_estimate(db: Session, estimate_id: UUID | None) -> None:
    if estimate_id is None:
        return
    estimate = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")


def _estimate_title(db: Session, estimate_id: UUID | None) -> str | None:
    if estimate_id is None:
        return None
    estimate = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    return estimate.title if estimate else None


def get_activity_or_404(db: Session, activity_id: UUID) -> Activity:
    activity = activity_repo.get_by_id(db, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


def get_milestone_or_404(db: Session, milestone_id: UUID) -> Milestone:
    milestone = activity_repo.get_milestone(db, milestone_id)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return milestone


# ---------------------------------------------------------------------------
# Delay calculation
#
# Delay is always derived from schedule data; it is never guessed:
#   - cancelled activities have no delay.
#   - completed activities are compared against the planned end date using
#     their actual end date.
#   - any other activity is delayed when today has passed the planned end
#     date and work is not complete.
#   - an explicitly "delayed" status is reported as delayed even when no
#     past planned date allows a day count.
# ---------------------------------------------------------------------------

def compute_delay(activity: Activity) -> tuple[bool, int]:
    if activity.status == "cancelled":
        return False, 0

    if activity.status == "completed" and activity.actual_end_date:
        if activity.planned_end_date and activity.actual_end_date > activity.planned_end_date:
            return True, (activity.actual_end_date - activity.planned_end_date).days
        return False, 0

    days = 0
    if activity.planned_end_date:
        today = _today()
        if today > activity.planned_end_date:
            days = (today - activity.planned_end_date).days
    is_delayed = activity.status == "delayed" or days > 0
    return is_delayed, days


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

def build_activity_response(db: Session, activity: Activity) -> ActivityResponse:
    response = ActivityResponse.model_validate(activity)
    response.estimate_title = _estimate_title(db, activity.estimate_id)
    is_delayed, delay_days = compute_delay(activity)
    response.is_delayed = is_delayed
    response.delay_days = delay_days
    return response


def build_milestone_response(db: Session, milestone: Milestone) -> MilestoneResponse:
    response = MilestoneResponse.model_validate(milestone)
    response.estimate_title = _estimate_title(db, milestone.estimate_id)
    return response


# ---------------------------------------------------------------------------
# Activity operations
# ---------------------------------------------------------------------------

def create_activity(db: Session, data: ActivityCreate) -> Activity:
    _validate_estimate(db, data.estimate_id)
    activity = Activity(
        project=data.project,
        name=data.name,
        description=data.description,
        project_stage=data.project_stage,
        estimate_id=data.estimate_id,
        planned_start_date=data.planned_start_date,
        planned_end_date=data.planned_end_date,
        actual_start_date=data.actual_start_date,
        actual_end_date=data.actual_end_date,
        status=data.status,
        progress_percentage=data.progress_percentage,
        responsible_person=data.responsible_person,
        notes=data.notes,
        delay_reason=data.delay_reason,
        delay_reason_detail=data.delay_reason_detail,
        resource_dependency=data.resource_dependency,
    )
    return activity_repo.create(db, activity)


def update_activity(db: Session, activity_id: UUID, data: ActivityUpdate) -> Activity:
    activity = get_activity_or_404(db, activity_id)
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        return activity_repo.save(db, activity)

    if updates.get("estimate_id") is not None:
        _validate_estimate(db, updates["estimate_id"])

    for field, value in updates.items():
        # A few fields are non-nullable; an explicit null means "no change".
        if field in ("name", "status", "progress_percentage") and value is None:
            continue
        setattr(activity, field, value)

    # Re-validate merged dates (a partial update may pair with an existing date).
    try:
        _validate_date_range(activity.planned_start_date, activity.planned_end_date)
        _validate_date_range(activity.actual_start_date, activity.actual_end_date)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return activity_repo.save(db, activity)


def get_activity_summary(db: Session) -> ActivitySummaryResponse:
    counts = activity_repo.status_counts(db)
    return ActivitySummaryResponse(
        total_activities=sum(counts.values()),
        total_completed=counts.get("completed", 0),
        total_in_progress=counts.get("in_progress", 0),
        total_delayed=counts.get("delayed", 0),
        total_blocked=counts.get("blocked", 0),
        total_not_started=counts.get("not_started", 0),
        total_cancelled=counts.get("cancelled", 0),
        overall_progress=activity_repo.average_progress(db),
    )


# ---------------------------------------------------------------------------
# Milestone operations
# ---------------------------------------------------------------------------

def create_milestone(db: Session, data: MilestoneCreate) -> Milestone:
    _validate_estimate(db, data.estimate_id)
    milestone = Milestone(
        project=data.project,
        name=data.name,
        estimate_id=data.estimate_id,
        planned_date=data.planned_date,
        actual_date=data.actual_date,
        status=data.status,
        notes=data.notes,
    )
    return activity_repo.create_milestone(db, milestone)


def update_milestone(db: Session, milestone_id: UUID, data: MilestoneUpdate) -> Milestone:
    milestone = get_milestone_or_404(db, milestone_id)
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        return activity_repo.save_milestone(db, milestone)

    if updates.get("estimate_id") is not None:
        _validate_estimate(db, updates["estimate_id"])

    for field, value in updates.items():
        if field in ("name", "status") and value is None:
            continue
        setattr(milestone, field, value)

    return activity_repo.save_milestone(db, milestone)