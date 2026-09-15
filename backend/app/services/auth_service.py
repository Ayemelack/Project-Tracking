from uuid import UUID

import hashlib
import hmac

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.models import User, Project
from app.repositories.user_repository import user_repo, project_repo
from app.schemas.schemas import (
    MeResponse,
    ProjectPublic,
    TokenResponse,
    UserPublic,
)

ROLE_ADMIN = "administrator"
ROLE_MEMBER = "member"
ROLE_VIEWER = "viewer"
WRITE_ROLES = (ROLE_ADMIN, ROLE_MEMBER)


def to_user_public(user: User) -> UserPublic:
    return UserPublic.model_validate(user)


def to_project_public(project: Project) -> ProjectPublic:
    return ProjectPublic.model_validate(project)


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = user_repo.get_by_username(db, username)
    if not user:
        # Equalize timing with the wrong-password path so response latency
        # does not reveal whether a username exists.
        verify_password(password, DUMMY_PASSWORD_HASH)
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_token_response(user: User) -> TokenResponse:
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=token, token_type="bearer", user=to_user_public(user))


def user_or_403(user: User) -> User:
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Contact the project administrator.",
        )
    return user


def member_of(db: Session, user: User) -> MeResponse:
    projects = project_repo.projects_for_user(db, user.id)
    return MeResponse(
        user=to_user_public(user),
        projects=[to_project_public(p) for p in projects],
    )


def create_user(
    db: Session,
    *,
    username: str,
    full_name: str,
    password: str,
    role: str = ROLE_MEMBER,
    project_id: UUID | None = None,
) -> User:
    if user_repo.get_by_username(db, username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that username already exists.",
        )
    db_user = user_repo.create(
        db,
        username=username,
        full_name=full_name,
        password_hash=hash_password(password),
        role=role,
    )
    if project_id:
        project_repo.add_member(db, project_id, db_user.id)
    return db_user


def update_user(db: Session, user_id: UUID, fields: dict) -> User:
    db_user = user_repo.get_by_id(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if fields.get("password"):
        fields["password_hash"] = hash_password(fields.pop("password"))
    db_user = user_repo.update(db, user_id, fields)
    return db_user


def create_project(db: Session, name: str, description: str | None = None) -> Project:
    if project_repo.get_by_name(db, name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A project with that name already exists.",
        )
    return project_repo.create(db, name, description)


def get_or_create_project(db: Session, name: str, description: str | None = None) -> Project:
    project = project_repo.get_by_name(db, name)
    if project:
        return project
    return project_repo.create(db, name, description)


def ensure_membership(db: Session, user_id: UUID, project_id: UUID) -> None:
    membership = project_repo.add_member(db, project_id, user_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Project not found")


def has_users(db: Session) -> bool:
    return user_repo.get_count(db) > 0


def _admin_key_valid(supplied_key: str | None) -> bool:
    """Constant-time check of the admin registration key.

    The key never leaves the server: only a yes/no decision is returned. An
    empty configured key disables admin-key registration entirely.
    """
    configured = (settings.ADMIN_REGISTRATION_SECRET or "").strip()
    if not configured or not supplied_key:
        return False
    supplied_digest = hashlib.sha256(supplied_key.strip().encode("utf-8")).digest()
    configured_digest = hashlib.sha256(configured.encode("utf-8")).digest()
    return hmac.compare_digest(supplied_digest, configured_digest)


def register_user(
    db: Session,
    *,
    username: str,
    full_name: str,
    password: str,
    admin_registration_secret: str | None = None,
) -> User:
    if user_repo.get_by_username(db, username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this username already exists. Please sign in instead.",
        )
    user_count = user_repo.get_count(db)
    if user_count == 0:
        role = ROLE_ADMIN
    elif admin_registration_secret:
        if not _admin_key_valid(admin_registration_secret):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The admin registration key is invalid. No account was created.",
            )
        role = ROLE_ADMIN
    else:
        role = ROLE_VIEWER
    db_user = user_repo.create(
        db,
        username=username,
        full_name=full_name,
        password_hash=hash_password(password),
        role=role,
    )
    return db_user


def bootstrap_default(db: Session) -> None:
    """Ensure the default project exists. No admin user is auto-created."""
    get_or_create_project(db, settings.DEFAULT_PROJECT_NAME)
    db.commit()