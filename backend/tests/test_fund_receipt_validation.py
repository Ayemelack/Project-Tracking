import uuid
from decimal import Decimal

from sqlalchemy import select

from app.models.models import FundReceipt


def base_payload(**overrides):
    payload = {
        "amount": "5000000.00",
        "currency": "FCFA",
        "received_date": "2026-09-09",
        "source": "Ministry of Works",
        "reference": "TRF-001",
        "purpose": "General construction",
        "notes": "",
        **overrides,
    }
    return payload


def create_receipt(client, **overrides):
    return client.post("/api/v1/funds", json=base_payload(**overrides))


def receipt_from_db(db_session, receipt_id):
    stmt = select(FundReceipt).where(FundReceipt.id == receipt_id)
    return db_session.execute(stmt).scalar_one()


class TestValidReceiptPersistence:
    def test_valid_receipt_string_amount_persisted(self, client, db_session):
        response = create_receipt(client, amount="5200000.50", reference="", notes="")
        assert response.status_code == 201, response.text
        body = response.json()
        row = receipt_from_db(db_session, body["id"])
        assert row.amount == Decimal("5200000.50")
        assert row.currency == "FCFA"
        assert row.source == "Ministry of Works"
        assert row.purpose == "General construction"
        assert row.reference is None
        assert row.notes is None
        assert row.status == "recorded"

    def test_valid_receipt_numeric_amount_still_accepted(self, client, db_session):
        response = create_receipt(client, amount=5000000)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["amount"] == "5000000.00"
        assert receipt_from_db(db_session, body["id"]).amount == Decimal("5000000.00")

    def test_minimum_positive_amount_accepted(self, client):
        response = create_receipt(client, amount="0.01")
        assert response.status_code == 201, response.text

    def test_largest_supported_amount_accepted(self, client):
        response = create_receipt(client, amount="9999999999999.99")
        assert response.status_code == 201, response.text

    def test_whitespace_around_required_text_is_stripped(self, client, db_session):
        response = create_receipt(
            client, source="  Ministry of Works  ", purpose="   Paving   ", currency=" fcfa "
        )
        assert response.status_code == 201, response.text
        body = response.json()
        row = receipt_from_db(db_session, body["id"])
        assert row.source == "Ministry of Works"
        assert row.purpose == "Paving"
        assert row.currency == "FCFA"

    def test_xaf_currency_accepted(self, client, db_session):
        response = create_receipt(client, currency="XAF")
        assert response.status_code == 201, response.text
        body = response.json()
        assert receipt_from_db(db_session, body["id"]).currency == "XAF"


class TestAmountValidation:
    def test_missing_amount_rejected(self, client):
        payload = base_payload()
        del payload["amount"]
        assert client.post("/api/v1/funds", json=payload).status_code == 422

    def test_zero_amount_rejected(self, client):
        assert create_receipt(client, amount="0").status_code == 422

    def test_negative_amount_rejected(self, client):
        assert create_receipt(client, amount="-100").status_code == 422

    def test_non_numeric_amount_rejected(self, client):
        assert create_receipt(client, amount="12abc").status_code == 422

    def test_amount_with_thousands_separator_rejected(self, client):
        assert create_receipt(client, amount="5,000,000").status_code == 422

    def test_amount_with_three_decimals_rejected(self, client):
        assert create_receipt(client, amount="1.999").status_code == 422

    def test_amount_exceeding_column_capacity_rejected(self, client):
        assert create_receipt(client, amount="10000000000000").status_code == 422

    def test_absurdly_large_amount_rejected(self, client):
        assert create_receipt(client, amount="1000000000000000000000000000").status_code == 422


class TestReceivedDateValidation:
    def test_missing_received_date_rejected(self, client):
        payload = base_payload()
        del payload["received_date"]
        assert client.post("/api/v1/funds", json=payload).status_code == 422

    def test_non_date_string_rejected(self, client):
        assert create_receipt(client, received_date="not-a-date").status_code == 422

    def test_out_of_range_month_rejected(self, client):
        assert create_receipt(client, received_date="2026-13-40").status_code == 422

    def test_impossible_calendar_date_rejected(self, client):
        assert create_receipt(client, received_date="2026-02-30").status_code == 422

    def test_valid_date_accepted(self, client):
        assert create_receipt(client, received_date="2026-09-09").status_code == 201


class TestCurrencyValidation:
    def test_arbitrary_currency_rejected(self, client):
        assert create_receipt(client, currency="USD").status_code == 422

    def test_another_arbitrary_currency_rejected(self, client):
        assert create_receipt(client, currency="GBP abc").status_code == 422

    def test_empty_currency_rejected(self, client):
        assert create_receipt(client, currency="").status_code == 422

    def test_whitespace_currency_rejected(self, client):
        assert create_receipt(client, currency="   ").status_code == 422


