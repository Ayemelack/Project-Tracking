"""Stage B: the project assistant.

The assistant answers natural-language questions with data read straight from
the same database the user uses. It is strictly read-only: it reports facts
exactly as stored/computed by the existing services and never performs a write.
A question that clearly asks for a mutation is refused with an honest reply.
"""

import re
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.models import Estimate, FundAllocation, Activity, User
from app.repositories.fund_repository import (
    fund_receipt_repo,
    fund_allocation_repo,
)
from app.repositories.expense_repository import expense_repo
from app.repositories.resource_repository import resource_repo
from app.repositories.activity_repository import activity_repo
from app.services import (
    fund_service,
    expense_service,
    activity_service,
    resource_service,
)
from app.schemas.schemas import (
    AssistantAttentionItem,
    AssistantBriefing,
    AssistantReference,
    AssistantReply,
)


ZERO = Decimal("0.00")

# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

_MUTATION_VERBS = {
    "create",
    "add",
    "delete",
    "remove",
    "cancel",
    "reverse",
    "update",
    "edit",
    "modify",
    "record",
    "register",
    "post",
    "insert",
    "enter",
    "approve",
    "reject",
    "attach",
    "upload",
    "confirm",
    "mark",
    "set",
}

_FILLER_WORDS = {
    "can",
    "could",
    "would",
    "should",
    "will",
    "may",
    "might",
    "do",
    "does",
    "did",
    "please",
    "kindly",
    "you",
    "i",
    "we",
    "me",
    "us",
    "help",
    "with",
    "to",
    "for",
    "a",
    "an",
    "the",
}

_TOPIC_KEYWORDS = {
    "estimates": ("estimate", "devis", "budget", "bill of quantities", "boq"),
    "funding": ("fund", "funding", "received", "receipt", "disbursed", "financed", "money come"),
    "allocations": ("allocat",),
    "expenses": ("expense", "spent", "expenditure", "payment", "paid out"),
    "resources": ("resource", "material", "stock", "inventory", "supplies", "purchase"),
    "delays": ("delay", "delayed", "late", "overdue", "behind schedule"),
    "schedule": ("schedule", "activity", "task", "progress", "travaux"),
    "milestones": ("milestone", "phase gate"),
}

_TOPIC_ORDER = (
    "delays",
    "allocations",
    "funding",
    "expenses",
    "resources",
    "milestones",
    "estimates",
    "schedule",
)


def _clean_words(question: str) -> list[str]:
    text = re.sub(r"[^a-zA-Z0-9 ]+", " ", question.lower())
    return [word for word in text.split() if word]


def _intends_to_mutate(question: str) -> bool:
    words = _clean_words(question)
    for word in words[:8]:
        if not word or word in _FILLER_WORDS:
            continue
        # "reversed", "recorded", "added" etc. describe past facts, not actions.
        if word.rstrip("eds") in _MUTATION_VERBS and not word.endswith(("ed", "s")):
            return True
        if word in _MUTATION_VERBS:
            return True
    return False


def _detect_topic(question: str) -> str | None:
    text = re.sub(r"[^a-zA-Z ]+", " ", question.lower())
    # "How much of the estimate has been allocated and spent?" is about the
    # estimate -> allocation -> expense trace, not just one module.
    if (
        any(word in text for word in ("estimate", "budget", "boq"))
        and "allocat" in text
        and any(word in text for word in ("spent", "expense", "expenditure"))
    ):
        return "estimate2allocations"
    for topic in _TOPIC_ORDER:
        for keyword in _TOPIC_KEYWORDS[topic]:
            if keyword in text:
                return topic
    return None


def _is_overview(question: str) -> bool:
    text = re.sub(r"[^a-zA-Z ]+", " ", question.lower())
    return any(
        marker in text
        for marker in ("overview", "summary", "status", "how is", "how's", "at a glance", "everything", "overall")
    )


# ---------------------------------------------------------------------------
# Formatting helpers (numbers are shown exactly as stored)
# ---------------------------------------------------------------------------

def _fmt(value) -> str:
    return f"{fund_service.money(value):,.2f}"


def _ref(entity_type: str, entity_id: UUID, label: str, href: str) -> AssistantReference:
    return AssistantReference(entity_type=entity_type, entity_id=entity_id, label=label, href=href)


def _trim_refs(refs: Iterable[AssistantReference], limit: int = 5) -> list[AssistantReference]:
    return list(refs)[:limit]


