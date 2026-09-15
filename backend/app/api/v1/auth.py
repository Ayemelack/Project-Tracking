from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.ratelimit import rate_limiter
from app.models.models import User
from app.schemas.schemas import (
    AuthStatusResponse,
    LoginRequest,
    PasswordResetRequest,
    PasswordResetResponse,
    RegisterResponse,
    TokenResponse,
    UserCreateAdmin,
    UserListResponse,
    UserPublic,
    UserRegister,
    UserUpdateAdmin,
    ProjectCreate,
    ProjectListResponse,
    ProjectPublic,
    MeResponse,
)
from app.repositories.user_repository import user_repo, project_repo
from app.services import auth_service
from app.services.auth_service import ROLE_ADMIN
from app.api.v1.dependencies import get_current_user, require_admin

router = APIRouter()


LOGIN_IP_LIMIT = 30
LOGIN_IP_WINDOW_SECONDS = 300
LOGIN_FAILED_LIMIT = 5
LOGIN_FAILED_WINDOW_SECONDS = 900
REGISTER_IP_LIMIT = 10
REGISTER_IP_WINDOW_SECONDS = 3600
ADMIN_KEY_IP_LIMIT = 5
ADMIN_KEY_IP_WINDOW_SECONDS = 900
RESET_PASSWORD_IP_LIMIT = 10
RESET_PASSWORD_IP_WINDOW_SECONDS = 900

RATE_LIMITED_MESSAGE = "Too many attempts. Please try again later."
REGISTER_RATE_LIMITED_MESSAGE = "Too many accounts created from this location. Please try again later."


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/status", response_model=AuthStatusResponse)
def auth_status(db: Session = Depends(get_db)):
    return AuthStatusResponse(has_users=auth_service.has_users(db))


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(data: UserRegister, request: Request, db: Session = Depends(get_db)):
    client_ip = _client_ip(request)
    if not rate_limiter.allow(
        f"register-ip:{client_ip}", REGISTER_IP_LIMIT, REGISTER_IP_WINDOW_SECONDS
    ):
        raise HTTPException(status_code=429, detail=REGISTER_RATE_LIMITED_MESSAGE)
    if data.admin_registration_secret:
        # Throttle repeated guessing of the server-side admin registration key.
        if not rate_limiter.allow(
            f"admin-key-ip:{client_ip}", ADMIN_KEY_IP_LIMIT, ADMIN_KEY_IP_WINDOW_SECONDS
        ):
            raise HTTPException(status_code=429, detail=RATE_LIMITED_MESSAGE)
    user = auth_service.register_user(
        db,
        username=data.username,
        full_name=data.full_name,
        password=data.password,
        admin_registration_secret=data.admin_registration_secret,
    )
    return RegisterResponse(
        message="Account created successfully.",
        user=auth_service.to_user_public(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = _client_ip(request)
    if not rate_limiter.allow(
        f"login-ip:{client_ip}", LOGIN_IP_LIMIT, LOGIN_IP_WINDOW_SECONDS
    ):
        raise HTTPException(status_code=429, detail=RATE_LIMITED_MESSAGE)
    failed_key = f"login-failed:{client_ip}:{data.username.strip().lower()}"
    if not rate_limiter.allow(
        failed_key, LOGIN_FAILED_LIMIT, LOGIN_FAILED_WINDOW_SECONDS
    ):
        raise HTTPException(status_code=429, detail=RATE_LIMITED_MESSAGE)
    user = auth_service.authenticate_user(db, data.username, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    auth_service.user_or_403(user)
    rate_limiter.clear(failed_key)
    return auth_service.create_token_response(user)


@router.get("/me", response_model=MeResponse)
def me(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return auth_service.member_of(db, current_user)


@router.post("/reset-password", response_model=PasswordResetResponse)
def reset_password(
    data: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # The password is reset for the authenticated user only. The target user is
    # derived from the session token, never from a client-supplied identifier,
    # so one user cannot change another user's password.
    client_ip = _client_ip(request)
    if not rate_limiter.allow(
        f"reset-password-ip:{client_ip}",
        RESET_PASSWORD_IP_LIMIT,
        RESET_PASSWORD_IP_WINDOW_SECONDS,
    ):
        raise HTTPException(status_code=429, detail=RATE_LIMITED_MESSAGE)
    auth_service.reset_password(db, current_user, data.new_password)
    return PasswordResetResponse(message="Password has been reset successfully.")


# ---------------------------------------------------------------------------
# User administration (administrator only)
# ---------------------------------------------------------------------------

@router.get("/users", response_model=UserListResponse)
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    users = user_repo.get_all(db, skip=skip, limit=limit)
    return UserListResponse(users=[UserPublic.model_validate(u) for u in users], total=user_repo.get_count(db))


@router.post("/users", response_model=UserPublic, status_code=201)
def create_user(
    data: UserCreateAdmin,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return auth_service.to_user_public(
        auth_service.create_user(db, username=data.username, full_name=data.full_name, password=data.password, role=data.role)
    )


@router.patch("/users/{user_id}", response_model=UserPublic)
def update_user(
    user_id: UUID,
    data: UserUpdateAdmin,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return auth_service.to_user_public(
        auth_service.update_user(db, user_id, data.model_dump(exclude_unset=True))
    )


# ---------------------------------------------------------------------------
# Projects and membership
# ---------------------------------------------------------------------------

@router.post("/projects", response_model=ProjectPublic, status_code=201)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return auth_service.to_project_public(
        auth_service.create_project(db, data.name, data.description)
    )


@router.get("/projects", response_model=ProjectListResponse)
def list_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    projects = project_repo.get_all(db)
    return ProjectListResponse(projects=[ProjectPublic.model_validate(p) for p in projects], total=len(projects))


@router.post("/projects/{project_id}/members/{user_id}", response_model=MeResponse, status_code=201)
def add_project_member(
    project_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    target = user_repo.get_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    auth_service.ensure_membership(db, user_id, project_id)
    return auth_service.member_of(db, target)


@router.get("/projects/{project_id}/members", response_model=UserListResponse)
def list_project_members(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    project = project_repo.get_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    members = project_repo.users_for_project(db, project_id)
    return UserListResponse(
        users=[UserPublic.model_validate(u) for u in members],
        total=len(members),
    )


@router.delete("/projects/{project_id}/members/{user_id}", response_model=MeResponse)
def remove_project_member(
    project_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    target = user_repo.get_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    removed = project_repo.remove_member(db, project_id, user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Membership not found")
    return auth_service.member_of(db, target)