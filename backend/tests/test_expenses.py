import io
from decimal import Decimal

from sqlalchemy import select

from app.models.models import Expense, Estimate, EstimateLineItem, FundAuditLog


def add_estimate(db_session, total=Decimal("2000000.00"), status="confirmed", title="MOLA FAKO ESTIMATE"):
    estimate = Estimate(
        title=title,
        project_name="MOLA FAKO",
        reference_number="REF-001",
        original_filename="estimate.pdf",
        stored_filename="stored_estimate.pdf",
        status=status,
        total_estimated_amount=total,
    )
    db_session.add(estimate)
    db_session.commit()
    db_session.refresh(estimate)
    return estimate


def add_line_item(db_session, estimate_id, description="Concrete works", item_number="1.1"):
    item = EstimateLineItem(
        estimate_id=estimate_id,
        item_number=item_number,
        description=description,
        quantity=Decimal("100.00"),
        unit="m2",
        unit_cost=Decimal("2000.00"),
        total_cost=Decimal("200000.00"),
        category="STRUCTURES",
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def create_receipt(client, amount="1000000.00", source="Ministry of Works"):
    payload = {
        "amount": amount,
        "currency": "FCFA",
        "received_date": "2026-09-09",
        "source": source,
        "reference": "TRF-001",
        "purpose": "General construction",
    }
    response = client.post("/api/v1/funds", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def create_allocation(client, fund_id, amount="700000.00", estimate_id=None, purpose="Foundation works"):
    payload = {
        "amount": amount,
        "purpose": purpose,
        "category": "FOUNDATION",
        "responsible_person": "John Doe",
        "allocation_date": "2026-09-10",
    }
    if estimate_id:
        payload["estimate_id"] = str(estimate_id)
    response = client.post(f"/api/v1/funds/{fund_id}/allocations", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def base_payload(**overrides):
    payload = {
        "amount": "450000.00",
        "expense_date": "2026-09-15",
        "description": "Cement purchase for foundation works",
        "category": "MATERIALS",
        "supplier": "CAMACO",
        "payment_method": "BANK_TRANSFER",
        "reference": "INV-2026-014",
        "purpose": "Works on site",
        "responsible_person": "Site Manager",
        "currency": "FCFA",
        **overrides,
    }
    return payload


def post_expense(client, **overrides):
    return client.post("/api/v1/expenses", json=base_payload(**overrides))


def expense_from_db(db_session, expense_id):
    stmt = select(Expense).where(Expense.id == expense_id)
    return db_session.execute(stmt).scalar_one()


def audit_actions(db_session, expense_id):
    entries = (
        db_session.execute(
            select(FundAuditLog)
            .where(FundAuditLog.entity_type == "expense", FundAuditLog.entity_id == expense_id)
            .order_by(FundAuditLog.created_at)
        )
        .scalars()
        .all()
    )
    return [entry.action for entry in entries]


class TestExpenseCreation:
    def test_create_expense(self, client):
        response = post_expense(client)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["amount"] == "450000.00"
        assert body["status"] == "recorded"
        assert body["description"] == "Cement purchase for foundation works"
        assert body["payment_method"] == "BANK_TRANSFER"
        assert body["currency"] == "FCFA"
        assert body["id"]

    def test_create_expense_linked_to_estimate_and_allocation(self, client, db_session):
        estimate = add_estimate(db_session)
        receipt = create_receipt(client)
        allocation = create_allocation(client, receipt["id"], estimate_id=estimate.id)
        response = post_expense(client, allocation_id=allocation["id"], estimate_id=str(estimate.id))
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["allocation_id"] == allocation["id"]
        assert body["estimate_id"] == str(estimate.id)

    def test_create_expense_defaults_estimate_from_allocation(self, client, db_session):
        estimate = add_estimate(db_session)
        receipt = create_receipt(client)
        allocation = create_allocation(client, receipt["id"], estimate_id=estimate.id)
        response = post_expense(client, allocation_id=allocation["id"])
        assert response.status_code == 201, response.text
        assert response.json()["estimate_id"] == str(estimate.id)

    def test_expense_persisted(self, client, db_session):
        response = post_expense(client, reference="INV-PERSIST")
        assert response.status_code == 201, response.text
        row = expense_from_db(db_session, response.json()["id"])
        assert row.amount == Decimal("450000.00")
        assert row.description == "Cement purchase for foundation works"
        assert row.status == "recorded"
        assert row.payment_method == "BANK_TRANSFER"

    def test_audit_log_preserves_history(self, client, db_session):
        expense_id = post_expense(client).json()["id"]
        assert "created" in audit_actions(db_session, expense_id)


class TestAmountCalculations:
    def test_backend_computes_total_from_quantity_and_unit_price(self, client):
        response = post_expense(
            client,
            amount=None,
            quantity="2.5",
            unit="bags",
            unit_price="3000.00",
        )
        assert response.status_code == 201, response.text
        assert response.json()["amount"] == "7500.00"
        assert response.json()["quantity"] == "2.50"
        assert response.json()["unit_price"] == "3000.00"

    def test_mismatched_client_total_rejected(self, client):
        response = post_expense(
            client,
            amount="8000.00",
            quantity="2.5",
            unit="bags",
            unit_price="3000.00",
        )
        assert response.status_code == 422
        assert "does not match" in response.json()["detail"]

    def test_quantity_without_unit_price_rejected(self, client):
        response = post_expense(client, amount="100.00", quantity="2.5", unit="bags")
        assert response.status_code == 422

    def test_unit_price_without_quantity_rejected(self, client):
        response = post_expense(client, amount="100.00", unit_price="3000.00")
        assert response.status_code == 422

    def test_huge_purchase_total_rejected(self, client):
        response = post_expense(
            client,
            amount="50000000000000.00",
            quantity="10000",
            unit="units",
            unit_price="5000000000.00",
        )
        assert response.status_code == 422

    def test_matching_client_total_accepted(self, client):
        response = post_expense(
            client,
            amount="7500.00",
            quantity="2.5",
            unit="bags",
            unit_price="3000.00",
        )
        assert response.status_code == 201, response.text
        assert response.json()["amount"] == "7500.00"


class TestExpenseValidation:
    def test_missing_amount_and_purchase_info_rejected(self, client):
        assert post_expense(client, amount=None).status_code == 422

    def test_zero_amount_rejected(self, client):
        assert post_expense(client, amount="0").status_code == 422

    def test_negative_amount_rejected(self, client):
        assert post_expense(client, amount="-100").status_code == 422

    def test_huge_amount_rejected(self, client):
        assert post_expense(client, amount="10000000000000000").status_code == 422

    def test_missing_date_rejected(self, client):
        assert post_expense(client, expense_date=None).status_code == 422

    def test_invalid_date_rejected(self, client):
        assert post_expense(client, expense_date="2026-13-40").status_code == 422
        assert post_expense(client, expense_date="not-a-date").status_code == 422

    def test_missing_description_rejected(self, client):
        assert post_expense(client, description=None).status_code == 422

    def test_whitespace_description_rejected(self, client):
        assert post_expense(client, description="   ").status_code == 422

    def test_description_over_max_length_rejected(self, client):
        assert post_expense(client, description="x" * 2001).status_code == 422

    def test_invalid_payment_method_rejected(self, client):
        assert post_expense(client, payment_method="CRYPTOCURRENCY").status_code == 422

    def test_valid_payment_methods_accepted(self, client):
        for method in ("CASH", "BANK_TRANSFER", "CHEQUE", "MOBILE_MONEY", "CARD", "OTHER"):
            assert post_expense(client, payment_method=method).status_code == 201

    def test_lowercase_payment_method_normalized(self, client):
        response = post_expense(client, payment_method="cash")
        assert response.status_code == 201, response.text
        assert response.json()["payment_method"] == "CASH"

    def test_invalid_currency_rejected(self, client):
        assert post_expense(client, currency="USD").status_code == 422

    def test_currency_mismatch_with_allocation_rejected(self, client, db_session):
        estimate = add_estimate(db_session)
        receipt = create_receipt(client)
        allocation = create_allocation(client, receipt["id"], estimate_id=estimate.id)
        response = post_expense(client, allocation_id=allocation["id"], currency="XAF")
        assert response.status_code == 422

    def test_sql_injection_in_text_fields_stored_safely(self, client, db_session):
        response = post_expense(
            client,
            description="Cement'); DROP TABLE expenses;--",
            supplier="<script>alert(1)</script>",
            notes="' OR '1'='1",
        )
        assert response.status_code == 201, response.text
        row = expense_from_db(db_session, response.json()["id"])
        assert row.description == "Cement'); DROP TABLE expenses;--"
        assert row.supplier == "<script>alert(1)</script>"

    def test_sql_injection_in_numeric_fields_rejected(self, client):
        assert post_expense(client, amount="450000 OR 1=1").status_code == 422
        assert (
            post_expense(client, expense_date="2026-09-15; DROP TABLE expenses;--").status_code
            == 422
        )

    def test_unknown_allocation_rejected(self, client):
        import uuid
        response = post_expense(client, allocation_id=str(uuid.uuid4()))
        assert response.status_code == 404

    def test_allocation_to_cancelled_allocation_rejected(self, client, db_session):
        estimate = add_estimate(db_session)
        receipt = create_receipt(client)
        allocation = create_allocation(client, receipt["id"], estimate_id=estimate.id)
        assert client.post(
            f"/api/v1/allocations/{allocation['id']}/cancel", json={"reason": "reallocated"}
        ).status_code == 200
        response = post_expense(client, allocation_id=allocation["id"])
        assert response.status_code == 409

    def test_line_item_mismatch_rejected(self, client, db_session):
        estimate_a = add_estimate(db_session, title="EST A")
        estimate_b = add_estimate(db_session, title="EST B")
        item = add_line_item(db_session, estimate_a.id)
        response = post_expense(
            client,
            estimate_id=str(estimate_b.id),
            estimate_line_item_id=str(item.id),
        )
        assert response.status_code == 422


class TestAllocationLimits:
    def test_expense_exceeding_remaining_allocation_rejected(self, client, db_session):
        estimate = add_estimate(db_session)
        receipt = create_receipt(client)
        allocation = create_allocation(client, receipt["id"], amount="700000.00", estimate_id=estimate.id)
        post_expense(client, allocation_id=allocation["id"], amount="450000.00")
        response = post_expense(client, allocation_id=allocation["id"], amount="300000.00")
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert "250000.00" in detail

    def test_expense_within_remaining_allocation_accepted(self, client, db_session):
        estimate = add_estimate(db_session)
        receipt = create_receipt(client)
        allocation = create_allocation(client, receipt["id"], amount="700000.00", estimate_id=estimate.id)
        post_expense(client, allocation_id=allocation["id"], amount="450000.00")
        response = post_expense(client, allocation_id=allocation["id"], amount="250000.00")
        assert response.status_code == 201, response.text

    def test_authorized_excess_requires_authorization(self, client, db_session):
        estimate = add_estimate(db_session)
        receipt = create_receipt(client)
        allocation = create_allocation(client, receipt["id"], amount="700000.00", estimate_id=estimate.id)
        response = post_expense(
            client,
            allocation_id=allocation["id"],
            amount="800000.00",
            authorized_by="Director General",
            authorization_reason="Urgent site works approved by board",
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["authorized_by"] == "Director General"
        detail = client.get(f"/api/v1/expenses/{body['id']}").json()
        assert detail["allocation_remaining_amount"] == "-100000.00"

    def test_authorized_excess_audited(self, client, db_session):
        estimate = add_estimate(db_session)
        receipt = create_receipt(client)
        allocation = create_allocation(client, receipt["id"], amount="700000.00", estimate_id=estimate.id)
        expense_id = post_expense(
            client,
            allocation_id=allocation["id"],
            amount="800000.00",
            authorized_by="Director General",
        ).json()["id"]
        actions = audit_actions(db_session, expense_id)
        assert "authorized_excess" in actions

    def test_reversed_expense_frees_allocation(self, client, db_session):
        estimate = add_estimate(db_session)
        receipt = create_receipt(client)
        allocation = create_allocation(client, receipt["id"], amount="700000.00", estimate_id=estimate.id)
        expense_id = post_expense(client, allocation_id=allocation["id"], amount="450000.00").json()["id"]
        assert client.post(f"/api/v1/expenses/{expense_id}/reverse", json={"reason": "incorrect entry"}).status_code == 200
        response = post_expense(client, allocation_id=allocation["id"], amount="650000.00")
        assert response.status_code == 201, response.text


class TestBudgetComparison:
    def test_under_estimate_variance(self, client, db_session):
        estimate = add_estimate(db_session, total=Decimal("2000000.00"))
        receipt = create_receipt(client)
        allocation = create_allocation(client, receipt["id"], amount="700000.00", estimate_id=estimate.id)
        post_expense(client, allocation_id=allocation["id"], amount="450000.00")

        summary = client.get("/api/v1/expenses/summary").json()
        assert summary["total_expenses"] == "450000.00"
        comparison = summary["budget_comparison"]
        assert len(comparison) == 1
        entry = comparison[0]
        assert entry["estimate_id"] == str(estimate.id)
        assert entry["estimated_amount"] == "2000000.00"
        assert entry["actual_expenditure"] == "450000.00"
        assert entry["variance_amount"] == "1550000.00"
        assert entry["status"] == "UNDER ESTIMATE"

    def test_over_estimate_status(self, client, db_session):
        estimate = add_estimate(db_session, total=Decimal("200000.00"))
        response = post_expense(client, estimate_id=str(estimate.id), amount="450000.00")
        assert response.status_code == 201, response.text
        comparison = client.get("/api/v1/expenses/summary").json()["budget_comparison"]
        assert len(comparison) == 1
        assert comparison[0]["status"] == "OVER ESTIMATE"
        assert comparison[0]["variance_amount"] == "-250000.00"

    def test_only_estimates_with_expenditure_compared(self, client, db_session):
        add_estimate(db_session, title="NO SPEND")
        spend = add_estimate(db_session, title="SPEND")
        post_expense(client, estimate_id=str(spend.id), amount="50000.00")
        comparison = client.get("/api/v1/expenses/summary").json()["budget_comparison"]
        assert len(comparison) == 1

    def test_expenses_by_category(self, client):
        post_expense(client, category="MATERIALS", amount="100000.00")
        post_expense(client, category="MATERIALS", amount="50000.00")
        post_expense(client, category="LABOUR", amount="75000.00")
        summary = client.get("/api/v1/expenses/summary").json()
        by_category = {item["category"]: item["total"] for item in summary["by_category"]}
        assert by_category == {"MATERIALS": "150000.00", "LABOUR": "75000.00"}


class TestAllocationBreakdown:
    def test_remaining_allocation_per_allocation(self, client, db_session):
        estimate = add_estimate(db_session)
        receipt = create_receipt(client)
        allocation = create_allocation(client, receipt["id"], amount="700000.00", estimate_id=estimate.id)
        post_expense(client, allocation_id=allocation["id"], amount="450000.00")

        summary = client.get("/api/v1/expenses/summary").json()
        breakdown = summary["allocation_breakdown"]
        assert len(breakdown) == 1
        item = breakdown[0]
        assert item["allocation_id"] == allocation["id"]
        assert item["allocated_amount"] == "700000.00"
        assert item["spent_amount"] == "450000.00"
        assert item["remaining_amount"] == "250000.00"

        listed = client.get("/api/v1/allocations").json()["allocations"]
        assert listed[0]["remaining_amount"] == "250000.00"


class TestEvidence:
    def test_attach_download_remove_evidence(self, client):
        expense_id = post_expense(client).json()["id"]
        files = {
            "file": (
                "invoice.pdf",
                io.BytesIO(b"%PDF-1.4 fake pdf content"),
                "application/pdf",
            )
        }
        response = client.post(f"/api/v1/expenses/{expense_id}/evidence", files=files)
        assert response.status_code == 200, response.text
        assert response.json()["evidence_original_filename"] == "invoice.pdf"

        download = client.get(f"/api/v1/expenses/{expense_id}/evidence")
        assert download.status_code == 200
        assert download.headers["content-type"] == "application/pdf"

        removed = client.delete(f"/api/v1/expenses/{expense_id}/evidence")
        assert removed.status_code == 200
        assert removed.json()["evidence_filename"] is None

    def test_download_without_evidence_404(self, client):
        expense_id = post_expense(client).json()["id"]
        assert client.get(f"/api/v1/expenses/{expense_id}/evidence").status_code == 404

    def test_bad_evidence_type_rejected(self, client):
        expense_id = post_expense(client).json()["id"]
        files = {"file": ("malware.exe", io.BytesIO(b"MZ"), "application/x-msdownload")}
        assert client.post(f"/api/v1/expenses/{expense_id}/evidence", files=files).status_code == 400


class TestRetrieval:
    def test_list_expenses(self, client):
        post_expense(client, amount="100000.00", description="First")
        post_expense(client, amount="250000.00", description="Second")
        response = client.get("/api/v1/expenses")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert {e["description"] for e in body["expenses"]} == {"First", "Second"}
        assert body["summary"]["total_expenses"] == "350000.00"

    def test_expense_detail_includes_links(self, client, db_session):
        estimate = add_estimate(db_session)
        item = add_line_item(db_session, estimate.id, description="Foundation concrete")
        expense_id = post_expense(
            client,
            estimate_id=str(estimate.id),
            estimate_line_item_id=str(item.id),
        ).json()["id"]
        detail = client.get(f"/api/v1/expenses/{expense_id}").json()
        assert detail["estimate_title"] == estimate.title
        assert detail["estimate_item_description"] == "Foundation concrete"
        assert detail["allocation_purpose"] is None
        assert detail["allocation_remaining_amount"] is None

    def test_missing_expense_404(self, client):
        import uuid
        assert client.get(f"/api/v1/expenses/{uuid.uuid4()}").status_code == 404


class TestCorrections:
    def test_patch_updates_non_financial_fields(self, client, db_session):
        expense_id = post_expense(client).json()["id"]
        response = client.patch(
            f"/api/v1/expenses/{expense_id}",
            json={"supplier": "Corrected Supplier", "category": "STRUCTURES"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["supplier"] == "Corrected Supplier"
        assert response.json()["category"] == "STRUCTURES"
        row = expense_from_db(db_session, expense_id)
        assert row.supplier == "Corrected Supplier"
        assert "updated" in audit_actions(db_session, expense_id)

    def test_patch_rejects_financial_fields(self, client):
        expense_id = post_expense(client).json()["id"]
        for field, value in {
            "amount": "1.00",
            "quantity": "2",
            "unit_price": "3",
            "expense_date": "2026-01-01",
            "allocation_id": "00000000-0000-0000-0000-000000000000",
            "estimate_id": "00000000-0000-0000-0000-000000000000",
            "estimate_line_item_id": "00000000-0000-0000-0000-000000000000",
            "currency": "XAF",
            "status": "reversed",
        }.items():
            response = client.patch(f"/api/v1/expenses/{expense_id}", json={field: value})
            assert response.status_code == 422, f"{field} should be rejected"

    def test_reverse_expense(self, client, db_session):
        expense_id = post_expense(client).json()["id"]
        response = client.post(
            f"/api/v1/expenses/{expense_id}/reverse",
            json={"reason": "Wrong amount charged"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "reversed"
        row = expense_from_db(db_session, expense_id)
        assert row.status == "reversed"
        assert "reversed" in audit_actions(db_session, expense_id)

    def test_reverse_excludes_from_totals(self, client, db_session):
        expense_id = post_expense(client, amount="450000.00").json()["id"]
        post_expense(client, amount="100000.00")
        assert client.get("/api/v1/expenses/summary").json()["total_expenses"] == "550000.00"
        assert client.post(f"/api/v1/expenses/{expense_id}/reverse", json={"reason": "correction"}).status_code == 200
        assert client.get("/api/v1/expenses/summary").json()["total_expenses"] == "100000.00"

    def test_reverse_twice_rejected(self, client):
        expense_id = post_expense(client).json()["id"]
        assert client.post(f"/api/v1/expenses/{expense_id}/reverse", json={}).status_code == 200
        assert client.post(f"/api/v1/expenses/{expense_id}/reverse", json={}).status_code == 409

    def test_patch_reversed_expense_rejected(self, client):
        expense_id = post_expense(client).json()["id"]
        assert client.post(f"/api/v1/expenses/{expense_id}/reverse", json={}).status_code == 200
        assert client.patch(f"/api/v1/expenses/{expense_id}", json={"supplier": "X"}).status_code == 409


class TestExpenseListAllocationsEndpoint:
    def test_list_allocations_with_spent_info(self, client, db_session):
        estimate = add_estimate(db_session)
        receipt = create_receipt(client)
        create_allocation(client, receipt["id"], estimate_id=estimate.id)
        response = client.get("/api/v1/allocations")
        assert response.status_code == 200
        allocations = response.json()["allocations"]
        assert len(allocations) == 1
        assert allocations[0]["allocated_amount"] > allocations[0]["spent_amount"]


class TestIntegrationChain:
    def test_estimate_funding_allocation_expense_remaining(self, client, db_session):
        # Estimate 2,000,000 -> Receipt 1,000,000 -> Allocation 700,000
        # -> Expense 450,000 -> Remaining allocation 250,000
        estimate = add_estimate(db_session, total=Decimal("2000000.00"))
        receipt = create_receipt(client, amount="1000000.00")
        allocation = create_allocation(client, receipt["id"], amount="700000.00", estimate_id=estimate.id)

        expense = post_expense(client, allocation_id=allocation["id"], amount="450000.00")
        assert expense.status_code == 201, expense.text

        # Expense detail shows the whole trace + remaining allocation
        detail = client.get(f"/api/v1/expenses/{expense.json()['id']}").json()
        assert detail["estimate_id"] == str(estimate.id)
        assert detail["allocation_id"] == allocation["id"]
        assert detail["allocation_spent_amount"] == "450000.00"
        assert detail["allocation_remaining_amount"] == "250000.00"

        # Funding layer is unchanged: receipt still shows 700,000 allocated
        funding = client.get(f"/api/v1/funds/{receipt['id']}").json()
        assert funding["allocated_amount"] == "700000.00"
        assert funding["unallocated_amount"] == "300000.00"

        # Expense summary reflects the correct remaining balance
        summary = client.get("/api/v1/expenses/summary").json()
        assert summary["total_expenses"] == "450000.00"
        assert summary["allocation_breakdown"][0]["remaining_amount"] == "250000.00"
        assert summary["budget_comparison"][0]["variance_amount"] == "1550000.00"

        # DB persistence
        row = expense_from_db(db_session, expense.json()["id"])
        assert row.amount == Decimal("450000.00")
        assert str(row.allocation_id) == allocation["id"]