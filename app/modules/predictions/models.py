from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.db.enums import PredictionLogEvent, PredictionStatus
from app.db.types import pg_enum

if TYPE_CHECKING:
    from app.modules.uploaded_files.models import UploadedFile
    from app.modules.users.models import DoctorProfile, User


class Prediction(BaseModel):
    __tablename__ = "predictions"
    __table_args__ = (
        Index("ix_predictions_requested_by_status", "requested_by_id", "status"),
        Index("ix_predictions_uploaded_file", "uploaded_file_id"),
        Index("ix_predictions_reviewed_by", "reviewed_by_id"),
        Index("ix_predictions_created_at", "created_at"),
    )

    requested_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    uploaded_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("uploaded_files.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("doctor_profiles.id", ondelete="SET NULL"),
    )
    status: Mapped[PredictionStatus] = mapped_column(
        pg_enum(PredictionStatus, "prediction_status"),
        nullable=False,
        default=PredictionStatus.PENDING,
        server_default=PredictionStatus.PENDING.value,
    )
    model_name: Mapped[str | None] = mapped_column(String(150))
    model_version: Mapped[str | None] = mapped_column(String(100))
    predicted_label: Mapped[str | None] = mapped_column(String(255))
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    requested_by: Mapped[User] = relationship(
        "User",
        back_populates="predictions",
        foreign_keys=[requested_by_id],
        lazy="raise",
    )
    uploaded_file: Mapped[UploadedFile] = relationship("UploadedFile", back_populates="predictions", lazy="raise")
    reviewed_by: Mapped[DoctorProfile | None] = relationship(
        "DoctorProfile",
        back_populates="reviewed_predictions",
        lazy="raise",
    )
    logs: Mapped[list[PredictionLog]] = relationship(
        back_populates="prediction",
        cascade="all, delete-orphan",
        lazy="raise",
    )


class PredictionLog(BaseModel):
    __tablename__ = "prediction_logs"
    __table_args__ = (
        Index("ix_prediction_logs_prediction_created_at", "prediction_id", "created_at"),
        Index("ix_prediction_logs_event", "event"),
    )

    prediction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("predictions.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    event: Mapped[PredictionLogEvent] = mapped_column(
        pg_enum(PredictionLogEvent, "prediction_log_event"),
        nullable=False,
    )
    message: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)

    prediction: Mapped[Prediction] = relationship("Prediction", back_populates="logs", lazy="raise")
    actor: Mapped[User | None] = relationship("User", back_populates="prediction_logs", lazy="raise")
