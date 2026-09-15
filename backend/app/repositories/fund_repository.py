from datetime import datetime, timezone
from uuid import UUID
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import FundReceipt, FundAllocation, FundAuditLog
from app.schemas.schemas import FundReceiptCreate, FundAllocationCreate


ZERO = Decimal("0.00")


class FundReceiptRepository:
    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[FundReceipt]:
        return (
            db.query(FundReceipt)
            .order_by(FundReceipt.received_date.desc(), FundReceipt.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_count(self, db: Session) -> int:
        return db.query(FundReceipt).count()

    def get_by_id(self, db: Session, receipt_id: UUID) -> FundReceipt | None:
        return db.query(FundReceipt).filter(FundReceipt.id == receipt_id).first()

    def create(self, db: Session, data: FundReceiptCreate) -> FundReceipt:
        receipt = FundReceipt(
            estimate_id=data.estimate_id,
            amount=data.amount,
            currency=data.currency.upper(),
            received_date=data.received_date,
            source=data.source,
            reference=data.reference,
            purpose=data.purpose,
            notes=data.notes,
            status="recorded",
        )
        db.add(receipt)
        db.commit()
        db.refresh(receipt)
        return receipt

    def allocated_total_per_receipt(self, db: Session) -> dict[UUID, Decimal]:
        rows = (
            db.query(
                FundAllocation.fund_receipt_id,
                func.sum(FundAllocation.amount),
            )
            .filter(FundAllocation.status == "allocated")
            .group_by(FundAllocation.fund_receipt_id)
            .all()
        )
        return {row[0]: (row[1] or ZERO) for row in rows}


class FundAllocationRepository:
    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[FundAllocation]:
        return (
            db.query(FundAllocation)
            .order_by(FundAllocation.allocation_date.desc(), FundAllocation.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_receipt(self, db: Session, receipt_id: UUID) -> list[FundAllocation]:
        return (
            db.query(FundAllocation)
            .filter(FundAllocation.fund_receipt_id == receipt_id)
            .order_by(FundAllocation.allocation_date.desc(), FundAllocation.created_at.desc())
            .all()
        )

    def get_by_id(self, db: Session, allocation_id: UUID) -> FundAllocation | None:
        return db.query(FundAllocation).filter(FundAllocation.id == allocation_id).first()

    def get_active_allocated_total(self, db: Session, receipt_id: UUID) -> Decimal:
        result = (
            db.query(func.sum(FundAllocation.amount))
            .filter(
                FundAllocation.fund_receipt_id == receipt_id,
                FundAllocation.status == "allocated",
            )
            .scalar()
        )
        return result or ZERO

    def create(self, db: Session, receipt_id: UUID, data: FundAllocationCreate) -> FundAllocation:
        allocation = FundAllocation(
            fund_receipt_id=receipt_id,
            estimate_id=data.estimate_id,
            category=data.category,
            amount=data.amount,
            purpose=data.purpose,
            responsible_person=data.responsible_person,
            allocation_date=data.allocation_date or datetime.now(timezone.utc).date(),
            notes=data.notes,
            status="allocated",
        )
        db.add(allocation)
        db.commit()
        db.refresh(allocation)
        return allocation

    def cancel(self, db: Session, allocation: FundAllocation) -> FundAllocation:
        allocation.status = "cancelled"
        db.commit()
        db.refresh(allocation)
        return allocation


class AuditRepository:
    def log(
        self,
        db: Session,
        entity_type: str,
        entity_id: UUID,
        action: str,
        field_name: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
        reason: str | None = None,
        created_by: str | None = None,
    ) -> FundAuditLog:
        entry = FundAuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            created_by=created_by or "system",
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry


fund_receipt_repo = FundReceiptRepository()
fund_allocation_repo = FundAllocationRepository()
fund_audit_repo = AuditRepository()