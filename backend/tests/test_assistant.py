"""Stage B: the read-only assistant endpoint."""

from datetime import date
from decimal import Decimal

from app.models.models import Expense, Activity, Milestone
from tests.test_expenses import (
    add_estimate,
    create_allocation,
    create_receipt,
)


ASK_URL = "/api/v1/assistant/ask"


def ask(client, question):
    response = client.post(ASK_URL, json={"question": question})
    assert response.status_code == 200, response.text
    return response.json()


def test_assistant_requires_auth(raw_client):
    response = raw_client.post(ASK_URL, json={"question": "Overview please"})
    assert response.status_code == 401


def test_empty_question_rejected(client):
    response = client.post(ASK_URL, json={"question": "   "})
    assert response.status_code == 422


def test_assistant_available_to_all_roles(member_client, viewer_client):
    for auth_client in (member_client, viewer_client):
        body = ask(auth_client, "How much funding has been received?")
        assert body["intent"] == "funding"
        assert "0.00" in body["reply"]


def test_unknown_question_honest_fallback(client):
    body = ask(client, "What is the meaning of life?")
    assert body["intent"] == "unclear"
    assert "not sure" in body["reply"].lower()


def test_mutation_request_refused(client):
    body = ask(client, "Please create a new fund receipt for 500000")
    assert body["intent"] == "mutation"
    assert "read-only" in body["reply"].lower()


def test_mutation_request_refused_expense(client):
    body = ask(client, "Register an expense of 1000 today")
    assert body["intent"] == "mutation"
    assert "read-only" in body["reply"].lower()


def test_estimates_empty_honest(client):
    body = ask(client, "How much are the estimates?")
    assert body["intent"] == "estimates"
    assert "no estimates" in body["reply"].lower()


def test_estimates_report_amounts(client, db_session):
    add_estimate(db_session, total=Decimal("2000000.00"), title="Site Building")
    body = ask(client, "What is the total estimated amount?")
    assert body["intent"] == "estimates"
    assert "2,000,000.00" in body["reply"]
    assert any(
        ref["entity_type"] == "estimate" and ref["href"].startswith("/estimates/")
        for ref in body["references"]
    )
    assert body["references"]


def test_funding_empty_honest(client):
    body = ask(client, "How much funding has been received?")
    assert body["intent"] == "funding"
    assert "0.00" in body["reply"]


def test_funding_reports_receipts(client, db_session):
    create_receipt(client, amount="1000000.00", source="Ministry of Works")
    body = ask(client, "How much funding has been received?")
    assert body["intent"] == "funding"
    assert "1,000,000.00" in body["reply"]
    assert any(ref["entity_type"] == "fund_receipt" for ref in body["references"])


def test_allocations_report_spent_and_remaining(client, db_session):
    estimate = add_estimate(db_session)
    receipt = create_receipt(client, amount="1000000.00")
    allocation = create_allocation(
        client, receipt["id"], amount="700000.00", estimate_id=estimate.id
    )
    expense = Expense(
        expense_date=date(2026, 9, 9),
        amount=Decimal("300000.00"),
        description="Foundation concrete",
        category="FOUNDATION",
        estimate_id=estimate.id,
        allocation_id=allocation["id"],
        currency="FCFA",
        status="recorded",
    )
    db_session.add(expense)
    db_session.commit()

    body = ask(client, "Tell me about the allocations")
    assert body["intent"] == "allocations"
    assert "700,000.00" in body["reply"]
    assert "300,000.00" in body["reply"]
    assert any(ref["entity_type"] == "fund_allocation" for ref in body["references"])


def test_expenses_report_total(client, db_session):
    estimate = add_estimate(db_session)
    receipt = create_receipt(client, amount="1000000.00")
    allocation = create_allocation(
        client, receipt["id"], amount="700000.00", estimate_id=estimate.id
    )
    for label, amount in [("Cement", Decimal("150000.00")), ("Steel", Decimal("50000.00"))]:
        db_session.add(
            Expense(
                expense_date=date(2026, 9, 9),
                amount=amount,
                description=label,
                category="MATERIALS",
                estimate_id=estimate.id,
                allocation_id=allocation["id"],
                currency="FCFA",
                status="recorded",
            )
        )
    db_session.commit()

    body = ask(client, "How much have we spent in expenses?")
    assert body["intent"] == "expenses"
    assert "200,000.00" in body["reply"]
    assert any(ref["entity_type"] == "expense" for ref in body["references"])


