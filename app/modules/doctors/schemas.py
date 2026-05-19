import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.enums import DoctorVerificationStatus
from app.modules.auth.schemas import TokenResponse, UserResponse


class DoctorRegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=1, max_length=255)
    license_number: str = Field(min_length=3, max_length=100)
    specialization: str = Field(min_length=2, max_length=150)
    clinic_name: str | None = Field(default=None, max_length=255)
    bio: str | None = Field(default=None, max_length=5000)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("license_number")
    @classmethod
    def normalize_license_number(cls, value: str) -> str:
        return value.strip().upper()


class DoctorRejectionRequest(BaseModel):
    rejection_reason: str = Field(min_length=5, max_length=2000)


class DoctorProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    license_number: str
    specialization: str
    clinic_name: str | None
    bio: str | None
    verification_status: DoctorVerificationStatus
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime


class DoctorRegistrationResponse(TokenResponse):
    user: UserResponse
    doctor_profile: DoctorProfileResponse
