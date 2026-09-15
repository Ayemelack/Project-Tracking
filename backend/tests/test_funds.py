import io
import uuid
from decimal import Decimal

import pytest

from app.models.models import Estimate
from app.services.storage_service import StorageService


def create_receipt(client, amount=1000000, source="Ministry of Works", **overrides):
    payload = {
        "amount": amount,
        "currency": "FCFA",
        "received_date": "2026-09-09",
        "source": source,
        "reference": "TRF-001",
        "purpose": "General construction",
        **overrides,
    }
    return client.post("/api/v1/funds", json=payload)


def create_allocation(client, fund_id, amount=400000, purpose="Foundation works", **overrides):
    payload = {
        "amount": amount,
        "purpose": purpose,
        "category": "FOUNDATION",
        "responsible_person": "John Doe",
        "allocation_date": "2026-09-10",
        **overrides,
    }
    return client.post(f"/api/v1/funds/{fund_id}/allocations", json=payload)


@pytest.fixture()
def receipt(client):
    response = create_receipt(client)
    assert response.status_code == 201, response.text
    return response.json()


class TestFundReceiptCreation:
    def test_create_fund_receipt(self, client):
        response = create_receipt(client, amount=2500000, source="Project Grant")
        assert response.status_code == 201
        body = response.json()
        assert body["amount"] == "2500000.00"
        assert body["currency"] == "FCFA"
        assert body["source"] == "Project Grant"
        assert body["status"] == "recorded"
        assert body["id"]
        assert body["estimate_id"] is None

    def test_create_receipt_with_zero_amount_rejected(self, client):
        response = create_receipt(client, amount=0)
        assert response.status_code == 422

    def test_create_receipt_with_negative_amount_rejected(self, client):
        response = create_receipt(client, amount=-500000)
        assert response.status_code == 422

    def test_create_receipt_missing_source_rejected(self, client):
        response = create_receipt(client, source="")
        assert response.status_code == 422

    def test_create_receipt_with_unknown_estimate_rejected(self, client):
        response = create_receipt(client, estimate_id=str(uuid.uuid4()))
        assert response.status_code == 404


class TestAllocations:
    def test_create_allocation(self, client, receipt):
        response = create_allocation(client, receipt["id"], amount=400000)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["amount"] == "400000.00"
        assert body["fund_receipt_id"] == receipt["id"]
        assert body["status"] == "allocated"
        assert body["category"] == "FOUNDATION"

    def test_over_allocation_rejected(self, client, receipt):
        response = create_allocation(client, receipt["id"], amount=2000000)
        assert response.status_code == 409

    def test_allocated_and_unallocated_tracking(self, client, receipt):
        create_allocation(client, receipt["id"], amount=700000)
        detail = client.get(f"/api/v1/funds/{receipt['id']}").json()
        assert detail["allocated_amount"] == "700000.00"
        assert detail["unallocated_amount"] == "300000.00"

    def test_multiple_allocations_cannot_exceed_available(self, client, receipt):
        create_allocation(client, receipt["id"], amount=600000)
        response = create_allocation(client, receipt["id"], amount=500000)
        assert response.status_code == 409

    def test_allocation_with_unknown_estimate_rejected(self, client, receipt):
        response = create_allocation(client, receipt["id"], amount=100000, estimate_id=str(uuid.uuid4()))
        assert response.status_code == 404

    def test_allocation_total_matches_summary(self, client, receipt):
        create_allocation(client, receipt["id"], amount=300000)
        create_allocation(client, receipt["id"], amount=200000)
        summary = client.get("/api/v1/funds/summary").json()
        assert summary["total_allocated"] == "500000.00"
        assert summary["total_received"] == "1000000.00"
        assert summary["total_unallocated"] == "500000.00"

    def test_cancel_allocation_frees_funds(self, client, receipt):
        allocation = create_allocation(client, receipt["id"], amount=700000).json()
        response = client.post(f"/api/v1/allocations/{allocation['id']}/cancel", json={"reason": "Repriced"})
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

        detail = client.get(f"/api/v1/funds/{receipt['id']}").json()
        assert detail["unallocated_amount"] == "1000000.00"

        reallocate = create_allocation(client, receipt["id"], amount=800000)
        assert reallocate.status_code == 201

    def test_cancel_allocation_twice_rejected(self, client, receipt):
        allocation = create_allocation(client, receipt["id"]).json()
        client.post(f"/api/v1/allocations/{allocation['id']}/cancel", json={"reason": "x"})
        response = client.post(f"/api/v1/allocations/{allocation['id']}/cancel", json={"reason": "x"})
        assert response.status_code == 409


