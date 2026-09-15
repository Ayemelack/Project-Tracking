import io
import uuid
from decimal import Decimal

from sqlalchemy import select

from app.models.models import Estimate, EstimateLineItem, Resource, ResourceMovement


def add_estimate(db_session, total=Decimal("2000000.00"), title="MOLA FAKO ESTIMATE"):
    estimate = Estimate(
        title=title,
        project_name="MOLA FAKO",
        original_filename="estimate.pdf",
        stored_filename="stored_estimate.pdf",
        status="confirmed",
        total_estimated_amount=total,
    )
    db_session.add(estimate)
    db_session.commit()
    db_session.refresh(estimate)
    return estimate


def add_line_item(db_session, estimate_id, description="Cement 42.5R"):
    item = EstimateLineItem(
        estimate_id=estimate_id,
        item_number="2.1.1",
        description=description,
        quantity=Decimal("174.00"),
        unit="bag",
        unit_cost=Decimal("7500.00"),
        total_cost=Decimal("1305000.00"),
        category="MATERIALS",
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def create_resource(client, **overrides):
    payload = {
        "name": "Cement",
        "project": "MOLA FAKO",
        "category": "MATERIALS",
        "unit": "bag",
        "currency": "FCFA",
        **overrides,
    }
    return client.post("/api/v1/resources", json=payload)


def post_expense(client, **overrides):
    payload = {
        "amount": "450000.00",
        "expense_date": "2026-09-15",
        "description": "Cement purchase",
        "category": "MATERIALS",
        "currency": "FCFA",
        **overrides,
    }
    return client.post("/api/v1/expenses", json=payload)


def create_purchase(client, resource_id, **overrides):
    payload = {
        "quantity": "100.00",
        "unit_cost": "7500.00",
        "movement_date": "2026-09-10",
        "supplier": "CAMACO",
        "reference": "PUR-001",
        **overrides,
    }
    return client.post(f"/api/v1/resources/{resource_id}/purchases", json=payload)


def create_delivery(client, resource_id, **overrides):
    payload = {
        "quantity": "90.00",
        "movement_date": "2026-09-11",
        "receiver": "Store Keeper",
        "reference": "DRN-001",
        **overrides,
    }
    return client.post(f"/api/v1/resources/{resource_id}/deliveries", json=payload)


def create_usage(client, resource_id, **overrides):
    payload = {
        "quantity": "80.00",
        "movement_date": "2026-09-12",
        "project_stage": "Foundation",
        "activity": "Concrete works",
        "responsible_person": "Site Manager",
        **overrides,
    }
    return client.post(f"/api/v1/resources/{resource_id}/usage", json=payload)


def create_adjustment(client, resource_id, **overrides):
    payload = {
        "quantity": "5.00",
        "movement_date": "2026-09-13",
        "notes": "Recount adjustment",
        **overrides,
    }
    return client.post(f"/api/v1/resources/{resource_id}/adjustments", json=payload)


def resource_detail(client, resource_id):
    response = client.get(f"/api/v1/resources/{resource_id}")
    assert response.status_code == 200, response.text
    return response.json()


def movement_from_db(db_session, movement_id):
    stmt = select(ResourceMovement).where(ResourceMovement.id == movement_id)
    return db_session.execute(stmt).scalar_one()


class TestResourceCreation:
    def test_create_resource(self, client):
        response = create_resource(client)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["name"] == "Cement"
        assert body["unit"] == "bag"
        assert body["currency"] == "FCFA"
        assert body["status"] == "active"
        assert body["purchased_quantity"] == "0.00"
        assert body["remaining_quantity"] == "0.00"

    def test_missing_name_rejected(self, client):
        assert create_resource(client, name=None).status_code == 422
        assert create_resource(client, name="   ").status_code == 422

    def test_negative_budget_rejected(self, client):
        response = create_resource(client, budgeted_quantity="-10.00")
        assert response.status_code == 422
        response = create_resource(client, budgeted_cost="-1000.00")
        assert response.status_code == 422

    def test_invalid_currency_rejected(self, client):
        assert create_resource(client, currency="USD").status_code == 422

    def test_resource_persisted_with_budget(self, client, db_session):
        response = create_resource(client, budgeted_quantity="174.00", budgeted_cost="1305000.00")
        assert response.status_code == 201, response.text
        row = db_session.execute(
            select(Resource).where(Resource.id == response.json()["id"])
        ).scalar_one()
        assert row.name == "Cement"
        assert row.budgeted_quantity == Decimal("174.00")
        assert row.budgeted_cost == Decimal("1305000.00")

    def test_estimate_link(self, client, db_session):
        estimate = add_estimate(db_session)
        item = add_line_item(db_session, estimate.id)
        response = create_resource(client, estimate_id=str(estimate.id), estimate_line_item_id=str(item.id))
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["estimate_id"] == str(estimate.id)
        assert body["estimate_title"] == estimate.title
        assert body["estimate_item_description"] == "Cement 42.5R"

    def test_line_item_mismatch_rejected(self, client, db_session):
        estimate_a = add_estimate(db_session, title="EST A")
        estimate_b = add_estimate(db_session, title="EST B")
        item = add_line_item(db_session, estimate_a.id)
        response = create_resource(
            client,
            estimate_id=str(estimate_b.id),
            estimate_line_item_id=str(item.id),
        )
        assert response.status_code == 422

    def test_unknown_estimate_rejected(self, client):
        response = create_resource(client, estimate_id=str(uuid.uuid4()))
        assert response.status_code == 404


class TestPurchases:
    def test_purchase_records_quantity_and_total(self, client, db_session):
        resource_id = create_resource(client).json()["id"]
        response = create_purchase(client, resource_id)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["movement_type"] == "purchase"
        assert body["quantity"] == "100.00"
        assert body["unit_cost"] == "7500.00"
        assert body["total_cost"] == "750000.00"

        row = movement_from_db(db_session, body["id"])
        assert row.total_cost == Decimal("750000.00")
        assert row.quantity == Decimal("100.00")

    def test_purchase_zero_or_negative_quantity_rejected(self, client):
        resource_id = create_resource(client).json()["id"]
        assert create_purchase(client, resource_id, quantity="0").status_code == 422
        assert create_purchase(client, resource_id, quantity="-5").status_code == 422
        assert create_purchase(
            client, resource_id, quantity="5"
        ).status_code == 201  # sanity: positive ok

    def test_purchase_missing_unit_cost_rejected(self, client):
        resource_id = create_resource(client).json()["id"]
        payload = {
            "quantity": "100.00",
            "movement_date": "2026-09-10",
        }
        response = client.post(f"/api/v1/resources/{resource_id}/purchases", json=payload)
        assert response.status_code == 422

    def test_expense_quantity_mismatch_rejected(self, client, db_session):
        resource_id = create_resource(client).json()["id"]
        expense = post_expense(client, quantity="100.00", unit="bag", unit_price="7500.00", amount="750000.00")
        assert expense.status_code == 201, expense.text
        response = create_purchase(client, resource_id, quantity="99.00", expense_id=expense.json()["id"])
        assert response.status_code == 422
        assert "quantity" in response.json()["detail"].lower()

    def test_expense_unit_price_mismatch_rejected(self, client, db_session):
        resource_id = create_resource(client).json()["id"]
        expense = post_expense(client, quantity="100.00", unit="bag", unit_price="7500.00", amount="750000.00")
        assert expense.status_code == 201, expense.text
        response = create_purchase(client, resource_id, quantity="100.00", unit_cost="8000.00", expense_id=expense.json()["id"])
        assert response.status_code == 422
        assert "unit price" in response.json()["detail"].lower()

    def test_expense_currency_mismatch_rejected(self, client, db_session):
        resource_id = create_resource(client).json()["id"]
        expense = post_expense(client, currency="XAF")
        assert expense.status_code == 201, expense.text
        response = create_purchase(client, resource_id, expense_id=expense.json()["id"])
        assert response.status_code == 422

    def test_unknown_expense_rejected(self, client):
        resource_id = create_resource(client).json()["id"]
        response = create_purchase(client, resource_id, expense_id=str(uuid.uuid4()))
        assert response.status_code == 404

    def test_reversed_expense_rejected(self, client):
        resource_id = create_resource(client).json()["id"]
        expense_id = post_expense(client).json()["id"]
        assert client.post(f"/api/v1/expenses/{expense_id}/reverse", json={}).status_code == 200
        response = create_purchase(client, resource_id, expense_id=expense_id)
        assert response.status_code == 409

    def test_purchase_linked_to_expense_appears_in_detail(self, client):
        resource_id = create_resource(client).json()["id"]
        expense = post_expense(client, quantity="100.00", unit="bag", unit_price="7500.00", amount="750000.00")
        expense_id = expense.json()["id"]
        create_purchase(client, resource_id, expense_id=expense_id)
        detail = resource_detail(client, resource_id)
        assert detail["total_purchase_cost"] == "750000.00"
        assert [e["id"] for e in detail["related_expenses"]] == [expense_id]

    def test_recorded_purchase_drives_purchased_quantity(self, client):
        resource_id = create_resource(client).json()["id"]
        create_purchase(client, resource_id, quantity="160.00", unit_cost="7500.00")
        detail = resource_detail(client, resource_id)
        assert detail["purchased_quantity"] == "160.00"
        assert detail["pending_delivery_quantity"] == "160.00"


class TestDeliveries:
    def test_delivery_after_purchase(self, client):
        resource_id = create_resource(client).json()["id"]
        create_purchase(client, resource_id, quantity="100.00")
        response = create_delivery(client, resource_id, quantity="60.00")
        assert response.status_code == 201, response.text
        detail = resource_detail(client, resource_id)
        assert detail["delivered_quantity"] == "60.00"
        assert detail["remaining_quantity"] == "60.00"
        assert detail["pending_delivery_quantity"] == "40.00"

    def test_delivery_exceeding_purchased_rejected(self, client):
        resource_id = create_resource(client).json()["id"]
        create_purchase(client, resource_id, quantity="100.00")
        response = create_delivery(client, resource_id, quantity="150.00")
        assert response.status_code == 409
        assert "exceeds the purchased quantity" in response.json()["detail"]

    def test_delivery_without_any_purchase_rejected(self, client):
        resource_id = create_resource(client).json()["id"]
        response = create_delivery(client, resource_id, quantity="10.00")
        assert response.status_code == 409

    def test_delivery_linked_to_non_purchase_rejected(self, client):
        resource_id = create_resource(client).json()["id"]
        create_purchase(client, resource_id, quantity="100.00")
        adjustment = create_adjustment(client, resource_id, quantity="5.00", notes="Found surplus")
        response = create_delivery(
            client, resource_id, quantity="5.00", linked_purchase_movement_id=adjustment.json()["id"]
        )
        assert response.status_code == 422

    def test_delivery_linked_to_purchase_of_other_resource_rejected(self, client):
        resource_a = create_resource(client, name="Cement").json()["id"]
        resource_b = create_resource(client, name="Sand").json()["id"]
        purchase_a = create_purchase(client, resource_a, quantity="100.00").json()["id"]
        response = create_delivery(
            client, resource_b, quantity="5.00", linked_purchase_movement_id=purchase_a
        )
        assert response.status_code == 422

    def test_delivery_records_receiver(self, client):
        resource_id = create_resource(client).json()["id"]
        create_purchase(client, resource_id, quantity="100.00")
        response = create_delivery(client, resource_id, quantity="10.00", receiver="Night Watchman")
        assert response.status_code == 201, response.text
        assert response.json()["receiver"] == "Night Watchman"


class TestUsageAndRemaining:
    def test_usage_within_available(self, client):
        resource_id = create_resource(client).json()["id"]
        create_purchase(client, resource_id, quantity="100.00")
        create_delivery(client, resource_id, quantity="100.00")
        response = create_usage(client, resource_id, quantity="30.00")
        assert response.status_code == 201, response.text
        detail = resource_detail(client, resource_id)
        assert detail["used_quantity"] == "30.00"
        assert detail["remaining_quantity"] == "70.00"

    def test_usage_exceeding_available_rejected(self, client):
        resource_id = create_resource(client).json()["id"]
        create_purchase(client, resource_id, quantity="100.00")
        create_delivery(client, resource_id, quantity="100.00")
        response = create_usage(client, resource_id, quantity="101.00")
        assert response.status_code == 409
        assert "exceeds the available quantity" in response.json()["detail"]

    def test_usage_before_any_delivery_rejected(self, client):
        resource_id = create_resource(client).json()["id"]
        create_purchase(client, resource_id, quantity="100.00")
        response = create_usage(client, resource_id, quantity="10.00")
        assert response.status_code == 409

    def test_remaining_never_goes_negative(self, client):
        resource_id = create_resource(client).json()["id"]
        create_purchase(client, resource_id, quantity="100.00")
        create_delivery(client, resource_id, quantity="100.00")
        create_usage(client, resource_id, quantity="100.00")
        detail = resource_detail(client, resource_id)
        assert detail["remaining_quantity"] == "0.00"
        assert create_usage(client, resource_id, quantity="1.00").status_code == 409


class TestAdjustments:
    def test_positive_adjustment_increases_available(self, client):
        resource_id = create_resource(client).json()["id"]
        response = create_adjustment(client, resource_id, quantity="10.00", notes="Found surplus bags on site")
        assert response.status_code == 201, response.text
        detail = resource_detail(client, resource_id)
        assert detail["adjustment_quantity"] == "10.00"
        assert detail["remaining_quantity"] == "10.00"

    def test_adjustment_requires_reason(self, client):
        resource_id = create_resource(client).json()["id"]
        response = create_adjustment(client, resource_id, quantity="10.00", notes=None)
        assert response.status_code == 422
        assert "reason" in response.json()["detail"].lower()

    def test_zero_adjustment_rejected(self, client):
        resource_id = create_resource(client).json()["id"]
        response = create_adjustment(client, resource_id, quantity="0.00", notes="Nothing")
        assert response.status_code == 422

    def test_negative_adjustment_requires_authorization(self, client):
        resource_id = create_resource(client).json()["id"]
        create_adjustment(client, resource_id, quantity="10.00", notes="Found surplus")
        response = create_adjustment(
            client, resource_id, quantity="-5.00", notes="Damage during storage"
        )
        assert response.status_code == 422
        assert "authorized_by" in response.json()["detail"].lower()

    def test_negative_adjustment_with_authorization(self, client):
        resource_id = create_resource(client).json()["id"]
        create_adjustment(client, resource_id, quantity="10.00", notes="Found surplus")
        response = create_adjustment(
            client,
            resource_id,
            quantity="-4.00",
            notes="Cracked bags written off",
            authorized_by="Site Manager",
            authorization_reason="Bags damaged during handling",
        )
        assert response.status_code == 201, response.text
        detail = resource_detail(client, resource_id)
        assert detail["remaining_quantity"] == "6.00"

    def test_negative_adjustment_below_zero_rejected(self, client):
        resource_id = create_resource(client).json()["id"]
        create_adjustment(client, resource_id, quantity="5.00", notes="Found surplus")
        response = create_adjustment(
            client,
            resource_id,
            quantity="-6.00",
            notes="Overstated surplus",
            authorized_by="Site Manager",
            authorization_reason="Recount showed fewer bags",
        )
        assert response.status_code == 409


class TestFinancialCalculations:
    def test_cost_variance(self, client):
        resource_id = create_resource(client, budgeted_cost="1305000.00").json()["id"]
        create_purchase(client, resource_id, quantity="160.00", unit_cost="7500.00")
        detail = resource_detail(client, resource_id)
        assert detail["total_purchase_cost"] == "1200000.00"
        assert detail["cost_variance"] == "105000.00"

    def test_money_uses_decimal_strings(self, client, db_session):
        resource_id = create_resource(client).json()["id"]
        purchase = create_purchase(client, resource_id, quantity="2.50", unit_cost="3000.00")
        assert purchase.status_code == 201, purchase.text
        row = movement_from_db(db_session, purchase.json()["id"])
        assert row.total_cost == Decimal("7500.00")
        assert isinstance(row.total_cost, Decimal)


class TestMovementHistory:
    def test_chronological_ledger(self, client):
        resource_id = create_resource(client).json()["id"]
        create_purchase(client, resource_id, quantity="100.00", movement_date="2026-09-10")
        create_delivery(client, resource_id, quantity="50.00", movement_date="2026-09-11")
        # Later movement with an earlier date sorts before later-dated ones only.
        detail = resource_detail(client, resource_id)
        dates = [m["movement_date"] for m in detail["movements"]]
        assert dates == ["2026-09-10", "2026-09-11"]
        types = [m["movement_type"] for m in detail["movements"]]
        assert types == ["purchase", "delivery"]

    def test_movement_history_preserved(self, client, db_session):
        resource_id = create_resource(client).json()["id"]
        purchase = create_purchase(client, resource_id, quantity="100.00")
        usage = create_usage(client, resource_id, quantity="1.00")
        assert usage.status_code == 409  # no delivery yet, must be rejected
        purchase_id = purchase.json()["id"]
        row = movement_from_db(db_session, purchase_id)
        assert row.movement_type == "purchase"


class TestEvidence:
    def test_attach_download_remove_evidence(self, client):
        resource_id = create_resource(client).json()["id"]
        create_purchase(client, resource_id, quantity="100.00")
        delivery = create_delivery(client, resource_id, quantity="10.00")
        movement_id = delivery.json()["id"]

        files = {"file": ("delivery_note.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")}
        attached = client.post(
            f"/api/v1/resources/{resource_id}/movements/{movement_id}/evidence", files=files
        )
        assert attached.status_code == 200, attached.text
        assert attached.json()["evidence_original_filename"] == "delivery_note.pdf"

        download = client.get(f"/api/v1/resources/{resource_id}/movements/{movement_id}/evidence")
        assert download.status_code == 200

        removed = client.delete(f"/api/v1/resources/{resource_id}/movements/{movement_id}/evidence")
        assert removed.status_code == 200
        assert removed.json()["evidence_filename"] is None

    def test_evidence_for_unknown_movement_404(self, client):
        resource_id = create_resource(client).json()["id"]
        files = {"file": ("note.pdf", io.BytesIO(b"PDF"), "application/pdf")}
        response = client.post(
            f"/api/v1/resources/{resource_id}/movements/{uuid.uuid4()}/evidence", files=files
        )
        assert response.status_code == 404

    def test_bad_evidence_type_rejected(self, client):
        resource_id = create_resource(client).json()["id"]
        create_purchase(client, resource_id, quantity="100.00")
        delivery = create_delivery(client, resource_id, quantity="10.00")
        files = {"file": ("malware.exe", io.BytesIO(b"MZ"), "application/x-msdownload")}
        response = client.post(
            f"/api/v1/resources/{resource_id}/movements/{delivery.json()['id']}/evidence",
            files=files,
        )
        assert response.status_code == 400


class TestListEndpoint:
    def test_list_resources_with_computed_totals(self, client):
        resource_id = create_resource(client, name="Cement").json()["id"]
        sand_id = create_resource(client, name="Sand", category="AGGREGATES").json()["id"]
        create_purchase(client, resource_id, quantity="100.00", unit_cost="7500.00")
        create_delivery(client, resource_id, quantity="40.00")

        response = client.get("/api/v1/resources")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        by_name = {r["name"]: r for r in body["resources"]}
        assert by_name["Cement"]["purchased_quantity"] == "100.00"
        assert by_name["Cement"]["delivered_quantity"] == "40.00"
        assert by_name["Cement"]["remaining_quantity"] == "40.00"
        assert by_name["Sand"]["purchased_quantity"] == "0.00"


class TestIntegrationChain:
    def test_estimate_purchase_delivery_usage_remaining(self, client, db_session):
        # Critical chain: Estimate -> Purchase -> Delivery -> Usage -> Remaining
        estimate = add_estimate(db_session)
        item = add_line_item(db_session, estimate.id)

        # Resource linked to the Phase 1 estimate line item (174 bags budgeted).
        resource = create_resource(
            client,
            estimate_id=str(estimate.id),
            estimate_line_item_id=str(item.id),
            budgeted_quantity="174.00",
            budgeted_cost="1305000.00",
        )
        assert resource.status_code == 201, resource.text
        resource_id = resource.json()["id"]

        # Purchase 160 bags @ 7,500 = 1,200,000, linked to a Phase 3 expense.
        expense = post_expense(
            client,
            description="Cement purchase for foundation works",
            quantity="160.00",
            unit="bag",
            unit_price="7500.00",
            amount="1200000.00",
        )
        assert expense.status_code == 201, expense.text
        purchase = create_purchase(
            client, resource_id, quantity="160.00", unit_cost="7500.00", expense_id=expense.json()["id"]
        )
        assert purchase.status_code == 201, purchase.text

        # Delivery 150 bags.
        delivery = create_delivery(client, resource_id, quantity="150.00", receiver="Store Keeper")
        assert delivery.status_code == 201, delivery.text

        # Usage 120 bags.
        usage = create_usage(
            client, resource_id, quantity="120.00", project_stage="Foundation", activity="Concrete works"
        )
        assert usage.status_code == 201, usage.text

        # Detail shows the full audit picture.
        detail = resource_detail(client, resource_id)
        assert detail["estimate_title"] == estimate.title
        assert detail["estimate_item_description"] == "Cement 42.5R"
        assert detail["budgeted_quantity"] == "174.00"
        assert detail["purchased_quantity"] == "160.00"
        assert detail["delivered_quantity"] == "150.00"
        assert detail["used_quantity"] == "120.00"
        assert detail["remaining_quantity"] == "30.00"
        assert detail["pending_delivery_quantity"] == "10.00"
        assert detail["total_purchase_cost"] == "1200000.00"
        assert detail["cost_variance"] == "105000.00"
        assert [e["id"] for e in detail["related_expenses"]] == [expense.json()["id"]]

        # Chronological ledger.
        assert [m["movement_type"] for m in detail["movements"]] == [
            "purchase",
            "delivery",
            "usage",
        ]

        # DB persistence of the audit chain.
        movements = db_session.execute(
            select(ResourceMovement)
            .where(ResourceMovement.resource_id == resource_id)
            .order_by(ResourceMovement.movement_date)
        ).scalars().all()
        assert len(movements) == 3
        assert movements[0].movement_type == "purchase"
        assert movements[1].movement_type == "delivery"
        assert movements[2].movement_type == "usage"

        # Impossible value still rejected after the chain: deliver more than purchased.
        assert create_delivery(client, resource_id, quantity="20.00").status_code == 409