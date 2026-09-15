from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import Expense


ZERO = Decimal("0.00")


class ExpenseRepository:
    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> list[Expense]:
        return (
            db.query(Expense)
            .order_by(Expense.expense_date.desc(), Expense.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_count(self, db: Session) -> int:
        return db.query(Expense).count()

    def get_by_id(self, db: Session, expense_id: UUID) -> Expense | None:
        return db.query(Expense).filter(Expense.id == expense_id).first()

    def create(self, db: Session, expense: Expense) -> Expense:
        db.add(expense)
        db.commit()
        db.refresh(expense)
        return expense

    def update(self, db: Session, expense: Expense, update_data: dict) -> Expense:
        for key, value in update_data.items():
            setattr(expense, key, value)
        db.commit()
        db.refresh(expense)
        return expense

    def set_status(self, db: Session, expense: Expense, status: str) -> Expense:
        expense.status = status
        db.commit()
        db.refresh(expense)
        return expense

    def each_recorded(self, db: Session) -> list[Expense]:
        return db.query(Expense).filter(Expense.status == "recorded").all()

    def spent_total_per_allocation(self, db: Session) -> dict[UUID, Decimal]:
        rows = (
            db.query(Expense.allocation_id, func.sum(Expense.amount))
            .filter(
                Expense.allocation_id.isnot(None),
                Expense.status == "recorded",
            )
            .group_by(Expense.allocation_id)
            .all()
        )
        return {row[0]: (row[1] or ZERO) for row in rows}

    def spent_total_per_allocation_without_estimate(self, db: Session) -> dict[UUID, Decimal]:
        rows = (
            db.query(Expense.allocation_id, func.sum(Expense.amount))
            .filter(
                Expense.allocation_id.isnot(None),
                Expense.estimate_id.is_(None),
                Expense.status == "recorded",
            )
            .group_by(Expense.allocation_id)
            .all()
        )
        return {row[0]: (row[1] or ZERO) for row in rows}

    def spent_total_per_estimate(self, db: Session) -> dict[UUID, Decimal]:
        rows = (
            db.query(Expense.estimate_id, func.sum(Expense.amount))
            .filter(
                Expense.estimate_id.isnot(None),
                Expense.status == "recorded",
            )
            .group_by(Expense.estimate_id)
            .all()
        )
        return {row[0]: (row[1] or ZERO) for row in rows}

    def totals_by_category(self, db: Session) -> list[tuple[str | None, Decimal]]:
        rows = (
            db.query(Expense.category, func.sum(Expense.amount))
            .filter(Expense.status == "recorded")
            .group_by(Expense.category)
            .all()
        )
        return [(row[0], (row[1] or ZERO)) for row in rows]

    def total_recorded(self, db: Session) -> Decimal:
        result = (
            db.query(func.sum(Expense.amount))
            .filter(Expense.status == "recorded")
            .scalar()
        )
        return result or ZERO


expense_repo = ExpenseRepository()