from datetime import UTC, datetime
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import UserRole, UserStatus
from app.modules.auth.models import RefreshToken
from app.modules.auth.repositories import RefreshTokenRepository, UserRepository
from app.modules.auth.schemas import AuthResponse, LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.modules.auth.security import hash_password_async, verify_password_async
from app.modules.auth.tokens import create_access_token, create_refresh_token, hash_refresh_token
from app.modules.users.models import User

DUMMY_PASSWORD_HASH = "$2b$12$C6UzMDM.H6dfI/f/IKcEe.6ymEOpWl2kV4XWLuQ6K5Z7rQJp6fQh6"


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)

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

        response = await self.issue_tokens(user)
        await self._session.commit()
        return response

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
