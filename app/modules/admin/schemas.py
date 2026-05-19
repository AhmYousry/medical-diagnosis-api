from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import (
    DoctorVerificationStatus,
    PredictionLogEvent,
    UserRole,
    UserStatus,
)


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    sort_by: str | None = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    size: int
    pages: int


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    status: UserStatus
    is_email_verified: bool
    created_at: datetime
    updated_at: datetime

    doctor_profile_id: uuid.UUID | None = None
    doctor_verification_status: DoctorVerificationStatus | None = None
    doctor_specialization: str | None = None


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]
    total: int
    page: int
    size: int
    pages: int


class AdminDoctorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    full_name: str
    license_number: str
    specialization: str
    clinic_name: str | None
    bio: str | None
    verification_status: DoctorVerificationStatus
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime


class AdminDoctorListResponse(BaseModel):
    items: list[AdminDoctorResponse]
    total: int
    page: int
    size: int
    pages: int


class AdminPredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    uploaded_file_id: uuid.UUID
    requested_by_id: uuid.UUID
    requested_by_email: str | None = None
    requested_by_name: str | None = None
    status: str
    model_name: str | None
    model_version: str | None
    predicted_label: str | None
    confidence_score: Decimal | None
    result: dict[str, Any] | None
    error_message: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminPredictionListResponse(BaseModel):
    items: list[AdminPredictionResponse]
    total: int
    page: int
    size: int
    pages: int


class PredictionLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prediction_id: uuid.UUID
    actor_user_id: uuid.UUID | None
    actor_name: str | None = None
    event: PredictionLogEvent
    message: str | None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")
    created_at: datetime


class PredictionLogListResponse(BaseModel):
    items: list[PredictionLogResponse]
    total: int
    page: int
    size: int
    pages: int