class TestEvidence:
    def test_receipt_evidence_roundtrip(self, client, monkeypatch, tmp_path, receipt):
        monkeypatch.setattr("app.services.fund_service.storage_service", StorageService(str(tmp_path)))
        upload = {"file": ("supporting.pdf", io.BytesIO(b"%PDF-1.4 test content"), "application/pdf")}
        response = client.post(f"/api/v1/funds/{receipt['id']}/evidence", files=upload)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["evidence_original_filename"] == "supporting.pdf"
        assert body["evidence_mime_type"] == "application/pdf"

        download = client.get(f"/api/v1/funds/{receipt['id']}/evidence")
        assert download.status_code == 200
        assert download.content == b"%PDF-1.4 test content"

        removed = client.delete(f"/api/v1/funds/{receipt['id']}/evidence")
        assert removed.status_code == 200
        assert removed.json()["evidence_filename"] is None

    def test_receipt_evidence_bad_extension_rejected(self, client, receipt):
        upload = {"file": ("virus.exe", io.BytesIO(b"MZ"), "application/octet-stream")}
        response = client.post(f"/api/v1/funds/{receipt['id']}/evidence", files=upload)
        assert response.status_code == 400

    def test_allocation_evidence_roundtrip(self, client, monkeypatch, tmp_path, receipt):
        monkeypatch.setattr("app.services.fund_service.storage_service", StorageService(str(tmp_path)))
        allocation = create_allocation(client, receipt["id"]).json()
        upload = {"file": ("invoice.jpg", io.BytesIO(b"\xff\xd8\xff\xe0 image"), "image/jpeg")}
        response = client.post(f"/api/v1/allocations/{allocation['id']}/evidence", files=upload)
        assert response.status_code == 200, response.text
        assert response.json()["evidence_mime_type"] == "image/jpeg"

        download = client.get(f"/api/v1/allocations/{allocation['id']}/evidence")
        assert download.status_code == 200


class TestFundingSummary:
    def test_summary_empty(self, client):
        summary = client.get("/api/v1/funds/summary").json()
        assert summary["approved_estimated_amount"] == "0.00"
        assert summary["total_received"] == "0.00"
        assert summary["total_allocated"] == "0.00"
        assert summary["funding_coverage_percentage"] is None

    def test_summary_with_confirmed_estimate(self, client, db_session):
        db_session.add(
            Estimate(
                title="Test Estimate",
                project_name="Test Project",
                reference_number="REF-1",
                contractor="ABC",
                client="XYZ",
                currency="FCFA",
                original_filename="test.pdf",
                stored_filename="test-stored.pdf",
                status="confirmed",
                total_estimated_amount=Decimal("50000000.00"),
            )
        )
        db_session.commit()

        create_receipt(client, amount=2_500_000)
        summary = client.get("/api/v1/funds/summary").json()
        assert summary["approved_estimated_amount"] == "50000000.00"
        assert summary["total_received"] == "2500000.00"
        assert round(summary["funding_coverage_percentage"], 2) == 5.0

    def test_summary_ignores_non_confirmed_estimates(self, client, db_session):
        db_session.add(
            Estimate(
                title="Draft Estimate",
                status="draft",
                currency="FCFA",
                original_filename="draft.pdf",
                stored_filename="draft-stored.pdf",
                total_estimated_amount=Decimal("99999999.00"),
            )
        )
        db_session.commit()
        summary = client.get("/api/v1/funds/summary").json()
        assert summary["approved_estimated_amount"] == "0.00"


class TestLinkToEstimate:
    def test_estimate_title_resolved_in_allocation(self, client, db_session, receipt):
        estimate = Estimate(
            title="MOLA FAKO GENERAL ESTIMATE",
            status="confirmed",
            currency="FCFA",
            original_filename="mola.pdf",
            stored_filename="mola-stored.pdf",
        )
        db_session.add(estimate)
        db_session.commit()

        response = create_allocation(
            client,
            receipt["id"],
            amount=500000,
            estimate_id=str(estimate.id),
        )
        assert response.status_code == 201, response.text
        assert response.json()["estimate_title"] == "MOLA FAKO GENERAL ESTIMATE"


class TestPersistence:
    def test_receipt_persists(self, client, receipt):
        response = client.get(f"/api/v1/funds/{receipt['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == receipt["id"]

    def test_list_funds(self, client):
        create_receipt(client)
        response = client.get("/api/v1/funds")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] >= 1
        assert body["receipts"]

    def test_missing_receipt_returns_404(self, client):
        response = client.get(f"/api/v1/funds/{uuid.uuid4()}")
        assert response.status_code == 404