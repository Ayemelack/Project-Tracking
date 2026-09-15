"""Controlled backend tools for the AI Project Employee.

Every tool is a read-only operation executed server-side against the same
database the authenticated user reads. The tools are deliberately few and
narrow:

- they never accept free-form SQL,
- they never open data the existing read endpoints would hide,
- they only return records that actually exist in the database,
- each result optionally carries record references so the AI can point the
  user straight at the underlying records.

OpenAI (or any future provider) may call these tools by name; the backend
remains the authority on what is retrieved.
"""

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.models import User
from app.schemas.schemas import AssistantReference
from app.repositories.estimate_repository import estimate_repo
from app.repositories.fund_repository import fund_receipt_repo, fund_allocation_repo
from app.repositories.expense_repository import expense_repo
from app.repositories.resource_repository import resource_repo
from app.repositories.activity_repository import activity_repo
from app.repositories.user_repository import project_repo
from app.services import (
    fund_service,
    expense_service,
    resource_service,
    activity_service,
)

ZERO = Decimal("0.00")


@dataclass
class ToolResult:
    output: Any = None
    references: list[AssistantReference] = field(default_factory=list)

    def as_tool_output(self) -> str:
        try:
            return json.dumps(self.output, ensure_ascii=False)
        except (TypeError, ValueError):
            return json.dumps({"error": "Tool output could not be encoded."}, ensure_ascii=False)


def _s(value: Any) -> Any:
    """Json-safe value: Decimal/date/datetime/UUID become strings."""
    if isinstance(value, Decimal):
        return f"{value:,.2f}"
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def _ref(entity_type: str, entity_id: UUID, label: str, href: str) -> AssistantReference:
    return AssistantReference(entity_type=entity_type, entity_id=entity_id, label=label, href=href)


def resolve_project_name(db: Session, user: User) -> str | None:
    """Resolve the user's authorized project from the actual project records.

    Prefers the user's own project memberships; otherwise falls back to a
    single project on file. Returns None when there is no project record, so
    the AI never invents a project identity.
    """
    for project in project_repo.projects_for_user(db, user.id):
        return project.name
    projects = project_repo.get_all(db)
    if len(projects) == 1:
        return projects[0].name
    return None


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


def _tool_record_refs(records: list[Any], entity_type: str, label_of, href_of) -> list[AssistantReference]:
    return [_ref(entity_type, r.id, label_of(r), href_of(r)) for r in records]


def _get_project_summary(db: Session, user: User) -> ToolResult:
    funding = fund_service.get_funding_summary(db)
    expenses = expense_service.get_expense_summary(db)
    schedule = activity_service.get_activity_summary(db)
    estimates = estimate_repo.get_all(db, limit=1000)
    resources = resource_repo.get_all(db, limit=1000)
    milestones = activity_repo.list_milestones(db, limit=1000)

    output = {
        "project_name": resolve_project_name(db, user),
        "estimates": {
            "count": len(estimates),
            "total_estimated_amount": _s(sum((e.total_estimated_amount or ZERO) for e in estimates)),
        },
        "funding": {
            "total_received": _s(funding.total_received),
            "total_allocated": _s(funding.total_allocated),
            "total_unallocated": _s(funding.total_unallocated),
            "coverage_percentage": _s(funding.funding_coverage_percentage),
        },
        "expenses": {
            "total_recorded": _s(expenses.total_expenses),
            "total_authorized_excess": _s(expenses.total_authorized_excess),
        },
        "resources": {"count": len(resources)},
        "schedule": {
            "total_activities": schedule.total_activities,
            "completed": schedule.total_completed,
            "in_progress": schedule.total_in_progress,
            "not_started": schedule.total_not_started,
            "delayed": schedule.total_delayed,
            "blocked": schedule.total_blocked,
            "cancelled": schedule.total_cancelled,
            "overall_progress": _s(schedule.overall_progress),
            "milestones_total": len(milestones),
        },
    }
    return ToolResult(
        output=output,
        references=[
            _ref("estimate", e.id, e.title, f"/estimates/{e.id}") for e in estimates[:5]
        ],
    )


def _get_estimates(db: Session, user: User) -> ToolResult:
    estimates = estimate_repo.get_all(db, limit=1000)
    if not estimates:
        return ToolResult(output={"count": 0, "estimates": []})
    return ToolResult(
        output={
            "count": len(estimates),
            "estimates": [
                {
                    "id": str(e.id),
                    "title": e.title,
                    "status": e.status,
                    "total_estimated_amount": _s(e.total_estimated_amount),
                    "currency": e.currency or "FCFA",
                    "line_items_count": estimate_repo.get_count(db)
                    if len(estimates) == 1
                    else None,
                }
                for e in estimates
            ],
        },
        references=[
            _ref("estimate", e.id, e.title, f"/estimates/{e.id}") for e in estimates[:5]
        ],
    )


