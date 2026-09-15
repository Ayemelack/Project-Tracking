import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.models.models import Activity, Estimate, Milestone


TODAY = datetime.now(timezone.utc).date()


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


def create_activity(client, **overrides):
    payload = {
        "name": "Foundations",
        "project": "MOLA FAKO",
        "project_stage": "Foundation",
        "planned_start_date": str(TODAY + timedelta(days=1)),
        "planned_end_date": str(TODAY + timedelta(days=10)),
        "status": "not_started",
        "progress_percentage": 0,
        "responsible_person": "Site Manager",
        **overrides,
    }
    return client.post("/api/v1/schedule", json=payload)


def create_milestone(client, **overrides):
    payload = {
        "name": "Foundation completed",
        "project": "MOLA FAKO",
        "planned_date": str(TODAY + timedelta(days=30)),
        "status": "pending",
        **overrides,
    }
    return client.post("/api/v1/schedule/milestones", json=payload)


class TestActivityCreation:
    def test_create_activity(self, client):
        response = create_activity(client)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["name"] == "Foundations"
        assert body["status"] == "not_started"
        assert body["progress_percentage"] == 0
        assert body["project_stage"] == "Foundation"
        assert body["is_delayed"] is False
        assert body["delay_days"] == 0

    def test_activity_persisted(self, client, db_session):
        activity_id = create_activity(client).json()["id"]
        row = db_session.execute(
            select(Activity).where(Activity.id == activity_id)
        ).scalar_one()
        assert row.name == "Foundations"
        assert row.project_stage == "Foundation"
        assert row.status == "not_started"
        assert row.progress_percentage == 0

    def test_missing_or_blank_name_rejected(self, client):
        assert create_activity(client, name=None).status_code == 422
        assert create_activity(client, name="   ").status_code == 422

    def test_invalid_status_rejected(self, client):
        response = create_activity(client, status="on_hold")
        assert response.status_code == 422
        assert "Invalid activity status" in response.text

    def test_status_normalized_to_lowercase(self, client):
        response = create_activity(client, status="In Progress")
        assert response.status_code == 201, response.text
        assert response.json()["status"] == "in_progress"

    def test_progress_bounds_rejected(self, client):
        assert create_activity(client, progress_percentage=-1).status_code == 422
        assert create_activity(client, progress_percentage=101).status_code == 422
        assert create_activity(client, progress_percentage=0).status_code == 201
        assert create_activity(client, progress_percentage=100).status_code == 201

    def test_planned_dates_invalid_order_rejected(self, client):
        response = create_activity(
            client,
            planned_start_date=str(TODAY + timedelta(days=10)),
            planned_end_date=str(TODAY + timedelta(days=1)),
        )
        assert response.status_code == 422
        assert "end date cannot be before the start date" in response.text

    def test_actual_dates_invalid_order_rejected(self, client):
        response = create_activity(
            client,
            status="in_progress",
            actual_start_date=str(TODAY + timedelta(days=2)),
            actual_end_date=str(TODAY + timedelta(days=1)),
        )
        assert response.status_code == 422

    def test_estimate_link(self, client, db_session):
        estimate = add_estimate(db_session)
        response = create_activity(client, estimate_id=str(estimate.id))
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["estimate_id"] == str(estimate.id)
        assert body["estimate_title"] == estimate.title

    def test_unknown_estimate_rejected(self, client):
        response = create_activity(client, estimate_id=str(uuid.uuid4()))
        assert response.status_code == 404

    def test_optional_fields_stripped(self, client):
        response = create_activity(
            client,
            project="   MOLA FAKO   ",
            resource_dependency="   Cement   ",
            delay_reason="  Material shortage  ",
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["project"] == "MOLA FAKO"
        assert body["resource_dependency"] == "Cement"
        assert body["delay_reason"] == "Material shortage"

    def test_delayed_status_allowed_without_reason(self, client):
        # Spec: users are never forced to give a reason when it is unknown.
        response = create_activity(client, status="delayed")
        assert response.status_code == 201, response.text
        assert response.json()["status"] == "delayed"
        assert response.json()["delay_reason"] is None


class TestProgressAndStatusUpdates:
    def test_progress_update_via_patch(self, client, db_session):
        activity_id = create_activity(client).json()["id"]
        response = client.patch(
            f"/api/v1/schedule/{activity_id}", json={"progress_percentage": 60}
        )
        assert response.status_code == 200, response.text
        assert response.json()["progress_percentage"] == 60
        row = db_session.execute(
            select(Activity).where(Activity.id == activity_id)
        ).scalar_one()
        assert row.progress_percentage == 60

    def test_progress_out_of_range_rejected(self, client):
        activity_id = create_activity(client).json()["id"]
        assert client.patch(
            f"/api/v1/schedule/{activity_id}", json={"progress_percentage": -5}
        ).status_code == 422
        assert client.patch(
            f"/api/v1/schedule/{activity_id}", json={"progress_percentage": 101}
        ).status_code == 422

    def test_status_change_via_patch(self, client, db_session):
        activity_id = create_activity(client).json()["id"]
        response = client.patch(
            f"/api/v1/schedule/{activity_id}", json={"status": "completed"}
        )
        assert response.status_code == 200, response.text
        row = db_session.execute(
            select(Activity).where(Activity.id == activity_id)
        ).scalar_one()
        assert row.status == "completed"

    def test_progress_100_does_not_overwrite_status(self, client):
        # Spec: reaching 100% may suggest Completed but must not overwrite data.
        activity_id = create_activity(client, status="in_progress", progress_percentage=40).json()["id"]
        response = client.patch(
            f"/api/v1/schedule/{activity_id}", json={"progress_percentage": 100}
        )
        assert response.status_code == 200, response.text
        assert response.json()["progress_percentage"] == 100
        assert response.json()["status"] == "in_progress"

    def test_partial_update_merges_date_validation(self, client):
        activity_id = create_activity(
            client,
            planned_start_date=str(TODAY + timedelta(days=5)),
            planned_end_date=str(TODAY + timedelta(days=10)),
        ).json()["id"]
        response = client.patch(
            f"/api/v1/schedule/{activity_id}",
            json={"planned_end_date": str(TODAY + timedelta(days=2))},
        )
        assert response.status_code == 422


class TestDelayDetection:
    def test_not_delayed_before_planned_end(self, client):
        response = create_activity(client, status="in_progress", progress_percentage=30)
        body = response.json()
        assert body["is_delayed"] is False
        assert body["delay_days"] == 0

    def test_delayed_when_planned_end_has_passed(self, client):
        response = create_activity(
            client,
            planned_start_date=str(TODAY - timedelta(days=5)),
            planned_end_date=str(TODAY - timedelta(days=2)),
            status="in_progress",
            progress_percentage=80,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["is_delayed"] is True
        assert body["delay_days"] == 2

    def test_not_started_past_planned_end_is_delayed(self, client):
        response = create_activity(
            client,
            planned_start_date=str(TODAY - timedelta(days=5)),
            planned_end_date=str(TODAY - timedelta(days=1)),
            status="not_started",
        )
        body = response.json()
        assert body["is_delayed"] is True
        assert body["delay_days"] == 1

    def test_completed_on_time_not_delayed(self, client):
        response = create_activity(
            client,
            planned_start_date=str(TODAY - timedelta(days=10)),
            planned_end_date=str(TODAY - timedelta(days=2)),
            actual_start_date=str(TODAY - timedelta(days=9)),
            actual_end_date=str(TODAY - timedelta(days=3)),
            status="completed",
            progress_percentage=100,
        )
        body = response.json()
        assert body["is_delayed"] is False
        assert body["delay_days"] == 0

    def test_completed_late_is_delayed(self, client):
        response = create_activity(
            client,
            planned_start_date=str(TODAY - timedelta(days=10)),
            planned_end_date=str(TODAY - timedelta(days=6)),
            actual_start_date=str(TODAY - timedelta(days=9)),
            actual_end_date=str(TODAY - timedelta(days=3)),
            status="completed",
            progress_percentage=100,
        )
        body = response.json()
        assert body["is_delayed"] is True
        assert body["delay_days"] == 3

    def test_marked_delayed_reported_even_with_future_planned_end(self, client):
        response = create_activity(client, status="delayed")
        body = response.json()
        assert body["is_delayed"] is True
        assert body["delay_days"] == 0

    def test_cancelled_not_delayed(self, client):
        response = create_activity(
            client,
            planned_start_date=str(TODAY - timedelta(days=8)),
            planned_end_date=str(TODAY - timedelta(days=4)),
            status="cancelled",
        )
        body = response.json()
        assert body["is_delayed"] is False
        assert body["delay_days"] == 0

    def test_schedule_variance_flow(self, client, db_session):
        # Spec: planned activity -> progress recorded -> deadline passes ->
        # system identifies variance -> user records delay reason.
        response = create_activity(
            client,
            name="Roofing",
            planned_start_date=str(TODAY - timedelta(days=6)),
            planned_end_date=str(TODAY - timedelta(days=1)),
            status="in_progress",
        )
        activity_id = response.json()["id"]

        progress_resp = client.patch(
            f"/api/v1/schedule/{activity_id}", json={"progress_percentage": 75}
        )
        assert progress_resp.json()["progress_percentage"] == 75

        variance_resp = client.patch(
            f"/api/v1/schedule/{activity_id}", json={"status": "delayed"}
        )
        body = variance_resp.json()
        assert body["is_delayed"] is True
        assert body["delay_days"] >= 1

        reason_resp = client.patch(
            f"/api/v1/schedule/{activity_id}",
            json={"delay_reason": "Material shortage", "delay_reason_detail": "Cement unavailable"},
        )
        body = reason_resp.json()
        assert body["delay_reason"] == "Material shortage"
        assert body["delay_reason_detail"] == "Cement unavailable"

        row = db_session.execute(
            select(Activity).where(Activity.id == activity_id)
        ).scalar_one()
        assert row.delay_reason == "Material shortage"
        assert row.delay_reason_detail == "Cement unavailable"
        assert row.progress_percentage == 75
        assert row.status == "delayed"


class TestDelayReasons:
    def test_record_delay_reason(self, client):
        activity_id = create_activity(client, status="delayed").json()["id"]
        response = client.patch(
            f"/api/v1/schedule/{activity_id}", json={"delay_reason": "Supplier delay"}
        )
        assert response.status_code == 200, response.text
        assert response.json()["delay_reason"] == "Supplier delay"

    def test_delay_reason_is_free_text(self, client):
        activity_id = create_activity(client, status="delayed").json()["id"]
        response = client.patch(
            f"/api/v1/schedule/{activity_id}",
            json={"delay_reason": "Unknown at this time", "delay_reason_detail": "Awaiting site report"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["delay_reason"] == "Unknown at this time"
        assert body["delay_reason_detail"] == "Awaiting site report"

    def test_delay_reason_can_be_cleared(self, client):
        activity_id = create_activity(client, status="delayed", delay_reason="Weather").json()["id"]
        response = client.patch(
            f"/api/v1/schedule/{activity_id}", json={"delay_reason": None}
        )
        assert response.status_code == 200, response.text
        assert response.json()["delay_reason"] is None


class TestMilestones:
    def test_create_milestone_defaults_pending(self, client):
        response = create_milestone(client)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["name"] == "Foundation completed"
        assert body["status"] == "pending"
        assert body["actual_date"] is None

    def test_milestone_persisted(self, client, db_session):
        milestone_id = create_milestone(client).json()["id"]
        row = db_session.execute(
            select(Milestone).where(Milestone.id == milestone_id)
        ).scalar_one()
        assert row.name == "Foundation completed"
        assert row.status == "pending"

    def test_milestone_name_required(self, client):
        assert create_milestone(client, name=None).status_code == 422
        assert create_milestone(client, name="   ").status_code == 422

    def test_milestone_invalid_status_rejected(self, client):
        assert create_milestone(client, status="skipped").status_code == 422

    def test_milestone_update_status_and_actual_date(self, client, db_session):
        milestone_id = create_milestone(client).json()["id"]
        response = client.patch(
            f"/api/v1/schedule/milestones/{milestone_id}",
            json={"status": "completed", "actual_date": str(TODAY)},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "completed"
        assert body["actual_date"] == str(TODAY)
        row = db_session.execute(
            select(Milestone).where(Milestone.id == milestone_id)
        ).scalar_one()
        assert row.status == "completed"

    def test_milestone_estimate_link(self, client, db_session):
        estimate = add_estimate(db_session, title="ROOFING ESTIMATE")
        response = create_milestone(client, estimate_id=str(estimate.id))
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["estimate_id"] == str(estimate.id)
        assert body["estimate_title"] == "ROOFING ESTIMATE"

    def test_milestone_unknown_estimate_rejected(self, client):
        assert create_milestone(client, estimate_id=str(uuid.uuid4())).status_code == 404

    def test_milestone_list_and_get(self, client):
        first = create_milestone(client, name="Foundation completed").json()
        second = create_milestone(client, name="Roofing completed").json()
        listing = client.get("/api/v1/schedule/milestones")
        assert listing.status_code == 200, listing.text
        body = listing.json()
        assert body["total"] == 2
        detail = client.get(f"/api/v1/schedule/milestones/{first['id']}")
        assert detail.status_code == 200
        assert detail.json()["name"] == "Foundation completed"
        assert client.get("/api/v1/schedule/milestones/00000000-0000-0000-0000-000000000000").status_code == 404


class TestRetrievalAndFilters:
    def test_list_activities(self, client):
        create_activity(client, name="Foundations")
        create_activity(client, name="Roofing")
        listing = client.get("/api/v1/schedule")
        assert listing.status_code == 200, listing.text
        body = listing.json()
        assert body["total"] == 2
        assert {item["name"] for item in body["activities"]} == {"Foundations", "Roofing"}

    def test_filter_by_status(self, client):
        create_activity(client, name="Foundations", status="completed", progress_percentage=100)
        create_activity(client, name="Roofing", status="in_progress")
        response = client.get("/api/v1/schedule", params={"status": "completed"})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 1
        assert body["activities"][0]["name"] == "Foundations"

    def test_filter_by_project_stage(self, client):
        create_activity(client, name="Concrete works", project_stage="Foundation")
        create_activity(client, name="Wall finishing", project_stage="Superstructure")
        response = client.get("/api/v1/schedule", params={"project_stage": "Foundation"})
        body = response.json()
        assert body["total"] == 1
        assert body["activities"][0]["name"] == "Concrete works"

    def test_get_activity_by_id(self, client):
        activity_id = create_activity(client).json()["id"]
        response = client.get(f"/api/v1/schedule/{activity_id}")
        assert response.status_code == 200, response.text
        assert response.json()["id"] == activity_id

    def test_unknown_activity_404(self, client):
        assert client.get("/api/v1/schedule/00000000-0000-0000-0000-000000000000").status_code == 404
        assert client.patch(
            "/api/v1/schedule/00000000-0000-0000-0000-000000000000", json={"status": "blocked"}
        ).status_code == 404

    def test_delete_not_supported(self, client):
        activity_id = create_activity(client).json()["id"]
        assert client.delete(f"/api/v1/schedule/{activity_id}").status_code == 405


class TestSummary:
    def test_summary_counts_and_average(self, client):
        create_activity(client, name="A", status="completed", progress_percentage=100)
        create_activity(client, name="B", status="in_progress", progress_percentage=60)
        create_activity(client, name="C", status="delayed", progress_percentage=40)
        create_activity(client, name="D", status="not_started", progress_percentage=0)
        create_activity(client, name="E", status="cancelled", progress_percentage=10)

        response = client.get("/api/v1/schedule/summary")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total_activities"] == 5
        assert body["total_completed"] == 1
        assert body["total_in_progress"] == 1
        assert body["total_delayed"] == 1
        assert body["total_blocked"] == 0
        assert body["total_not_started"] == 1
        assert body["total_cancelled"] == 1
        # Excludes cancelled; average of 100, 60, 40, 0 = 50.0
        assert body["overall_progress"] == 50.0
        assert "Simple average" in body["progress_calculation"]

    def test_summary_included_in_list_response(self, client):
        create_activity(client, name="A", status="in_progress", progress_percentage=25)
        response = client.get("/api/v1/schedule")
        body = response.json()
        assert body["summary"]["total_activities"] == 1
        assert body["summary"]["overall_progress"] == 25.0

    def test_summary_empty(self, client):
        response = client.get("/api/v1/schedule/summary")
        body = response.json()
        assert body["total_activities"] == 0
        assert body["overall_progress"] is None