def test_delays_list_delayed_activities(client, db_session):
    db_session.add(
        Activity(
            name="Roof installation",
            project="Test Project",
            status="in_progress",
            planned_start_date=date(2026, 8, 1),
            planned_end_date=date(2026, 8, 20),
            delay_reason="Delayed material delivery",
        )
    )
    db_session.add(
        Activity(
            name="Painting",
            project="Test Project",
            status="completed",
            planned_start_date=date(2026, 8, 1),
            planned_end_date=date(2026, 8, 20),
            actual_start_date=date(2026, 8, 1),
            actual_end_date=date(2026, 8, 22),
        )
    )
    db_session.commit()

    body = ask(client, "Which activities are delayed?")
    assert body["intent"] == "delays"
    assert "Roof installation" in body["reply"]
    assert "Painting" in body["reply"]
    assert "Delayed material delivery" in body["reply"]
    assert "2 activity" in body["reply"]
    assert any(ref["entity_type"] == "activity" for ref in body["references"])


def test_delays_empty_honest(client):
    body = ask(client, "Any delays on the schedule?")
    assert body["intent"] == "delays"
    assert "no activities are currently delayed" in body["reply"].lower()


def test_overview_includes_all_modules(client, db_session):
    estimate = add_estimate(db_session)
    receipt = create_receipt(client, amount="1000000.00")
    create_allocation(client, receipt["id"], amount="700000.00", estimate_id=estimate.id)
    db_session.add(
        Expense(
            expense_date=date(2026, 9, 9),
            amount=Decimal("100000.00"),
            description="Site works",
            category="SITE",
            estimate_id=estimate.id,
            currency="FCFA",
            status="recorded",
        )
    )
    db_session.commit()

    body = ask(client, "Give me an overview of the project status")
    assert body["intent"] == "overview"
    assert "1,000,000.00" in body["reply"]  # received
    assert "700,000.00" in body["reply"]  # allocated
    assert "100,000.00" in body["reply"]  # spent


def test_schedule_summary_reports_milestones(client, db_session):
    db_session.add(
        Milestone(
            name="Foundation complete",
            project="Test Project",
            status="completed",
            planned_date=date(2026, 9, 1),
            actual_date=date(2026, 9, 2),
        )
    )
    db_session.commit()

    body = ask(client, "How is the schedule looking?")
    assert body["intent"] == "schedule"
    assert "milestone" in body["reply"].lower()
    assert "completed" in body["reply"].lower()


def test_milestones_reported(client, db_session):
    db_session.add(
        Milestone(
            name="Handover",
            project="Test Project",
            status="pending",
            planned_date=date(2026, 12, 15),
        )
    )
    db_session.commit()

    body = ask(client, "What milestones are planned?")
    assert body["intent"] == "milestones"
    assert "Handover" in body["reply"]
    assert body["references"]


def test_estimate_trace_reports_allocated_and_spent(client, db_session):
    estimate = add_estimate(db_session, total=Decimal("5000000.00"), title="MOLA FAKO Construction Project")
    receipt = create_receipt(client, amount="3000000.00")
    create_allocation(client, receipt["id"], amount="2000000.00", estimate_id=estimate.id)
    db_session.add(
        Expense(
            expense_date=date(2026, 9, 9),
            amount=Decimal("500000.00"),
            description="Materials",
            category="MATERIALS",
            estimate_id=estimate.id,
            status="recorded",
        )
    )
    db_session.commit()

    body = ask(client, "How much of the estimate has been allocated and spent?")
    assert body["intent"] == "estimates"
    assert "2,000,000.00" in body["reply"]  # allocated
    assert "500,000.00" in body["reply"]  # spent