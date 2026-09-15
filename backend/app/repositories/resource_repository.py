from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import Resource, ResourceMovement


ZERO = Decimal("0.00")


class ResourceRepository:
    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[Resource]:
        return (
            db.query(Resource)
            .order_by(Resource.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_count(self, db: Session) -> int:
        return db.query(Resource).count()

    def get_by_id(self, db: Session, resource_id: UUID) -> Resource | None:
        return db.query(Resource).filter(Resource.id == resource_id).first()

    def get_by_id_for_update(self, db: Session, resource_id: UUID) -> Resource | None:
        # Serializes movement writes per resource so availability checks are safe.
        return (
            db.query(Resource)
            .filter(Resource.id == resource_id)
            .with_for_update()
            .first()
        )

    def create(self, db: Session, resource: Resource) -> Resource:
        db.add(resource)
        db.commit()
        db.refresh(resource)
        return resource

    # ------------------------------------------------------------------
    # Movement ledger
    # ------------------------------------------------------------------

    def create_movement(self, db: Session, movement: ResourceMovement) -> ResourceMovement:
        db.add(movement)
        db.commit()
        db.refresh(movement)
        return movement

    def movement_by_id(self, db: Session, movement_id: UUID) -> ResourceMovement | None:
        return (
            db.query(ResourceMovement)
            .filter(ResourceMovement.id == movement_id)
            .first()
        )

    def movements(self, db: Session, resource_id: UUID) -> list[ResourceMovement]:
        return (
            db.query(ResourceMovement)
            .filter(ResourceMovement.resource_id == resource_id)
            .order_by(ResourceMovement.movement_date.asc(), ResourceMovement.created_at.asc())
            .all()
        )

    def quantity_totals(self, db: Session, resource_id: UUID) -> dict[str, Decimal]:
        """Sum of quantity grouped by movement type for one resource."""
        rows = (
            db.query(ResourceMovement.movement_type, func.sum(ResourceMovement.quantity))
            .filter(ResourceMovement.resource_id == resource_id)
            .group_by(ResourceMovement.movement_type)
            .all()
        )
        return {row[0]: (row[1] or ZERO) for row in rows}

    def purchase_cost_total(self, db: Session, resource_id: UUID) -> Decimal:
        result = (
            db.query(func.sum(ResourceMovement.total_cost))
            .filter(
                ResourceMovement.resource_id == resource_id,
                ResourceMovement.movement_type == "purchase",
            )
            .scalar()
        )
        return result or ZERO


resource_repo = ResourceRepository()