# ---------------------------------------------------------------------------
# Read-only data builders (only facts that are already computed/stored)
# ---------------------------------------------------------------------------

def _overview_builder(db: Session) -> AssistantReply:
    funding = fund_service.get_funding_summary(db)
    expenses = expense_service.get_expense_summary(db)
    activity_summary = activity_service.get_activity_summary(db)
    estimate_count = db.query(Estimate).count()
    resource_count = resource_repo.get_count(db)

    lines = [
        "Here is the current recorded state of the project:",
        f"- Estimates: {estimate_count} estimate(s) on file with a total estimated amount of {_fmt(funding.approved_estimated_amount)}.",
        f"- Funds: {_fmt(funding.total_received)} received, {_fmt(funding.total_allocated)} allocated and {_fmt(funding.total_unallocated)} still unallocated.",
        f"- Expenses: {_fmt(expenses.total_expenses)} recorded.",
        f"- Resources: {resource_count} resource(s) tracked.",
        f"- Schedule: {activity_summary.total_activities} activity(ies), {activity_summary.total_completed} completed, {activity_summary.total_delayed} delayed.",
    ]
    return AssistantReply(intent="overview", reply="\n".join(lines))


def _estimates_builder(db: Session) -> AssistantReply:
    estimates = estimate_repo_get_all(db)
    if not estimates:
        return AssistantReply(
            intent="estimates",
            reply="There are no estimates on file yet, so I have nothing to report about them.",
        )

    total = sum((estimate.total_estimated_amount or ZERO) for estimate in estimates)
    lines = [
        f"There are {len(estimates)} estimate(s) on file with a combined total of {_fmt(total)}:"
    ]
    refs: list[AssistantReference] = []
    for estimate in estimates:
        currency = estimate.currency or "FCFA"
        lines.append(
            f"- {estimate.title} ({estimate.status}): {_fmt(estimate.total_estimated_amount)} {currency}"
        )
        refs.append(_ref("estimate", estimate.id, estimate.title, f"/estimates/{estimate.id}"))
    return AssistantReply(intent="estimates", reply="\n".join(lines), references=refs)


def estimate_repo_get_all(db: Session):
    from app.repositories.estimate_repository import estimate_repo

    return estimate_repo.get_all(db, limit=1000)


def _funding_builder(db: Session) -> AssistantReply:
    funding = fund_service.get_funding_summary(db)
    receipts = fund_receipt_repo.get_all(db, limit=1000)

    lines = [
        f"Total received: {_fmt(funding.total_received)}.",
        f"Allocated: {_fmt(funding.total_allocated)}.",
        f"Still unallocated: {_fmt(funding.total_unallocated)}.",
    ]
    if funding.funding_coverage_percentage is not None:
        lines.append(
            f"Funding coverage against confirmed estimates: {funding.funding_coverage_percentage:.2f}%."
        )
    if receipts:
        lines.append("Latest receipts:")
        refs: list[AssistantReference] = []
        for receipt in sorted(receipts, key=lambda r: r.received_date, reverse=True)[:5]:
            currency = receipt.currency or "FCFA"
            lines.append(
                f"- {receipt.received_date}: {_fmt(receipt.amount)} {currency} from {receipt.source}"
            )
            refs.append(
                _ref(
                    "fund_receipt",
                    receipt.id,
                    f"{receipt.received_date} – {receipt.source}",
                    f"/funding/{receipt.id}",
                )
            )
        return AssistantReply(
            intent="funding", reply="\n".join(lines), references=_trim_refs(refs)
        )
    return AssistantReply(intent="funding", reply="\n".join(lines))


def _allocations_builder(db: Session) -> AssistantReply:
    allocations = fund_allocation_repo.get_all(db, limit=1000)
    active = [a for a in allocations if a.status == "allocated"]
    if not active:
        return AssistantReply(
            intent="allocations",
            reply="There are no active allocations yet, so there is nothing to report about them.",
        )

    lines = [f"There are {len(active)} active allocation(s):"]
    refs: list[AssistantReference] = []
    for allocation in active:
        spent = expense_service.allocation_spent(db, allocation.id)
        remaining = money_sub(allocation.amount, spent)
        currency = allocation.fund_receipt.currency if allocation.fund_receipt else "FCFA"
        purpose = allocation.purpose or allocation.category or "unnamed allocation"
        lines.append(
            f"- {purpose}: {_fmt(allocation.amount)} {currency}, {_fmt(spent)} spent, {_fmt(remaining)} remaining"
        )
        refs.append(
            _ref(
                "fund_allocation",
                allocation.id,
                str(purpose),
                f"/funding/{allocation.fund_receipt_id}",
            )
        )
    return AssistantReply(
        intent="allocations", reply="\n".join(lines), references=_trim_refs(refs)
    )