def _get_funding(db: Session, user: User) -> ToolResult:
    funding = fund_service.get_funding_summary(db)
    receipts = fund_receipt_repo.get_all(db, limit=1000)
    output = {
        "total_received": _s(funding.total_received),
        "total_allocated": _s(funding.total_allocated),
        "total_unallocated": _s(funding.total_unallocated),
        "funding_coverage_percentage": _s(funding.funding_coverage_percentage),
        "receipts_count": len(receipts),
        "receipts": [
            {
                "id": str(r.id),
                "amount": _s(r.amount),
                "currency": r.currency or "FCFA",
                "received_date": _s(r.received_date),
                "source": r.source,
            }
            for r in sorted(receipts, key=lambda r: r.received_date, reverse=True)[:10]
        ],
    }
    refs = [
        _ref("fund_receipt", r.id, f"{r.received_date} – {r.source}", f"/funding/{r.id}")
        for r in sorted(receipts, key=lambda r: r.received_date, reverse=True)[:5]
    ]
    return ToolResult(output=output, references=refs)


def _get_expenses(db: Session, user: User) -> ToolResult:
    summary = expense_service.get_expense_summary(db)
    recent = expense_repo.get_all(db, limit=10)
    output = {
        "total_recorded": _s(summary.total_expenses),
        "total_authorized_excess": _s(summary.total_authorized_excess),
        "by_category": [
            {"category": item.category, "total": _s(item.total)} for item in summary.by_category
        ],
        "recent_count": len(recent),
        "recent": [
            {
                "id": str(e.id),
                "expense_date": _s(e.expense_date),
                "description": e.description,
                "amount": _s(e.amount),
                "currency": e.currency or "FCFA",
                "category": e.category,
                "status": e.status,
            }
            for e in recent[:8]
        ],
    }
    refs = [
        _ref("expense", e.id, f"{e.expense_date} – {e.description[:80]}", f"/expenses/{e.id}")
        for e in recent[:5]
    ]
    return ToolResult(output=output, references=refs)


def _get_resources(db: Session, user: User) -> ToolResult:
    resources = resource_repo.get_all(db, limit=1000)
    if not resources:
        return ToolResult(output={"count": 0, "resources": []})
    items = []
    for r in resources[:10]:
        position = resource_service.computed_position(db, r)
        items.append({
            "id": str(r.id),
            "name": r.name,
            "unit": r.unit,
            "purchased_quantity": _s(position["purchased_quantity"]),
            "delivered_quantity": _s(position["delivered_quantity"]),
            "used_quantity": _s(position["used_quantity"]),
            "remaining_quantity": _s(position["remaining_quantity"]),
            "total_purchase_cost": _s(position["total_purchase_cost"]),
        })
    return ToolResult(
        output={"count": len(resources), "resources": items},
        references=[_ref("resource", r.id, r.name, f"/resources/{r.id}") for r in resources[:5]],
    )


def _get_schedule(db: Session, user: User) -> ToolResult:
    summary = activity_service.get_activity_summary(db)
    milestones = activity_repo.list_milestones(db, limit=1000)
    output = {
        "activities": {
            "total": summary.total_activities,
            "completed": summary.total_completed,
            "in_progress": summary.total_in_progress,
            "not_started": summary.total_not_started,
            "delayed": summary.total_delayed,
            "blocked": summary.total_blocked,
            "cancelled": summary.total_cancelled,
            "overall_progress": _s(summary.overall_progress),
        },
        "milestones": {
            "total": len(milestones),
            "completed": sum(1 for m in milestones if m.status == "completed"),
            "missed": sum(1 for m in milestones if m.status == "missed"),
        },
    }
    return ToolResult(output=output)


def _get_delays(db: Session, user: User) -> ToolResult:
    activities = activity_repo.get_all(db, limit=1000)
    delayed = []
    for activity in activities:
        is_delayed, days = activity_service.compute_delay(activity)
        if is_delayed:
            delayed.append((activity, days))
    output = {
        "count": len(delayed),
        "delayed_activities": [
            {
                "id": str(activity.id),
                "name": activity.name,
                "status": activity.status,
                "days_delayed": days,
                "delay_reason": activity.delay_reason,
            }
            for activity, days in delayed[:20]
        ],
    }
    refs = [
        _ref("activity", activity.id, activity.name, f"/schedule/{activity.id}")
        for activity, _ in delayed[:5]
    ]
    return ToolResult(output=output, references=refs)


_RECORD_FETCHERS = {
    "estimate": (estimate_repo.get_by_id, lambda r: (f"/estimates/{r.id}", r.title)),
    "fund_receipt": (fund_receipt_repo.get_by_id, lambda r: (f"/funding/{r.id}", r.source)),
    "expense": (expense_repo.get_by_id, lambda r: (f"/expenses/{r.id}", r.description)),
    "resource": (resource_repo.get_by_id, lambda r: (f"/resources/{r.id}", r.name)),
    "activity": (activity_repo.get_by_id, lambda r: (f"/schedule/{r.id}", r.name)),
    "milestone": (activity_repo.get_milestone, lambda r: (f"/schedule", r.name)),
}

