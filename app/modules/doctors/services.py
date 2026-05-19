import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import DoctorVerificationStatus, UserRole, UserStatus
from app.modules.auth.repositories import UserRepository
from app.modules.auth.schemas import UserResponse
from app.modules.auth.security import hash_password_async
from app.modules.auth.services import AuthService
from app.modules.doctors.repositories import DoctorProfileRepository
from app.modules.doctors.schemas import (
    DoctorProfileResponse,
    DoctorRegistrationResponse,
    DoctorRegisterRequest,
    DoctorRejectionRequest,
)
from app.modules.users.models import DoctorProfile, User


class DoctorService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._profiles = DoctorProfileRepository(session)

    async def register_doctor(self, payload: DoctorRegisterRequest) -> DoctorRegistrationResponse:
        existing_user = await self._users.get_by_email(payload.email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            )

        existing_profile = await self._profiles.get_by_license_number(payload.license_number)
        if existing_profile is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="License number is already registered",
            )

        user = User(
            email=payload.email,
            full_name=payload.full_name,
            password_hash=await hash_password_async(payload.password),
            role=UserRole.DOCTOR,
            status=UserStatus.ACTIVE,
        )

        try:
            self._users.add(user)
            await self._session.flush()

            profile = DoctorProfile(
                user_id=user.id,
                license_number=payload.license_number,
                specialization=payload.specialization,
                clinic_name=payload.clinic_name,
                bio=payload.bio,
                verification_status=DoctorVerificationStatus.PENDING,
            )
            self._profiles.add(profile)
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Doctor registration conflicts with an existing account",
            ) from exc

        auth_response = await AuthService(self._session).issue_tokens(user)
        await self._session.commit()
        return DoctorRegistrationResponse(
            access_token=auth_response.access_token,
            refresh_token=auth_response.refresh_token,
            expires_at=auth_response.expires_at,
            user=UserResponse.model_validate(user),
            doctor_profile=DoctorProfileResponse.model_validate(profile),
        )

    async def list_pending_doctors(self) -> list[DoctorProfile]:
        return await self._profiles.list_by_status(DoctorVerificationStatus.PENDING)

    async def approve_doctor(self, profile_id: uuid.UUID) -> DoctorProfile:
        profile = await self._get_profile_or_404(profile_id)
        profile.verification_status = DoctorVerificationStatus.VERIFIED
        profile.rejection_reason = None
        await self._session.commit()
        await self._session.refresh(profile)
        return profile

    async def reject_doctor(self, profile_id: uuid.UUID, payload: DoctorRejectionRequest) -> DoctorProfile:
        profile = await self._get_profile_or_404(profile_id)
        profile.verification_status = DoctorVerificationStatus.REJECTED
        profile.rejection_reason = payload.rejection_reason
        await self._session.commit()
        await self._session.refresh(profile)
        return profile

    async def _get_profile_or_404(self, profile_id: uuid.UUID) -> DoctorProfile:
        profile = await self._profiles.get_by_id(profile_id)
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor profile not found",
            )
        return profile
