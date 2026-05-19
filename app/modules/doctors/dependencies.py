from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import DoctorVerificationStatus, UserRole
from app.db.session import get_db_session
from app.modules.auth.dependencies import get_current_user
from app.modules.doctors.repositories import DoctorProfileRepository
from app.modules.users.models import DoctorProfile, User


async def get_approved_doctor_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> DoctorProfile:
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor access required",
        )

    profile = await DoctorProfileRepository(session).get_by_user_id(current_user.id)
    if profile is None or profile.verification_status != DoctorVerificationStatus.VERIFIED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor account is not approved",
        )
    return profile

