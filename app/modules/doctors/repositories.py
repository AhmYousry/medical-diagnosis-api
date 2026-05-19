import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import DoctorVerificationStatus
from app.modules.users.models import DoctorProfile


class DoctorProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, profile_id: uuid.UUID) -> DoctorProfile | None:
        result = await self._session.execute(
            select(DoctorProfile)
            .options(selectinload(DoctorProfile.user))
            .where(DoctorProfile.id == profile_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: uuid.UUID) -> DoctorProfile | None:
        result = await self._session.execute(
            select(DoctorProfile)
            .options(selectinload(DoctorProfile.user))
            .where(DoctorProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_license_number(self, license_number: str) -> DoctorProfile | None:
        result = await self._session.execute(
            select(DoctorProfile).where(DoctorProfile.license_number == license_number)
        )
        return result.scalar_one_or_none()

    async def list_by_status(self, status: DoctorVerificationStatus) -> list[DoctorProfile]:
        result = await self._session.execute(
            select(DoctorProfile)
            .options(selectinload(DoctorProfile.user))
            .where(DoctorProfile.verification_status == status)
            .order_by(DoctorProfile.created_at.desc())
        )
        return list(result.scalars().all())

    def add(self, profile: DoctorProfile) -> None:
        self._session.add(profile)

