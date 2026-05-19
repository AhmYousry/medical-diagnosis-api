import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import UserRole
from app.db.session import get_db_session
from app.modules.auth.dependencies import require_roles
from app.modules.doctors.dependencies import get_approved_doctor_profile
from app.modules.doctors.schemas import (
    DoctorProfileResponse,
    DoctorRegistrationResponse,
    DoctorRegisterRequest,
    DoctorRejectionRequest,
)
from app.modules.doctors.services import DoctorService
from app.modules.users.models import DoctorProfile, User

router = APIRouter()


@router.post("/register", response_model=DoctorRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_doctor(
    payload: DoctorRegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> DoctorRegistrationResponse:
    return await DoctorService(session).register_doctor(payload)


@router.get("/me", response_model=DoctorProfileResponse)
async def get_my_doctor_profile(
    doctor_profile: DoctorProfile = Depends(get_approved_doctor_profile),
) -> DoctorProfile:
    return doctor_profile


@router.get("/admin/pending", response_model=list[DoctorProfileResponse])
async def list_pending_doctors(
    _: User = Depends(require_roles(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session),
) -> list[DoctorProfile]:
    return await DoctorService(session).list_pending_doctors()


@router.post("/admin/{profile_id}/approve", response_model=DoctorProfileResponse)
async def approve_doctor(
    profile_id: uuid.UUID,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session),
) -> DoctorProfile:
    return await DoctorService(session).approve_doctor(profile_id)


@router.post("/admin/{profile_id}/reject", response_model=DoctorProfileResponse)
async def reject_doctor(
    profile_id: uuid.UUID,
    payload: DoctorRejectionRequest,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session),
) -> DoctorProfile:
    return await DoctorService(session).reject_doctor(profile_id, payload)

