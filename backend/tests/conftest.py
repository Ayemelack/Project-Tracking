import os
import sys

import pytest
from urllib.parse import urlsplit, urlunsplit

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app

TEST_DB_NAME = "project_tracking_test"

ADMIN_USERNAME = "admin_test"
MEMBER_USERNAME = "member_test"
VIEWER_USERNAME = "viewer_test"
TEST_PASSWORD = "test-pass-123"
TEST_PROJECT_NAME = "Test Project"


def _test_db_url() -> str:
    parts = urlsplit(settings.DATABASE_URL)
    return urlunsplit((parts.scheme, parts.netloc, "/" + TEST_DB_NAME, "", ""))


@pytest.fixture(scope="session")
def engine():
    admin_engine = create_engine(settings.DATABASE_URL, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": TEST_DB_NAME},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin_engine.dispose()

    test_engine = create_engine(_test_db_url())
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture()
def db_session(engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class AuthedClient:
    """Wrapper around TestClient that injects an Authorization header."""

    def __init__(self, tester: TestClient, headers: dict):
        self._tester = tester
        self._headers = headers

    def request(self, method: str, url: str, **kwargs):
        headers = dict(self._headers)
        headers.update(kwargs.pop("headers", None) or {})
        return self._tester.request(method, url, headers=headers, **kwargs)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def put(self, url, **kwargs):
        return self.request("PUT", url, **kwargs)

    def patch(self, url, **kwargs):
        return self.request("PATCH", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request("DELETE", url, **kwargs)


def _seed_user_and_project(engine, username: str, role: str) -> None:
    from app.models.models import User, Project, UserProject
    from app.repositories.user_repository import user_repo, project_repo

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    with SessionLocal() as db:
        user = user_repo.get_by_username(db, username)
        if not user:
            user = user_repo.create(
                db,
                username=username,
                full_name=f"Test {role}",
                password_hash=hash_password(TEST_PASSWORD),
                role=role,
            )
        project = project_repo.get_by_name(db, TEST_PROJECT_NAME)
        if not project:
            project = project_repo.create(db, TEST_PROJECT_NAME)
        existing = (
            db.query(UserProject)
            .filter(
                UserProject.user_id == user.id,
                UserProject.project_id == project.id,
            )
            .first()
        )
        if existing is None:
            project_repo.add_member(db, project.id, user.id)
        db.commit()


@pytest.fixture()
def client(engine):
    _seed_user_and_project(engine, ADMIN_USERNAME, "administrator")
    yield from _make_authed_client(engine, ADMIN_USERNAME)


@pytest.fixture()
def member_client(engine):
    _seed_user_and_project(engine, MEMBER_USERNAME, "member")
    yield from _make_authed_client(engine, MEMBER_USERNAME)


@pytest.fixture()
def viewer_client(engine):
    _seed_user_and_project(engine, VIEWER_USERNAME, "viewer")
    yield from _make_authed_client(engine, VIEWER_USERNAME)


def _make_authed_client(engine, username: str):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as tester:
            login = tester.post(
                "/api/v1/auth/login",
                json={"username": username, "password": TEST_PASSWORD},
            )
            assert login.status_code == 200, login.text
            token = login.json()["access_token"]
            yield AuthedClient(tester, {"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def raw_client(engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def no_openai_key(monkeypatch):
    """Keep the test suite offline and fast.

    The local backend/.env may carry a live OPENAI_API_KEY. Tests must never
    issue real OpenAI calls, so the key is forced empty (provider selection then
    degrades to the deterministic engine). Provider unit tests set their own
    (fake) key explicitly.
    """
    from pydantic import SecretStr

    monkeypatch.setattr(settings, "OPENAI_API_KEY", SecretStr(""))


@pytest.fixture(autouse=True)
def clean_tables(engine):
    yield
    from app.core.ratelimit import rate_limiter
    from sqlalchemy import text as sql_text

    rate_limiter.reset()
    with engine.connect() as conn:
        conn.execute(
            sql_text(
                'TRUNCATE TABLE user_projects, users, projects, fund_audit_logs, '
                'expenses, resource_movements, resources, fund_allocations, '
                'fund_receipts, estimate_line_items, estimates, activities, '
                'milestones RESTART IDENTITY CASCADE'
            )
        )
        conn.commit()