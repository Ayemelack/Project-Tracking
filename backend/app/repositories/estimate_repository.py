from sqlalchemy.orm import Session
from uuid import UUID
from app.models.models import Estimate, EstimateLineItem
from app.schemas.schemas import (
    EstimateCreate, EstimateUpdate,
    EstimateLineItemCreate, EstimateLineItemUpdate,
)


class EstimateRepository:
    def get_all(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(Estimate).offset(skip).limit(limit).all()

    def get_count(self, db: Session) -> int:
        return db.query(Estimate).count()

    def get_by_id(self, db: Session, estimate_id: UUID) -> Estimate | None:
        return db.query(Estimate).filter(Estimate.id == estimate_id).first()

    def create(self, db: Session, estimate_data: EstimateCreate, stored_filename: str, original_filename: str) -> Estimate:
        grand_total_row = next(
            (item for item in estimate_data.line_items if item.section_total_type == 'grand_total' and item.total_cost),
            None,
        )
        if grand_total_row:
            total = grand_total_row.total_cost
        else:
            total = sum(
                item.total_cost for item in estimate_data.line_items
                if item.total_cost
                and item.section_total_type not in ('section_total', 'grand_total', 'material', 'labour')
            )

        db_estimate = Estimate(
            title=estimate_data.title,
            project_name=estimate_data.project_name,
            reference_number=estimate_data.reference_number,
            contractor=estimate_data.contractor,
            client=estimate_data.client,
            currency=estimate_data.currency,
            original_filename=original_filename,
            stored_filename=stored_filename,
            status="extracted",
            total_estimated_amount=total,
            notes=estimate_data.notes,
        )
        db.add(db_estimate)
        db.flush()

        for item_data in estimate_data.line_items:
            db_item = EstimateLineItem(
                estimate_id=db_estimate.id,
                item_number=item_data.item_number,
                category=item_data.category,
                description=item_data.description,
                quantity=item_data.quantity,
                unit=item_data.unit,
                unit_cost=item_data.unit_cost,
                total_cost=item_data.total_cost,
                source_page=item_data.source_page,
                section_total_type=item_data.section_total_type,
            )
            db.add(db_item)

        db.commit()
        db.refresh(db_estimate)
        return db_estimate

    def update(self, db: Session, estimate_id: UUID, estimate_data: EstimateUpdate) -> Estimate | None:
        db_estimate = self.get_by_id(db, estimate_id)
        if not db_estimate:
            return None

        update_data = estimate_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_estimate, key, value)

        db.commit()
        db.refresh(db_estimate)
        return db_estimate

    def update_status(self, db: Session, estimate_id: UUID, status: str) -> Estimate | None:
        db_estimate = self.get_by_id(db, estimate_id)
        if not db_estimate:
            return None
        db_estimate.status = status
        db.commit()
        db.refresh(db_estimate)
        return db_estimate

    def delete(self, db: Session, estimate_id: UUID) -> bool:
        db_estimate = self.get_by_id(db, estimate_id)
        if not db_estimate:
            return False
        db.delete(db_estimate)
        db.commit()
        return True

    def recalculate_total(self, db: Session, estimate_id: UUID) -> Estimate | None:
        db_estimate = self.get_by_id(db, estimate_id)
        if not db_estimate:
            return None
        grand_total_row = next(
            (item for item in db_estimate.line_items if item.section_total_type == 'grand_total' and item.total_cost),
            None,
        )
        if grand_total_row:
            total = grand_total_row.total_cost
        else:
            total = sum(
                item.total_cost for item in db_estimate.line_items
                if item.total_cost
                and item.section_total_type not in ('section_total', 'grand_total', 'material', 'labour')
            )
        db_estimate.total_estimated_amount = total
        db.commit()
        db.refresh(db_estimate)
        return db_estimate


class LineItemRepository:
    def get_by_estimate(self, db: Session, estimate_id: UUID) -> list[EstimateLineItem]:
        return db.query(EstimateLineItem).filter(
            EstimateLineItem.estimate_id == estimate_id
        ).all()

    def get_by_id(self, db: Session, item_id: UUID) -> EstimateLineItem | None:
        return db.query(EstimateLineItem).filter(EstimateLineItem.id == item_id).first()

    def create(self, db: Session, estimate_id: UUID, item_data: EstimateLineItemCreate) -> EstimateLineItem:
        db_item = EstimateLineItem(
            estimate_id=estimate_id,
            **item_data.model_dump()
        )
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item

    def update(self, db: Session, item_id: UUID, item_data: EstimateLineItemUpdate) -> EstimateLineItem | None:
        db_item = self.get_by_id(db, item_id)
        if not db_item:
            return None

        update_data = item_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_item, key, value)

        db.commit()
        db.refresh(db_item)
        return db_item

    def delete(self, db: Session, item_id: UUID) -> bool:
        db_item = self.get_by_id(db, item_id)
        if not db_item:
            return False
        db.delete(db_item)
        db.commit()
        return True

    def delete_by_estimate(self, db: Session, estimate_id: UUID):
        db.query(EstimateLineItem).filter(
            EstimateLineItem.estimate_id == estimate_id
        ).delete()
        db.commit()


estimate_repo = EstimateRepository()
line_item_repo = LineItemRepository()