_RECORD_FIELD_MAP = {
    "estimate": lambda r: {
        "id": str(r.id),
        "title": r.title,
        "status": r.status,
        "total_estimated_amount": _s(r.total_estimated_amount),
        "currency": r.currency or "FCFA",
    },
    "fund_receipt": lambda r: {
        "id": str(r.id),
        "amount": _s(r.amount),
        "currency": r.currency or "FCFA",
        "received_date": _s(r.received_date),
        "source": r.source,
        "reference": r.reference,
        "purpose": r.purpose,
    },
    "expense": lambda r: {
        "id": str(r.id),
        "amount": _s(r.amount),
        "currency": r.currency or "FCFA",
        "expense_date": _s(r.expense_date),
        "description": r.description,
        "category": r.category,
        "status": r.status,
    },
    "resource": lambda r: {
        "id": str(r.id),
        "name": r.name,
        "unit": r.unit,
    },
    "activity": lambda r: {
        "id": str(r.id),
        "name": r.name,
        "status": r.status,
        "progress_percentage": r.progress_percentage,
    },
    "milestone": lambda r: {
        "id": str(r.id),
        "name": r.name,
        "status": r.status,
    },
}


def _get_record(db: Session, user: User, record_type: str, record_id: str) -> ToolResult:
    fetcher, link = _RECORD_FETCHERS.get(record_type) or (None, None)
    if fetcher is None:
        return ToolResult(
            output={"error": f"Unknown record type '{record_type}'.", "found": False}
        )
    try:
        parsed_id = UUID(record_id)
    except (ValueError, TypeError):
        return ToolResult(output={"error": "Invalid record id.", "found": False})
    record = fetcher(db, parsed_id)
    if record is None:
        return ToolResult(output={"error": "No such record exists.", "found": False})
    href, label = link(record)
    return ToolResult(
        output={"found": True, "record_type": record_type, "record": _RECORD_FIELD_MAP[record_type](record)},
        references=[_ref(record_type, record.id, label, href)],
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_project_summary",
        "description": (
            "Get the authenticated user's authorized project overview: estimate totals, "
            "funding received/allocated/unallocated, recorded expenses, resource count and "
            "schedule status. No arguments."
        ),
        "handler": _get_project_summary,
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_estimates",
        "description": "Get the verified estimates on file with their totals, status and currency. No arguments.",
        "handler": _get_estimates,
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_funding",
        "description": "Get the verified funding records: total received, allocated, unallocated and recent receipts. No arguments.",
        "handler": _get_funding,
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_expenses",
        "description": "Get the verified expense records: total recorded expenses, breakdown by category and recent expenses. No arguments.",
        "handler": _get_expenses,
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_resources",
        "description": "Get verified material/resource records with computed purchased, delivered, used and remaining quantities. No arguments.",
        "handler": _get_resources,
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_schedule",
        "description": "Get verified project schedule state: activities by status, overall progress and milestone counts. No arguments.",
        "handler": _get_schedule,
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_delays",
        "description": "Get the verified list of currently delayed activities with days delayed and reasons. No arguments.",
        "handler": _get_delays,
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_record",
        "description": (
            "Get a single verified record by type and id so the AI can confirm specifics. "
            "Allowed types: estimate, fund_receipt, expense, resource, activity, milestone."
        ),
        "handler": lambda db, user, **kw: _get_record(db, user, **kw),
        "parameters": {
            "type": "object",
            "properties": {
                "record_type": {
                    "type": "string",
                    "enum": ["estimate", "fund_receipt", "expense", "resource", "activity", "milestone"],
                },
                "record_id": {"type": "string", "description": "The record's UUID."},
            },
            "required": ["record_type", "record_id"],
            "additionalProperties": False,
        },
    },
]

TOOL_SPECS = [
    {
        "type": "function",
        "name": t["name"],
        "description": t["description"],
        "parameters": t["parameters"],
    }
    for t in _TOOLS
]

_TOOL_HANDLERS = {t["name"]: t["handler"] for t in _TOOLS}


def execute_tool(db: Session, user: User, name: str, arguments: str | None = None) -> ToolResult:
    handler = _TOOL_HANDLERS.get(name)
    if handler is None:
        return ToolResult(output={"error": f"Tool '{name}' is not available.", "executed": False})
    parsed = {}
    if arguments:
        try:
            parsed = json.loads(arguments) if isinstance(arguments, str) else arguments
            if not isinstance(parsed, dict):
                parsed = {}
        except json.JSONDecodeError:
            return ToolResult(output={"error": "Tool arguments were not valid JSON.", "executed": False})
    try:
        result = handler(db, user, **parsed)
        if not isinstance(result, ToolResult):
            result = ToolResult(output=result)
        result.output = {"executed": True, **result.output} if isinstance(result.output, dict) else result.output
        return result
    except Exception:  # noqa: BLE001 - tool failures must never crash the AI loop
        return ToolResult(output={"error": "The requested record lookup failed.", "executed": False})