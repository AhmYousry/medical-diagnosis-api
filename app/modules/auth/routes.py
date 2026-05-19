from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import get_current_user, require_roles
from app.db.enums import UserRole
from app.modules.auth.schemas import (
    AuthResponse,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.services import AuthService
from app.modules.doctors.dependencies import get_approved_doctor_profile
from app.modules.users.models import DoctorProfile
from app.modules.users.models import User

router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    return await AuthService(session).register(payload)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    return await AuthService(session).login(payload)


@router.post("/token", response_model=TokenResponse)
async def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    auth_response = await AuthService(session).login(
        LoginRequest(email=form_data.username, password=form_data.password)
    )
    return TokenResponse(
        access_token=auth_response.access_token,
        refresh_token=auth_response.refresh_token,
        expires_at=auth_response.expires_at,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    return await AuthService(session).refresh(payload.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/admin", response_model=UserResponse)
async def admin_only(current_user: User = Depends(require_roles(UserRole.ADMIN))) -> User:
    return current_user


@router.get("/doctor", response_model=UserResponse)
async def approved_doctor_only(
    doctor_profile: DoctorProfile = Depends(get_approved_doctor_profile),
) -> User:
    return doctor_profile.user
