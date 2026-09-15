from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import Activity, Milestone


class ActivityRepository:
    def get_all(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
        project_stage: str | None = None,
        project: str | None = None,
    ) -> list[Activity]:
        query = db.query(Activity)
        if status:
            query = query.filter(Activity.status == status)
        if project_stage:
            query = query.filter(Activity.project_stage == project_stage)
        if project:
            query = query.filter(Activity.project == project)
        return (
            query.order_by(
                Activity.planned_start_date.asc().nulls_last(),
                Activity.created_at.asc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_count(
        self,
        db: Session,
        status: str | None = None,
        project_stage: str | None = None,
        project: str | None = None,
    ) -> int:
        query = db.query(Activity)
        if status:
            query = query.filter(Activity.status == status)
        if project_stage:
            query = query.filter(Activity.project_stage == project_stage)
        if project:
            query = query.filter(Activity.project == project)
        return query.count()

    def get_by_id(self, db: Session, activity_id: UUID) -> Activity | None:
        return db.query(Activity).filter(Activity.id == activity_id).first()

    def create(self, db: Session, activity: Activity) -> Activity:
        db.add(activity)
        db.commit()
        db.refresh(activity)
        return activity

    def save(self, db: Session, activity: Activity) -> Activity:
        db.commit()
        db.refresh(activity)
        return activity

    def status_counts(self, db: Session) -> dict[str, int]:
        rows = (
            db.query(Activity.status, func.count(Activity.id))
            .group_by(Activity.status)
            .all()
        )
        return {row[0]: row[1] for row in rows}

    def average_progress(self, db: Session) -> float | None:
        result = (
            db.query(func.avg(Activity.progress_percentage))
            .filter(Activity.status != "cancelled")
            .scalar()
        )
        return round(float(result), 2) if result is not None else None

    # ------------------------------------------------------------------
    # Milestones
    # ------------------------------------------------------------------

    def list_milestones(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
        project: str | None = None,
    ) -> list[Milestone]:
        query = db.query(Milestone)
        if status:
            query = query.filter(Milestone.status == status)
        if project:
            query = query.filter(Milestone.project == project)
        return (
            query.order_by(
                Milestone.planned_date.asc().nulls_last(),
                Milestone.created_at.asc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def milestone_count(
        self,
        db: Session,
        status: str | None = None,
        project: str | None = None,
    ) -> int:
        query = db.query(Milestone)
        if status:
            query = query.filter(Milestone.status == status)
        if project:
            query = query.filter(Milestone.project == project)
        return query.count()

    def get_milestone(self, db: Session, milestone_id: UUID) -> Milestone | None:
        return db.query(Milestone).filter(Milestone.id == milestone_id).first()

    def create_milestone(self, db: Session, milestone: Milestone) -> Milestone:
        db.add(milestone)
        db.commit()
        db.refresh(milestone)
        return milestone

    def save_milestone(self, db: Session, milestone: Milestone) -> Milestone:
        db.commit()
        db.refresh(milestone)
        return milestone


activity_repo = ActivityRepository()