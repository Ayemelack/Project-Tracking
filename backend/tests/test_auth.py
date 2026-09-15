"""Stage A: authentication, roles and project membership."""

import pytest

from tests.conftest import TEST_PASSWORD, ADMIN_USERNAME


def test_health_is_public(raw_client):
    resp = raw_client.get("/api/v1/health")
    assert resp.status_code == 200


def test_login_success_returns_token_and_user(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": ADMIN_USERNAME, "password": TEST_PASSWORD},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["username"] == ADMIN_USERNAME
    assert body["user"]["role"] == "administrator"
    assert body["user"]["status"] == "active"


def test_login_wrong_password_rejected(raw_client):
    resp = raw_client.post(
        "/api/v1/auth/login",
        json={"username": ADMIN_USERNAME, "password": "wrong"},
    )
    assert resp.status_code == 401


def test_login_unknown_user_rejected(raw_client):
    resp = raw_client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "whatever"},
    )
    assert resp.status_code == 401


def test_me_returns_user_and_projects(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["username"] == ADMIN_USERNAME
    assert body["projects"], "admin should belong to the seeded project"
    assert body["projects"][0]["name"] == "Test Project"


def test_protected_routes_require_auth(raw_client):
    for url in [
        "/api/v1/estimates",
        "/api/v1/funds",
        "/api/v1/allocations",
        "/api/v1/expenses",
        "/api/v1/resources",
        "/api/v1/schedule",
        "/api/v1/auth/me",
    ]:
        resp = raw_client.get(url)
        assert resp.status_code == 401, f"{url} should require auth"


def test_invalid_token_rejected(raw_client):
    resp = raw_client.get(
        "/api/v1/estimates",
        headers={"Authorization": "Bearer not.a.token"},
    )
    assert resp.status_code == 401


def test_wrong_scheme_rejected(raw_client):
    resp = raw_client.get(
        "/api/v1/estimates",
        headers={"Authorization": "Basic abc"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Roles: read access for every role
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fixture_name", ["client", "member_client", "viewer_client"])
def test_all_roles_can_read(request, fixture_name):
    authed = request.getfixturevalue(fixture_name)
    for url in [
        "/api/v1/estimates",
        "/api/v1/funds",
        "/api/v1/expenses",
        "/api/v1/resources",
        "/api/v1/schedule",
    ]:
        assert authed.get(url).status_code == 200, f"{fixture_name}: {url}"


# ---------------------------------------------------------------------------
# Role enforcement on write operations
# ---------------------------------------------------------------------------

def test_viewer_cannot_create_expense(viewer_client):
    resp = viewer_client.post(
        "/api/v1/expenses",
        json={"expense_date": "2026-09-10", "description": "Blocked", "amount": 100},
    )
    assert resp.status_code == 403


def test_member_can_create_expense(member_client):
    resp = member_client.post(
        "/api/v1/expenses",
        json={"expense_date": "2026-09-10", "description": "Allowed", "amount": 100},
    )
    assert resp.status_code == 201


def test_viewer_cannot_create_activity(viewer_client):
    resp = viewer_client.post("/api/v1/schedule", json={"name": "Blocked task"})
    assert resp.status_code == 403


def test_member_can_create_activity(member_client):
    resp = member_client.post("/api/v1/schedule", json={"name": "Allowed task"})
    assert resp.status_code == 201


def test_viewer_cannot_upload_or_run_admin_actions(viewer_client):
    assert viewer_client.post("/api/v1/estimates/00000000-0000-0000-0000-000000000001/confirm").status_code == 403


def test_viewer_cannot_create_fund(viewer_client):
    resp = viewer_client.post(
        "/api/v1/funds",
        json={"amount": 100, "received_date": "2026-09-10", "source": "Test", "purpose": "Test purpose"},
    )
    assert resp.status_code == 403


def test_member_cannot_confirm_estimate(member_client, client, estimate_id):
    resp = member_client.post(f"/api/v1/estimates/{estimate_id}/confirm")
    assert resp.status_code == 403
    assert client.get(f"/api/v1/estimates/{estimate_id}").json()["status"] != "confirmed"


def test_admin_can_confirm_estimate(client, estimate_id):
    resp = client.post(f"/api/v1/estimates/{estimate_id}/confirm")
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"


def test_member_cannot_delete_estimate(member_client, client, estimate_id):
    assert member_client.delete(f"/api/v1/estimates/{estimate_id}").status_code == 403
    assert client.get(f"/api/v1/estimates/{estimate_id}").status_code == 200


def test_viewer_cannot_delete_estimate(viewer_client, client, estimate_id):
    assert viewer_client.delete(f"/api/v1/estimates/{estimate_id}").status_code == 403


def test_member_cannot_cancel_allocation(member_client, client, allocation_id):
    assert member_client.post(f"/api/v1/allocations/{allocation_id}/cancel", json={"reason": "nope"}).status_code == 403


def test_member_cannot_reverse_expense(member_client, client, expense_id):
    assert member_client.post(f"/api/v1/expenses/{expense_id}/reverse", json={"reason": "nope"}).status_code == 403


def test_admin_can_reverse_expense(client, expense_id):
    resp = client.post(f"/api/v1/expenses/{expense_id}/reverse", json={"reason": "admin correction"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "reversed"


# ---------------------------------------------------------------------------
# User administration (administrator only)
# ---------------------------------------------------------------------------

def test_list_users_admin_only(viewer_client, client):
    assert viewer_client.get("/api/v1/auth/users").status_code == 403
    resp = client.get("/api/v1/auth/users")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


def test_create_user_admin_only(member_client, client):
    assert member_client.post(
        "/api/v1/auth/users",
        json={"username": "newuser", "full_name": "New User", "password": "secret123", "role": "member"},
    ).status_code == 403

    resp = client.post(
        "/api/v1/auth/users",
        json={"username": "newuser", "full_name": "New User", "password": "secret123", "role": "member"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "member"


def test_duplicate_username_conflict(client):
    first = client.post(
        "/api/v1/auth/users",
        json={"username": "dupe", "full_name": "First", "password": "secret123", "role": "member"},
    )
    assert first.status_code == 201
    second = client.post(
        "/api/v1/auth/users",
        json={"username": "dupe", "full_name": "Second", "password": "secret123", "role": "administrator"},
    )
    assert second.status_code == 409


def test_invalid_role_rejected(client):
    resp = client.post(
        "/api/v1/auth/users",
        json={"username": "badrole", "full_name": "Bad", "password": "secret123", "role": "superuser"},
    )
    assert resp.status_code == 422


def test_update_user_role_and_status(client):
    created = client.post(
        "/api/v1/auth/users",
        json={"username": "toupdate", "full_name": "To Update", "password": "secret123", "role": "member"},
    ).json()
    user_id = created["id"]
    resp = client.patch(f"/api/v1/auth/users/{user_id}", json={"role": "viewer", "status": "inactive"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "viewer"
    assert resp.json()["status"] == "inactive"


def test_inactive_account_cannot_login(client):
    created = client.post(
        "/api/v1/auth/users",
        json={"username": "frozen", "full_name": "Frozen", "password": "secret123", "role": "member"},
    ).json()
    client.patch(f"/api/v1/auth/users/{created['id']}", json={"status": "inactive"})
    login = client.post("/api/v1/auth/login", json={"username": "frozen", "password": "secret123"})
    assert login.status_code == 403


# ---------------------------------------------------------------------------
# Projects and membership
# ---------------------------------------------------------------------------

def test_create_project_admin_only(viewer_client, client):
    assert viewer_client.post("/api/v1/auth/projects", json={"name": "Blocked Project"}).status_code == 403
    resp = client.post("/api/v1/auth/projects", json={"name": "New Project"})
    assert resp.status_code == 201


def test_list_projects_any_role(viewer_client):
    resp = viewer_client.get("/api/v1/auth/projects")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


def test_add_and_remove_project_member(client, member_client):
    new_user = client.post(
        "/api/v1/auth/users",
        json={"username": "member2", "full_name": "Member Two", "password": "secret123", "role": "member"},
    ).json()
    projects = client.get("/api/v1/auth/projects").json()["projects"]
    project_id = projects[0]["id"]

    joined = client.post(f"/api/v1/auth/projects/{project_id}/members/{new_user['id']}")
    assert joined.status_code == 201
    assert any(p["id"] == project_id for p in joined.json()["projects"])

    removed = client.delete(f"/api/v1/auth/projects/{project_id}/members/{new_user['id']}")
    assert removed.status_code == 200
    assert not any(p["id"] == project_id for p in removed.json()["projects"])


def test_list_project_members_admin_only(member_client, client):
    assert member_client.get("/api/v1/auth/projects/00000000-0000-0000-0000-000000000001/members").status_code == 403
    new_user = client.post(
        "/api/v1/auth/users",
        json={"username": "projmember", "full_name": "Proj Member", "password": "secret123", "role": "member"},
    ).json()
    projects = client.get("/api/v1/auth/projects").json()["projects"]
    project_id = projects[0]["id"]
    client.post(f"/api/v1/auth/projects/{project_id}/members/{new_user['id']}")
    resp = client.get(f"/api/v1/auth/projects/{project_id}/members")
    assert resp.status_code == 200
    assert any(u["id"] == new_user["id"] for u in resp.json()["users"])


def test_member_cannot_manage_membership(member_client):
    assert member_client.post(
        "/api/v1/auth/projects/00000000-0000-0000-0000-000000000001/members/00000000-0000-0000-0000-000000000002"
    ).status_code == 403


# ---------------------------------------------------------------------------
# Public account registration
# ---------------------------------------------------------------------------

def test_register_first_user_becomes_administrator(raw_client):
    resp = raw_client.post(
        "/api/v1/auth/register",
        json={
            "username": "firstuser",
            "full_name": "First User",
            "password": "secret123",
            "confirm_password": "secret123",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["username"] == "firstuser"
    assert body["user"]["role"] == "administrator"
    assert body["message"]


def test_register_subsequent_user_is_viewer(raw_client):
    raw_client.post(
        "/api/v1/auth/register",
        json={
            "username": "founder",
            "full_name": "Founder",
            "password": "secret123",
            "confirm_password": "secret123",
        },
    )
    resp = raw_client.post(
        "/api/v1/auth/register",
        json={
            "username": "lateruser",
            "full_name": "Later User",
            "password": "secret123",
            "confirm_password": "secret123",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["user"]["role"] == "viewer"


def test_register_duplicate_username_conflict(raw_client):
    first = raw_client.post(
        "/api/v1/auth/register",
        json={
            "username": "dupeuser",
            "full_name": "First",
            "password": "secret123",
            "confirm_password": "secret123",
        },
    )
    assert first.status_code == 201
    second = raw_client.post(
        "/api/v1/auth/register",
        json={
            "username": "dupeuser",
            "full_name": "Second",
            "password": "secret123",
            "confirm_password": "secret123",
        },
    )
    assert second.status_code == 409


def test_register_password_mismatch_rejected(raw_client):
    resp = raw_client.post(
        "/api/v1/auth/register",
        json={
            "username": "mismatch",
            "full_name": "Mismatch",
            "password": "secret123",
            "confirm_password": "different123",
        },
    )
    assert resp.status_code == 422


def test_registered_user_can_login(raw_client):
    raw_client.post(
        "/api/v1/auth/register",
        json={
            "username": "newlogin",
            "full_name": "New Login",
            "password": "secret123",
            "confirm_password": "secret123",
        },
    )
    resp = raw_client.post(
        "/api/v1/auth/login",
        json={"username": "newlogin", "password": "secret123"},
    )
    assert resp.status_code == 200
    assert resp.json()["user"]["username"] == "newlogin"


def test_registered_user_has_no_project_membership(raw_client):
    raw_client.post(
        "/api/v1/auth/register",
        json={
            "username": "nomember",
            "full_name": "No Member",
            "password": "secret123",
            "confirm_password": "secret123",
        },
    )
    login = raw_client.post(
        "/api/v1/auth/login",
        json={"username": "nomember", "password": "secret123"},
    )
    token = login.json()["access_token"]
    me = raw_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    assert me.json()["projects"] == []


def test_register_rejects_numeric_full_name(raw_client):
    for name in ["12345", "123 John", "999999"]:
        resp = raw_client.post(
            "/api/v1/auth/register",
            json={
                "username": "numname",
                "full_name": name,
                "password": "secret123",
                "confirm_password": "secret123",
            },
        )
        assert resp.status_code == 422, f"{name!r} should be rejected"


def test_register_accepts_valid_full_names(raw_client):
    for name in ["John Doe", "Jean-Paul Kamga", "Mary Jane", "O'Connor"]:
        resp = raw_client.post(
            "/api/v1/auth/register",
            json={
                "username": name.lower().replace(" ", "_").replace("-", "_").replace("'", ""),
                "full_name": name,
                "password": "secret123",
                "confirm_password": "secret123",
            },
        )
        assert resp.status_code == 201, f"{name!r} should be accepted"


def test_register_short_password_rejected(raw_client):
    resp = raw_client.post(
        "/api/v1/auth/register",
        json={
            "username": "shortpass",
            "full_name": "Short Pass",
            "password": "abc",
            "confirm_password": "abc",
        },
    )
    assert resp.status_code == 422


def test_register_username_with_spaces_rejected(raw_client):
    resp = raw_client.post(
        "/api/v1/auth/register",
        json={
            "username": "bad user",
            "full_name": "Bad User",
            "password": "secret123",
            "confirm_password": "secret123",
        },
    )
    assert resp.status_code == 422


def test_register_username_with_period_accepted(raw_client):
    resp = raw_client.post(
        "/api/v1/auth/register",
        json={
            "username": "john.doe",
            "full_name": "John Doe",
            "password": "secret123",
            "confirm_password": "secret123",
        },
    )
    assert resp.status_code == 201


def test_invalid_register_credentials_not_revealed(raw_client):
    raw_client.post(
        "/api/v1/auth/register",
        json={
            "username": "whoops",
            "full_name": "Whoops",
            "password": "secret123",
            "confirm_password": "secret123",
        },
    )
    resp = raw_client.post(
        "/api/v1/auth/login",
        json={"username": "whoops", "password": "wrongpass"},
    )
    assert resp.status_code == 401
    assert resp.json().get("detail") == "Invalid username or password"


# ---------------------------------------------------------------------------
# Forgot / Reset password (self-service, authenticated)
# ---------------------------------------------------------------------------

def test_reset_password_requires_auth(raw_client):
    resp = raw_client.post(
        "/api/v1/auth/reset-password",
        json={"new_password": "brand-new-456", "confirm_password": "brand-new-456"},
    )
    assert resp.status_code == 401


def _register_reset_user(raw_client, username="resetuser", password="initial123"):
    resp = raw_client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "full_name": "Reset User",
            "password": password,
            "confirm_password": password,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _login_token(raw_client, username, password):
    login = raw_client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def test_reset_password_success_and_old_password_invalid(raw_client):
    _register_reset_user(raw_client)
    token = _login_token(raw_client, "resetuser", "initial123")
    resp = raw_client.post(
        "/api/v1/auth/reset-password",
        json={"new_password": "brand-new-456", "confirm_password": "brand-new-456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Password has been reset successfully."
    # Old password no longer works.
    old = raw_client.post(
        "/api/v1/auth/login", json={"username": "resetuser", "password": "initial123"}
    )
    assert old.status_code == 401
    # New password works.
    new = raw_client.post(
        "/api/v1/auth/login", json={"username": "resetuser", "password": "brand-new-456"}
    )
    assert new.status_code == 200


def test_reset_password_mismatch_rejected(raw_client):
    _register_reset_user(raw_client)
    token = _login_token(raw_client, "resetuser", "initial123")
    resp = raw_client.post(
        "/api/v1/auth/reset-password",
        json={"new_password": "brand-new-456", "confirm_password": "different-789"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


def test_reset_password_short_password_rejected(raw_client):
    _register_reset_user(raw_client)
    token = _login_token(raw_client, "resetuser", "initial123")
    resp = raw_client.post(
        "/api/v1/auth/reset-password",
        json={"new_password": "abc", "confirm_password": "abc"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


def test_reset_password_cannot_change_other_user(raw_client):
    # A reset only ever changes the password of the authenticated user. It
    # must not be possible to change another user's password.
    _register_reset_user(raw_client, "resetter", "initial123")
    _register_reset_user(raw_client, "victim", "victimPass123")
    token = _login_token(raw_client, "resetter", "initial123")
    resp = raw_client.post(
        "/api/v1/auth/reset-password",
        json={"new_password": "attacker-new-456", "confirm_password": "attacker-new-456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    # The victim's password is unchanged.
    victim = raw_client.post(
        "/api/v1/auth/login", json={"username": "victim", "password": "victimPass123"}
    )
    assert victim.status_code == 200
    # The resetter can now sign in with their new password.
    resetter = raw_client.post(
        "/api/v1/auth/login", json={"username": "resetter", "password": "attacker-new-456"}
    )
    assert resetter.status_code == 200


def test_reset_password_hash_never_returned(raw_client):
    _register_reset_user(raw_client)
    token = _login_token(raw_client, "resetuser", "initial123")
    resp = raw_client.post(
        "/api/v1/auth/reset-password",
        json={"new_password": "brand-new-456", "confirm_password": "brand-new-456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "password_hash" not in resp.text
    assert "brand-new-456" not in resp.text


# ---------------------------------------------------------------------------
# Security hardening: identifier policy, brute-force protection, headers
# ---------------------------------------------------------------------------

def test_register_rejects_invalid_identifiers(raw_client):
    for username in [
        "..",
        "....",
        "@@",
        "abc@",
        "@example",
        "a@b@c",
        "john..doe",
        ".jane",
        "jane-",
        "a b",
    ]:
        resp = raw_client.post(
            "/api/v1/auth/register",
            json={
                "username": username,
                "full_name": "Valid Name",
                "password": "secret123",
                "confirm_password": "secret123",
            },
        )
        assert resp.status_code == 422, f"{username!r} should be rejected"


def test_register_accepts_valid_identifiers(raw_client):
    for username in [
        "john.doe",
        "jane_doe",
        "jean-paul",
        "normaluser",
        "ayemelacknoshinedo@gmail.com",
    ]:
        resp = raw_client.post(
            "/api/v1/auth/register",
            json={
                "username": username,
                "full_name": "Valid Name",
                "password": "secret123",
                "confirm_password": "secret123",
            },
        )
        assert resp.status_code == 201, f"{username!r} should be accepted"


def test_admin_create_user_rejects_invalid_username(client):
    resp = client.post(
        "/api/v1/auth/users",
        json={"username": "a..b", "full_name": "Valid Name", "password": "secret123", "role": "member"},
    )
    assert resp.status_code == 422


def test_login_throttled_after_repeated_failures(client):
    from app.api.v1.auth import LOGIN_FAILED_LIMIT

    for _ in range(LOGIN_FAILED_LIMIT):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": ADMIN_USERNAME, "password": "wrongpass"},
        )
        assert resp.status_code == 401
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": ADMIN_USERNAME, "password": "wrongpass"},
    )
    assert resp.status_code == 429
    assert resp.json()["detail"] == "Too many attempts. Please try again later."


def test_successful_login_clears_throttle(client):
    for _ in range(3):
        client.post(
            "/api/v1/auth/login",
            json={"username": ADMIN_USERNAME, "password": "wrongpass"},
        )
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": ADMIN_USERNAME, "password": TEST_PASSWORD},
    )
    assert resp.status_code == 200
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": ADMIN_USERNAME, "password": "wrongpass"},
    )
    assert resp.status_code == 401


def test_register_throttled_per_ip(raw_client):
    from app.api.v1.auth import REGISTER_IP_LIMIT

    for i in range(REGISTER_IP_LIMIT):
        resp = raw_client.post(
            "/api/v1/auth/register",
            json={
                "username": f"reguser{i}",
                "full_name": "Registry User",
                "password": "secret123",
                "confirm_password": "secret123",
            },
        )
        assert resp.status_code == 201, resp.text
    resp = raw_client.post(
        "/api/v1/auth/register",
        json={
            "username": "regoverflow",
            "full_name": "Registry User",
            "password": "secret123",
            "confirm_password": "secret123",
        },
    )
    assert resp.status_code == 429


def test_unknown_user_and_wrong_password_identical_response(raw_client):
    raw_client.post(
        "/api/v1/auth/register",
        json={
            "username": "timinguser",
            "full_name": "Timing User",
            "password": "secret123",
            "confirm_password": "secret123",
        },
    )
    unknown = raw_client.post(
        "/api/v1/auth/login",
        json={"username": "ghostuser", "password": "totallywrong"},
    )
    wrong_password = raw_client.post(
        "/api/v1/auth/login",
        json={"username": "timinguser", "password": "totallywrong"},
    )
    assert unknown.status_code == 401
    assert wrong_password.status_code == 401
    assert unknown.json() == wrong_password.json()


def test_multiple_login_attempts_across_ip_keys_isolated(raw_client):
    # Attempts for one username must not throttle a different username.
    for _ in range(5):
        raw_client.post(
            "/api/v1/auth/login",
            json={"username": "firstvictim", "password": "wrongpass"},
        )
    resp = raw_client.post(
        "/api/v1/auth/login",
        json={"username": "otheruser", "password": "wrongpass"},
    )
    assert resp.status_code == 401


def test_security_headers_present(raw_client):
    resp = raw_client.get("/api/v1/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "no-referrer"
    assert "no-store" in resp.headers["cache-control"]


def test_password_hash_never_returned(client):
    created = client.post(
        "/api/v1/auth/users",
        json={"username": "nosecret", "full_name": "No Secret", "password": "secret123", "role": "member"},
    ).json()
    assert "password_hash" not in created
    users = client.get("/api/v1/auth/users").json()["users"]
    for user in users:
        assert "password_hash" not in user


# ---------------------------------------------------------------------------
# Fixtures used by admin-only checks above
# ---------------------------------------------------------------------------

@pytest.fixture()
def estimate_id(db_session):
    from app.models.models import Estimate

    estimate = Estimate(
        title="Auth test estimate",
        currency="FCFA",
        original_filename="auth-test.pdf",
        stored_filename="auth-test.pdf",
        status="extracted",
        total_estimated_amount=0,
    )
    db_session.add(estimate)
    db_session.commit()
    db_session.refresh(estimate)
    return estimate.id


@pytest.fixture()
def allocation_id(client, estimate_id):
    fund = client.post(
        "/api/v1/funds",
        json={"amount": 10000, "received_date": "2026-09-10", "source": "Auth test fund", "purpose": "Auth test"},
    ).json()
    allocation = client.post(
        f"/api/v1/funds/{fund['id']}/allocations",
        json={"amount": 5000, "estimate_id": str(estimate_id), "purpose": "Auth test"},
    )
    assert allocation.status_code in (200, 201), allocation.text
    return allocation.json()["id"]


@pytest.fixture()
def expense_id(client, allocation_id):
    resp = client.post(
        "/api/v1/expenses",
        json={
            "expense_date": "2026-09-10",
            "amount": 1000,
            "description": "Auth test expense",
            "allocation_id": allocation_id,
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Secure Admin/Owner account registration
# ---------------------------------------------------------------------------

ADMIN_KEY = "test-admin-key-2026"


def _set_admin_key(monkeypatch):
    # The key lives server-side in configuration; tests set it directly on the
    # shared settings object the auth service reads at request time.
    monkeypatch.setattr(
        "app.services.auth_service.settings.ADMIN_REGISTRATION_SECRET", ADMIN_KEY
    )


def _register_body(username, extra=None):
    body = {
        "username": username,
        "full_name": "Admin Key Tester",
        "password": "secret123",
        "confirm_password": "secret123",
    }
    if extra:
        body.update(extra)
    return body


def test_register_normal_user_without_key_is_viewer(raw_client):
    # Make this a subsequent registration so it is not the first user.
    raw_client.post(
        "/api/v1/auth/register",
        json={"username": "founder2", "full_name": "Founder Two", "password": "secret123", "confirm_password": "secret123"},
    )
    resp = raw_client.post(
        "/api/v1/auth/register",
        json=_register_body("plainviewer", {"admin_registration_secret": ""}),
    )
    assert resp.status_code == 201
    assert resp.json()["user"]["role"] == "viewer"


def test_register_with_valid_admin_key_creates_administrator(raw_client, monkeypatch):
    _set_admin_key(monkeypatch)
    raw_client.post(
        "/api/v1/auth/register",
        json={"username": "founder3", "full_name": "Founder Three", "password": "secret123", "confirm_password": "secret123"},
    )
    resp = raw_client.post(
        "/api/v1/auth/register",
        json=_register_body("newadmin", {"admin_registration_secret": ADMIN_KEY}),
    )
    assert resp.status_code == 201
    assert resp.json()["user"]["role"] == "administrator"


def test_register_admin_account_keeps_role_after_login(raw_client, monkeypatch):
    _set_admin_key(monkeypatch)
    raw_client.post(
        "/api/v1/auth/register",
        json={"username": "founder4", "full_name": "Founder Four", "password": "secret123", "confirm_password": "secret123"},
    )
    reg = raw_client.post(
        "/api/v1/auth/register",
        json=_register_body("adminpersist", {"admin_registration_secret": ADMIN_KEY}),
    )
    assert reg.status_code == 201
    assert reg.json()["user"]["role"] == "administrator"
    login = raw_client.post(
        "/api/v1/auth/login",
        json={"username": "adminpersist", "password": "secret123"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "administrator"
    me = raw_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["user"]["role"] == "administrator"


def test_register_with_invalid_admin_key_rejected(raw_client, monkeypatch):
    _set_admin_key(monkeypatch)
    raw_client.post(
        "/api/v1/auth/register",
        json={"username": "founder5", "full_name": "Founder Five", "password": "secret123", "confirm_password": "secret123"},
    )
    resp = raw_client.post(
        "/api/v1/auth/register",
        json=_register_body("notadmin", {"admin_registration_secret": "wrong-key"}),
    )
    assert resp.status_code == 403
    # No account is created and the forged role never appears anywhere.
    login = raw_client.post(
        "/api/v1/auth/login", json={"username": "notadmin", "password": "secret123"}
    )
    assert login.status_code == 401


def test_register_admin_key_ignored_when_not_configured(raw_client):
    # With no key configured server-side, supplying one must never grant admin.
    raw_client.post(
        "/api/v1/auth/register",
        json={"username": "founder6", "full_name": "Founder Six", "password": "secret123", "confirm_password": "secret123"},
    )
    resp = raw_client.post(
        "/api/v1/auth/register",
        json=_register_body("nogrant", {"admin_registration_secret": "any-key"}),
    )
    assert resp.status_code == 403


@pytest.mark.parametrize(
    "forge_field",
    [
        {"role": "administrator"},
        {"role": "admin"},
        {"role": "owner"},
        {"is_admin": True},
        {"is_admin": "true"},
    ],
)
def test_register_rejects_client_supplied_privilege_fields(raw_client, forge_field, monkeypatch):
    _set_admin_key(monkeypatch)
    raw_client.post(
        "/api/v1/auth/register",
        json={"username": "founder7", "full_name": "Founder Seven", "password": "secret123", "confirm_password": "secret123"},
    )
    resp = raw_client.post(
        "/api/v1/auth/register",
        json=_register_body("forger", forge_field),
    )
    assert resp.status_code == 422
    login = raw_client.post(
        "/api/v1/auth/login", json={"username": "forger", "password": "secret123"}
    )
    assert login.status_code == 401


def test_register_role_plus_valid_key_still_rejected(raw_client, monkeypatch):
    _set_admin_key(monkeypatch)
    raw_client.post(
        "/api/v1/auth/register",
        json={"username": "founder8", "full_name": "Founder Eight", "password": "secret123", "confirm_password": "secret123"},
    )
    resp = raw_client.post(
        "/api/v1/auth/register",
        json=_register_body(
            "keyandrole",
            {"admin_registration_secret": ADMIN_KEY, "role": "administrator"},
        ),
    )
    assert resp.status_code == 422
    login = raw_client.post(
        "/api/v1/auth/login", json={"username": "keyandrole", "password": "secret123"}
    )
    assert login.status_code == 401


def test_admin_key_never_returned_in_response(raw_client, monkeypatch):
    _set_admin_key(monkeypatch)
    raw_client.post(
        "/api/v1/auth/register",
        json={"username": "founder9", "full_name": "Founder Nine", "password": "secret123", "confirm_password": "secret123"},
    )
    resp = raw_client.post(
        "/api/v1/auth/register",
        json=_register_body("nodisclose", {"admin_registration_secret": ADMIN_KEY}),
    )
    assert resp.status_code == 201
    assert ADMIN_KEY not in resp.text
    login = raw_client.post(
        "/api/v1/auth/login", json={"username": "nodisclose", "password": "secret123"}
    )
    assert login.status_code == 200
    assert ADMIN_KEY not in login.text


def test_admin_key_guess_attempts_rate_limited(raw_client, monkeypatch):
    _set_admin_key(monkeypatch)
    raw_client.post(
        "/api/v1/auth/register",
        json={"username": "founderA", "full_name": "Founder A", "password": "secret123", "confirm_password": "secret123"},
    )
    statuses = []
    for i in range(7):
        resp = raw_client.post(
            "/api/v1/auth/register",
            json=_register_body(
                f"guess{i}",
                {"admin_registration_secret": f"bad-key-{i}"},
            ),
        )
        statuses.append(resp.status_code)
    assert statuses.count(429) >= 2
    assert resp.json()["detail"]
    # Every guess failed to create an administrator/any account.
    login = raw_client.post(
        "/api/v1/auth/login", json={"username": "guess6", "password": "secret123"}
    )
    assert login.status_code == 401


def test_admin_user_can_manage_records(raw_client, monkeypatch):
    _set_admin_key(monkeypatch)
    raw_client.post(
        "/api/v1/auth/register",
        json={"username": "founderB", "full_name": "Founder B", "password": "secret123", "confirm_password": "secret123"},
    )
    reg = raw_client.post(
        "/api/v1/auth/register",
        json=_register_body("managingadmin", {"admin_registration_secret": ADMIN_KEY}),
    )
    assert reg.status_code == 201
    login = raw_client.post(
        "/api/v1/auth/login",
        json={"username": "managingadmin", "password": "secret123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # Admin can create a project and a member.
    project = raw_client.post(
        "/api/v1/auth/projects", json={"name": "Admin Created Project"}, headers=headers
    )
    assert project.status_code in (200, 201), project.text
    # Admin can list all users.
    users = raw_client.get("/api/v1/auth/users", headers=headers)
    assert users.status_code == 200
    # Admin can even create another administrator account administratively.
    created = raw_client.post(
        "/api/v1/auth/users",
        json={
            "username": "secondadmin",
            "full_name": "Second Admin",
            "password": "secret123",
            "role": "administrator",
        },
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["role"] == "administrator"