def money_sub(left, right) -> Decimal:
    return fund_service.money(left) - fund_service.money(right)


def _expenses_builder(db: Session) -> AssistantReply:
    summary = expense_service.get_expense_summary(db)
    if summary.total_expenses <= ZERO:
        return AssistantReply(
            intent="expenses",
            reply="No expenses have been recorded yet, so I have nothing to report.",
        )

    lines = [f"Total recorded expenses: {_fmt(summary.total_expenses)}."]
    if summary.total_authorized_excess > ZERO:
        lines.append(
            f"Of that, {_fmt(summary.total_authorized_excess)} is authorized excess beyond allocation amounts."
        )
    if summary.by_category:
        lines.append("Breakdown by category:")
        for item in summary.by_category:
            lines.append(f"- {item.category}: {_fmt(item.total)}")

    refs: list[AssistantReference] = []
    recent = expense_repo.get_all(db, limit=5)
    for expense in recent:
        currency = expense.currency or "FCFA"
        refs.append(
            _ref(
                "expense",
                expense.id,
                f"{expense.expense_date} – {expense.description[:80]}",
                f"/expenses/{expense.id}",
            )
        )
    return AssistantReply(
        intent="expenses", reply="\n".join(lines), references=_trim_refs(refs)
    )


def _resources_builder(db: Session) -> AssistantReply:
    resources = resource_repo.get_all(db, limit=1000)
    if not resources:
        return AssistantReply(
            intent="resources",
            reply="There are no resources tracked yet, so I have nothing to report about them.",
        )

    total_purchase_cost = ZERO
    for resource in resources:
        total_purchase_cost += resource_service.computed_position(db, resource)["total_purchase_cost"]

    lines = [
        f"{len(resources)} resource(s) are tracked, with {_fmt(total_purchase_cost)} recorded in purchases:"
    ]
    refs: list[AssistantReference] = []
    for resource in resources[:5]:
        position = resource_service.computed_position(db, resource)
        lines.append(
            f"- {resource.name}: {_fmt(position['remaining_quantity'])} {resource.unit or ''} remaining "
            f"(purchased {_fmt(position['purchased_quantity'])} {resource.unit or ''})"
        )
        refs.append(_ref("resource", resource.id, resource.name, f"/resources/{resource.id}"))
    return AssistantReply(
        intent="resources", reply="\n".join(lines), references=_trim_refs(refs)
    )


def _delays_builder(db: Session) -> AssistantReply:
    activities = activity_repo.get_all(db, limit=1000)
    delayed: list[tuple[Activity, int]] = []
    for activity in activities:
        is_delayed, days = activity_service.compute_delay(activity)
        if is_delayed:
            delayed.append((activity, days))

    if not delayed:
        return AssistantReply(
            intent="delays",
            reply="No activities are currently delayed; the schedule is on track.",
        )

    lines = [f"{len(delayed)} activity(ies) are currently delayed:"]
    refs: list[AssistantReference] = []
    for activity, days in delayed:
        detail = ""
        if activity.delay_reason:
            detail = f" Reason: {activity.delay_reason}"
        lines.append(f"- {activity.name} (delayed {days} day(s), {activity.status}).{detail}")
        refs.append(_ref("activity", activity.id, activity.name, f"/schedule/{activity.id}"))
    return AssistantReply(
        intent="delays", reply="\n".join(lines), references=_trim_refs(refs)
    )


def _schedule_builder(db: Session) -> AssistantReply:
    summary = activity_service.get_activity_summary(db)
    milestones = activity_repo.list_milestones(db, limit=1000)

    lines = [
        f"{summary.total_activities} activity(ies) overall: "
        f"{summary.total_completed} completed, {summary.total_in_progress} in progress, "
        f"{summary.total_not_started} not started, {summary.total_delayed} delayed, "
        f"{summary.total_blocked} blocked, {summary.total_cancelled} cancelled.",
        f"Average progress across scheduled work: {summary.overall_progress or 0}%.",
    ]
    if milestones:
        done = [m for m in milestones if m.status == "completed"]
        missed = [m for m in milestones if m.status == "missed"]
        lines.append(
            f"{len(milestones)} milestone(s) overall: {len(done)} completed, {len(missed)} missed."
        )
    return AssistantReply(intent="schedule", reply="\n".join(lines))