class TestRequiredTextFields:
    def test_missing_source_rejected(self, client):
        payload = base_payload()
        del payload["source"]
        assert client.post("/api/v1/funds", json=payload).status_code == 422

    def test_empty_source_rejected(self, client):
        assert create_receipt(client, source="").status_code == 422

    def test_whitespace_only_source_rejected(self, client):
        assert create_receipt(client, source="   ").status_code == 422

    def test_source_at_max_length_accepted(self, client):
        assert create_receipt(client, source="x" * 500).status_code == 201

    def test_source_over_max_length_rejected(self, client):
        assert create_receipt(client, source="x" * 501).status_code == 422

    def test_missing_purpose_rejected(self, client):
        payload = base_payload()
        del payload["purpose"]
        assert client.post("/api/v1/funds", json=payload).status_code == 422

    def test_empty_purpose_rejected(self, client):
        assert create_receipt(client, purpose="").status_code == 422

    def test_whitespace_only_purpose_rejected(self, client):
        assert create_receipt(client, purpose="   ").status_code == 422

    def test_purpose_at_max_length_accepted(self, client):
        assert create_receipt(client, purpose="y" * 1000).status_code == 201

    def test_purpose_over_max_length_rejected(self, client):
        assert create_receipt(client, purpose="y" * 1001).status_code == 422

    def test_reference_over_max_length_rejected(self, client):
        assert create_receipt(client, reference="r" * 201).status_code == 422

    def test_reference_at_max_length_accepted(self, client):
        assert create_receipt(client, reference="r" * 200).status_code == 201

    def test_reference_whitespace_stored_as_null(self, client, db_session):
        response = create_receipt(client, reference="   ")
        assert response.status_code == 201, response.text
        body = response.json()
        assert receipt_from_db(db_session, body["id"]).reference is None

    def test_notes_over_max_length_rejected(self, client):
        assert create_receipt(client, notes="n" * 2001).status_code == 422

    def test_notes_at_max_length_accepted(self, client):
        assert create_receipt(client, notes="n" * 2000).status_code == 201


class TestMaliciousInput:
    SQLI_TEXT = "Robert'); DROP TABLE fund_receipts;--"

    def test_sql_injection_in_text_fields_is_stored_safely(self, client, db_session):
        response = create_receipt(
            client,
            source=self.SQLI_TEXT,
            purpose="1; DROP TABLE estimates;--",
            reference="'; SELECT * FROM fund_receipts;--",
            notes="<script>alert(1)</script> & ' OR '1'='1",
        )
        assert response.status_code == 201, response.text
        body = response.json()
        row = receipt_from_db(db_session, body["id"])
        assert row.source == self.SQLI_TEXT
        assert row.purpose == "1; DROP TABLE estimates;--"
        assert row.reference == "'; SELECT * FROM fund_receipts;--"
        assert row.notes == "<script>alert(1)</script> & ' OR '1'='1"

    def test_system_still_fully_operational_after_malicious_insert(self, client):
        create_receipt(client, source=self.SQLI_TEXT)
        assert create_receipt(client).status_code == 201

    def test_sql_injection_in_amount_rejected(self, client):
        assert create_receipt(client, amount="5000000 OR 1=1").status_code == 422

    def test_sql_injection_string_as_amount_rejected(self, client):
        assert (
            create_receipt(client, amount="1; DROP TABLE fund_receipts;--").status_code
            == 422
        )

    def test_sql_injection_in_received_date_rejected(self, client):
        assert (
            create_receipt(
                client, received_date="2026-09-09; DROP TABLE fund_receipts;--"
            ).status_code
            == 422
        )

    def test_sql_injection_in_currency_rejected(self, client):
        assert create_receipt(client, currency="FCFA; DROP TABLE fund_receipts").status_code == 422

    def test_unicode_and_special_characters_stored_safely(self, client, db_session):
        response = create_receipt(
            client,
            source="Fonds spécial d'équipement",
            purpose="École – bâtiments & salles 😀",
            notes="Note avec « guillemets », accents et symboles ✓",
        )
        assert response.status_code == 201, response.text
        body = response.json()
        row = receipt_from_db(db_session, body["id"])
        assert row.source == "Fonds spécial d'équipement"
        assert row.purpose == "École – bâtiments & salles 😀"


class TestProtectedFields:
    def test_client_cannot_set_status(self, client, db_session):
        response = create_receipt(client, status="funded", updated_at="2099-01-01T00:00:00")
        assert response.status_code == 201, response.text
        body = response.json()
        row = receipt_from_db(db_session, body["id"])
        assert row.status == "recorded"
        assert body["status"] == "recorded"

    def test_client_cannot_set_id(self, client):
        spoofed = str(uuid.uuid4())
        response = create_receipt(client, id=spoofed)
        assert response.status_code == 201, response.text
        assert response.json()["id"] != spoofed


class TestDuplicateSubmission:
    def test_multiple_identical_submissions_are_consistent(self, client, db_session):
        first = create_receipt(client, reference="TRF-DUP")
        second = create_receipt(client, reference="TRF-DUP")
        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["id"] != second.json()["id"]
        count = len(
            db_session.execute(
                select(FundReceipt).where(FundReceipt.reference == "TRF-DUP")
            ).scalars().all()
        )
        assert count == 2