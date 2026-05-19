from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, false
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.db.enums import DoctorVerificationStatus, UserRole, UserStatus
from app.db.types import pg_enum

if TYPE_CHECKING:
    from app.modules.auth.models import RefreshToken
    from app.modules.notifications.models import Notification
    from app.modules.predictions.models import Prediction, PredictionLog
    from app.modules.uploaded_files.models import UploadedFile


class User(BaseModel):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_role_status", "role", "status"),
        Index("ix_users_created_at", "created_at"),
    )

    email: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        pg_enum(UserRole, "user_role"),
        nullable=False,
        default=UserRole.USER,
        server_default=UserRole.USER.value,
    )
    status: Mapped[UserStatus] = mapped_column(
        pg_enum(UserStatus, "user_status"),
        nullable=False,
        default=UserStatus.ACTIVE,
        server_default=UserStatus.ACTIVE.value,
    )
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )

    doctor_profile: Mapped[DoctorProfile | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="raise",
        uselist=False,
    )
    uploaded_files: Mapped[list[UploadedFile]] = relationship("UploadedFile", back_populates="owner", lazy="raise")
    predictions: Mapped[list[Prediction]] = relationship(
        "Prediction",
        back_populates="requested_by",
        foreign_keys="Prediction.requested_by_id",
        lazy="raise",
    )
    prediction_logs: Mapped[list[PredictionLog]] = relationship("PredictionLog", back_populates="actor", lazy="raise")
    notifications: Mapped[list[Notification]] = relationship("Notification", back_populates="recipient", lazy="raise")
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="raise",
    )


class DoctorProfile(BaseModel):
    __tablename__ = "doctor_profiles"
    __table_args__ = (
        Index("ix_doctor_profiles_specialization", "specialization"),
        Index("ix_doctor_profiles_verification_status", "verification_status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    license_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    specialization: Mapped[str] = mapped_column(String(150), nullable=False)
    clinic_name: Mapped[str | None] = mapped_column(String(255))
    bio: Mapped[str | None] = mapped_column(Text)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[DoctorVerificationStatus] = mapped_column(
        pg_enum(DoctorVerificationStatus, "doctor_verification_status"),
        nullable=False,
        default=DoctorVerificationStatus.PENDING,
        server_default=DoctorVerificationStatus.PENDING.value,
    )

    user: Mapped[User] = relationship("User", back_populates="doctor_profile", lazy="raise")
    reviewed_predictions: Mapped[list[Prediction]] = relationship("Prediction", back_populates="reviewed_by", lazy="raise")
