from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.enums import EmailTokenType, UserRole, UserStatus
from app.infrastructure.email import (
    build_password_reset_email,
    build_verification_email,
    send_email,
)
from app.modules.auth.models import EmailToken, RefreshToken
from app.modules.auth.repositories import (
    EmailTokenRepository,
    RefreshTokenRepository,
    UserRepository,
)
from app.modules.auth.schemas import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    ResendVerificationRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.modules.auth.security import hash_password_async, verify_password_async
from app.modules.auth.tokens import create_access_token, create_refresh_token, hash_refresh_token
from app.modules.users.models import User

DUMMY_PASSWORD_HASH = "$2b$12$C6UzMDM.H6dfI/f/IKcEe.6ymEOpWl2kV4XWLuQ6K5Z7rQJp6fQh6"


def _generate_token() -> tuple[str, str]:
    """Return (plain_token, sha256_hex_hash)."""
    plain = secrets.token_urlsafe(48)
    digest = hashlib.sha256(plain.encode()).hexdigest()
    return plain, digest


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)
        self._email_tokens = EmailTokenRepository(session)

    # ── register ──────────────────────────────────────────────────────────────

    async def register(self, payload: RegisterRequest) -> AuthResponse:
        existing_user = await self._users.get_by_email(payload.email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            )

        user = User(
            email=payload.email,
            full_name=payload.full_name,
            password_hash=await hash_password_async(payload.password),
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        self._users.add(user)

        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            ) from exc

        # Send verification email (best-effort — non-blocking)
        plain_token, token_hash = _generate_token()
        self._email_tokens.add(
            EmailToken(
                user_id=user.id,
                token_hash=token_hash,
                token_type=EmailTokenType.EMAIL_VERIFICATION,
                expires_at=datetime.now(UTC) + timedelta(hours=settings.email_verification_expire_hours),
            )
        )

        response = await self.issue_tokens(user)
        await self._session.commit()

        verify_url = f"{settings.frontend_url}/verify-email?token={plain_token}"
        await send_email(
            to=user.email,
            subject="Verify your MedScan AI account",
            html=build_verification_email(user.full_name, verify_url),
        )
        return response

    # ── login ─────────────────────────────────────────────────────────────────

    async def login(self, payload: LoginRequest) -> AuthResponse:
        user = await self._users.get_by_email(payload.email)
        password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
        is_valid_password = await verify_password_async(payload.password, password_hash)
        if user is None or not is_valid_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not active",
            )

        response = await self.issue_tokens(user)
        await self._session.commit()
        return response

    # ── token refresh ─────────────────────────────────────────────────────────

    async def refresh(self, refresh_token: str) -> TokenResponse:
        token_hash = hash_refresh_token(refresh_token)
        stored_token = await self._refresh_tokens.get_active_by_hash_for_update(token_hash)
        if stored_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        user = await self._users.get_by_id(stored_token.user_id)
        if user is None or user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        access_token, access_expires_at = create_access_token(user.id, user.role)
        new_refresh_token, new_refresh_token_hash, refresh_expires_at = create_refresh_token()

        stored_token.revoked_at = datetime.now(UTC)
        stored_token.replaced_by_token_hash = new_refresh_token_hash
        self._refresh_tokens.add(
            RefreshToken(
                user_id=user.id,
                token_hash=new_refresh_token_hash,
                expires_at=refresh_expires_at,
            )
        )

        await self._session.commit()
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_at=access_expires_at,
        )

    # ── email verification ────────────────────────────────────────────────────

    async def verify_email(self, payload: VerifyEmailRequest) -> None:
        token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
        email_token = await self._email_tokens.get_active(token_hash, EmailTokenType.EMAIL_VERIFICATION)
        if email_token is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        user = await self._users.get_by_id(email_token.user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        user.is_email_verified = True
        email_token.used_at = datetime.now(UTC)
        await self._session.commit()

    async def resend_verification(self, payload: ResendVerificationRequest) -> None:
        user = await self._users.get_by_email(payload.email)
        # Always return 200 to prevent email enumeration
        if user is None or user.is_email_verified:
            return

        await self._email_tokens.invalidate_existing(user.id, EmailTokenType.EMAIL_VERIFICATION)
        plain_token, token_hash = _generate_token()
        self._email_tokens.add(
            EmailToken(
                user_id=user.id,
                token_hash=token_hash,
                token_type=EmailTokenType.EMAIL_VERIFICATION,
                expires_at=datetime.now(UTC) + timedelta(hours=settings.email_verification_expire_hours),
            )
        )
        await self._session.commit()

        verify_url = f"{settings.frontend_url}/verify-email?token={plain_token}"
        await send_email(
            to=user.email,
            subject="Verify your MedScan AI account",
            html=build_verification_email(user.full_name, verify_url),
        )

    # ── password reset ────────────────────────────────────────────────────────

    async def forgot_password(self, payload: ForgotPasswordRequest) -> None:
        user = await self._users.get_by_email(payload.email)
        # Always return 200 to prevent email enumeration
        if user is None or user.status != UserStatus.ACTIVE:
            return

        await self._email_tokens.invalidate_existing(user.id, EmailTokenType.PASSWORD_RESET)
        plain_token, token_hash = _generate_token()
        self._email_tokens.add(
            EmailToken(
                user_id=user.id,
                token_hash=token_hash,
                token_type=EmailTokenType.PASSWORD_RESET,
                expires_at=datetime.now(UTC) + timedelta(hours=settings.password_reset_expire_hours),
            )
        )
        await self._session.commit()

        reset_url = f"{settings.frontend_url}/reset-password?token={plain_token}"
        await send_email(
            to=user.email,
            subject="Reset your MedScan AI password",
            html=build_password_reset_email(user.full_name, reset_url),
        )

    async def reset_password(self, payload: ResetPasswordRequest) -> None:
        token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
        email_token = await self._email_tokens.get_active(token_hash, EmailTokenType.PASSWORD_RESET)
        if email_token is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        user = await self._users.get_by_id(email_token.user_id)
        if user is None or user.status != UserStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        user.password_hash = await hash_password_async(payload.new_password)
        email_token.used_at = datetime.now(UTC)

        # Revoke all existing refresh tokens for security
        from sqlalchemy import update
        from app.modules.auth.models import RefreshToken
        await self._session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )

        await self._session.commit()

    # ── helpers ───────────────────────────────────────────────────────────────

    async def issue_tokens(self, user: User) -> AuthResponse:
        access_token, access_expires_at = create_access_token(user.id, user.role)
        refresh_token, refresh_token_hash, refresh_expires_at = create_refresh_token()
        self._refresh_tokens.add(
            RefreshToken(
                user_id=user.id,
                token_hash=refresh_token_hash,
                expires_at=refresh_expires_at,
            )
        )
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=access_expires_at,
            user=UserResponse.model_validate(user),
        )
