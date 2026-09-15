from app.schemas.schemas import EstimateCreate
from app.repositories.estimate_repository import estimate_repo

ESTIMATES_URL = "/api/v1/estimates"


def _seed_estimate(db_session) -> str:
    data = EstimateCreate(
        title="Security Test Estimate",
        project_name="Test Project",
        currency="FCFA",
        line_items=[],
    )
    estimate = estimate_repo.create(db_session, data, "stored.pdf", "original.pdf")
    return str(estimate.id)


def test_member_can_edit_estimate_metadata(member_client, db_session):
    estimate_id = _seed_estimate(db_session)
    response = member_client.put(
        f"{ESTIMATES_URL}/{estimate_id}", json={"title": "Updated Title"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


def test_member_cannot_set_estimate_status(client, member_client, db_session):
    estimate_id = _seed_estimate(db_session)
    response = member_client.put(
        f"{ESTIMATES_URL}/{estimate_id}", json={"status": "confirmed"}
    )
    assert response.status_code == 422


def test_member_cannot_set_estimate_total(client, member_client, db_session):
    estimate_id = _seed_estimate(db_session)
    response = member_client.put(
        f"{ESTIMATES_URL}/{estimate_id}", json={"total_estimated_amount": 999999.99}
    )
    assert response.status_code == 422
    detail = client.get(f"{ESTIMATES_URL}/{estimate_id}")
    assert detail.json()["total_estimated_amount"] == 0


def test_member_cannot_send_unknown_fields(member_client, db_session):
    estimate_id = _seed_estimate(db_session)
    response = member_client.put(
        f"{ESTIMATES_URL}/{estimate_id}",
        json={"title": "x", "is_confirmed": True},
    )
    assert response.status_code == 422


def test_member_cannot_confirm_estimate(member_client, db_session):
    estimate_id = _seed_estimate(db_session)
    response = member_client.post(f"{ESTIMATES_URL}/{estimate_id}/confirm")
    assert response.status_code == 403