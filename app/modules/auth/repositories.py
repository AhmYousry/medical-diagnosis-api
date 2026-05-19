from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import RefreshToken
from app.modules.users.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    def add(self, user: User) -> None:
        self._session.add(user)


    async def count_active(self) -> int:
        from sqlalchemy import func, select

        from app.db.enums import UserStatus

        result = await self._session.execute(
            select(func.count()).select_from(
                select(User).where(User.status == UserStatus.ACTIVE).subquery()
            )
        )
        return result.scalar_one() or 0


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self._session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(UTC),
            )
        )
        return result.scalar_one_or_none()

    async def get_active_by_hash_for_update(self, token_hash: str) -> RefreshToken | None:
        result = await self._session.execute(
            select(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(UTC),
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    def add(self, refresh_token: RefreshToken) -> None:
        self._session.add(refresh_token)