def _milestones_builder(db: Session) -> AssistantReply:
    milestones = activity_repo.list_milestones(db, limit=1000)
    if not milestones:
        return AssistantReply(
            intent="milestones",
            reply="There are no milestones yet, so I have nothing to report about them.",
        )

    lines = [f"{len(milestones)} milestone(s) on file:"]
    refs: list[AssistantReference] = []
    for milestone in milestones:
        actual = f" (actual {milestone.actual_date})" if milestone.actual_date else ""
        lines.append(f"- {milestone.name}: {milestone.status}{actual}")
        refs.append(_ref("milestone", milestone.id, milestone.name, f"/schedule"))
    return AssistantReply(
        intent="milestones", reply="\n".join(lines), references=_trim_refs(refs)
    )


# The "estimate → allocations → expenses" traceability question, e.g.
# "how much of the estimate has been allocated and spent".
def _estimate_trace_builder(db: Session) -> AssistantReply:
    estimates = estimate_repo_get_all(db)
    if not estimates:
        return AssistantReply(
            intent="estimates",
            reply="There are no estimates on file yet, so I have nothing to report.",
        )

    spent_by_estimate = expense_repo.spent_total_per_estimate(db)

    lines: list[str] = []
    refs: list[AssistantReference] = []
    for estimate in estimates[:5]:
        currency = estimate.currency or "FCFA"
        approved = money_sub(estimate.total_estimated_amount, ZERO)
        allocations = (
            db.query(FundAllocation)
            .filter(
                FundAllocation.estimate_id == estimate.id,
                FundAllocation.status == "allocated",
            )
            .all()
        )
        allocated = sum((a.amount or ZERO) for a in allocations)
        spent = money_sub(spent_by_estimate.get(estimate.id, ZERO), ZERO)

        lines.append(
            f"- {estimate.title}: estimated {_fmt(approved)} {currency}, "
            f"{_fmt(allocated)} allocated, {_fmt(spent)} spent."
        )
        refs.append(_ref("estimate", estimate.id, estimate.title, f"/estimates/{estimate.id}"))
    return AssistantReply(
        intent="estimates", reply="\n".join(lines), references=_trim_refs(refs)
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

_TOPIC_BUILDERS = {
    "allocations": _allocations_builder,
    "delays": _delays_builder,
    "estimates": _estimates_builder,
    "expenses": _expenses_builder,
    "funding": _funding_builder,
    "milestones": _milestones_builder,
    "resources": _resources_builder,
    "schedule": _schedule_builder,
}


def answer(db: Session, question: str) -> AssistantReply:
    if _intends_to_mutate(question):
        return AssistantReply(
            intent="mutation",
            reply=(
                "I understand you want a change made to the records, but I am a read-only "
                "assistant. I can answer questions about the data and point you to the right "
                "page, but recording fund receipts, allocations, expenses, resources or "
                "schedule updates must be done through the regular forms. Which record would "
                "you like to look at instead?"
            ),
        )

    topic = _detect_topic(question)
    if topic is not None:
        if topic == "estimate2allocations":
            return _estimate_trace_builder(db)
        return _TOPIC_BUILDERS[topic](db)

    if _is_overview(question):
        return _overview_builder(db)

    return AssistantReply(
        intent="unclear",
        reply=(
            "I am not sure what you would like to know. I can summarize the project, or "
            "answer questions about estimates, funding and allocations, expenses, "
            "resources, delays and the schedule. For example: 'Give me an overview of "
            "the project', 'How much funding has been received?', or 'Which activities "
            "are delayed?'"
        ),
    )


# ---------------------------------------------------------------------------
# Pre-chat briefing (dynamic greeting + computed attention items)
# ---------------------------------------------------------------------------

_BRIEFING_SUGGESTIONS = [
    "Give me an overview of the project",
    "What is the current project estimate?",
    "How much funding has been received?",
    "How much have we spent in expenses?",
    "Which activities are delayed?",
]


def build_briefing(db: Session, user: User) -> AssistantBriefing:
    from app.services.assistant_tools import resolve_project_name

    project_name = resolve_project_name(db, user)
    first_name = user.full_name.strip().split()[0] if user.full_name and user.full_name.strip() else "there"

    greeting_parts = [
        f"Welcome{'' if first_name.lower() == 'there' else ', ' + first_name}.",
        f"I'm your AI Project Employee for the {project_name}."
        if project_name
        else "I'm your AI Project Employee.",
        "I answer from the project's verified records — estimates, funding, expenses, "
        "resources and the schedule — and I never change data.",
    ]
    greeting = " ".join(greeting_parts)

    attention: list[AssistantAttentionItem] = []

    funding = fund_service.get_funding_summary(db)
    estimate_count = db.query(Estimate).count()
    estimate_refs = [
        AssistantReference(
            entity_type="estimate",
            entity_id=e.id,
            label=e.title,
            href=f"/estimates/{e.id}",
        )
        for e in estimate_repo_get_all(db)[:3]
    ]
    if funding.funding_coverage_percentage is not None and funding.funding_coverage_percentage < 100:
        attention.append(
            AssistantAttentionItem(
                kind="funding",
                message=(
                    f"Funding covers {funding.funding_coverage_percentage:.2f}% of the "
                    "confirmed estimate amount."
                ),
                references=estimate_refs,
            )
        )
    elif estimate_count > 0 and funding.total_received <= ZERO:
        attention.append(
            AssistantAttentionItem(
                kind="funding",
                message="No funding has been recorded against the confirmed estimate yet.",
                references=estimate_refs,
            )
        )
    if funding.total_unallocated > ZERO:
        attention.append(
            AssistantAttentionItem(
                kind="funding",
                message=f"{_fmt(funding.total_unallocated)} of received funding is still unallocated.",
            )
        )

    delays = _delays_builder(db)
    if delays.intent == "delays" and "no activities are currently delayed" not in delays.reply.lower():
        first_lines = delays.reply.splitlines()[1:4]
        attention.append(
            AssistantAttentionItem(
                kind="delays",
                message=" ".join(line.strip() for line in first_lines if line.strip()),
                references=delays.references,
            )
        )

    milestones = activity_repo.list_milestones(db, limit=1000)
    missed = [m for m in milestones if m.status == "missed"]
    if missed:
        names = ", ".join(m.name for m in missed[:3])
        attention.append(
            AssistantAttentionItem(
                kind="milestones",
                message=f"{len(missed)} milestone(s) are marked missed: {names}.",
            )
        )

    from app.models.models import Expense, FundReceipt

    expenses_missing_evidence = (
        db.query(Expense).filter(Expense.evidence_filename.is_(None)).all()
    )
    receipts_missing_evidence = (
        db.query(FundReceipt).filter(FundReceipt.evidence_filename.is_(None)).all()
    )
    if expenses_missing_evidence:
        attention.append(
            AssistantAttentionItem(
                kind="evidence",
                message=f"{len(expenses_missing_evidence)} recorded expense(s) have no supporting evidence attached.",
                references=[
                    AssistantReference(
                        entity_type="expense",
                        entity_id=e.id,
                        label=e.description[:60] or "Expense record",
                        href=f"/expenses/{e.id}",
                    )
                    for e in expenses_missing_evidence[:5]
                ],
            )
        )
    if receipts_missing_evidence:
        attention.append(
            AssistantAttentionItem(
                kind="evidence",
                message=f"{len(receipts_missing_evidence)} fund receipt(s) have no supporting evidence attached.",
                references=[
                    AssistantReference(
                        entity_type="fund_receipt",
                        entity_id=r.id,
                        label=f"{r.received_date} – {r.source}",
                        href=f"/funding/{r.id}",
                    )
                    for r in receipts_missing_evidence[:5]
                ],
            )
        )

    total_authorized_excess = expense_service.get_expense_summary(db).total_authorized_excess
    if total_authorized_excess > ZERO:
        attention.append(
            AssistantAttentionItem(
                kind="expenses",
                message=f"{_fmt(total_authorized_excess)} of recorded expenses is authorized excess beyond allocation amounts.",
            )
        )

    return AssistantBriefing(
        greeting=greeting,
        project_name=project_name,
        attention=attention[:4],
        suggestions=list(_BRIEFING_SUGGESTIONS),
    )