from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.db.enums import UploadedFileStatus
from app.db.types import pg_enum

if TYPE_CHECKING:
    from app.modules.predictions.models import Prediction
    from app.modules.users.models import User


class UploadedFile(BaseModel):
    __tablename__ = "uploaded_files"
    __table_args__ = (
        Index("ix_uploaded_files_owner_status", "owner_id", "status"),
        Index("ix_uploaded_files_checksum", "checksum_sha256"),
        Index("ix_uploaded_files_created_at", "created_at"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[UploadedFileStatus] = mapped_column(
        pg_enum(UploadedFileStatus, "uploaded_file_status"),
        nullable=False,
        default=UploadedFileStatus.PENDING,
        server_default=UploadedFileStatus.PENDING.value,
    )

    owner: Mapped[User] = relationship("User", back_populates="uploaded_files", lazy="raise")
    predictions: Mapped[list[Prediction]] = relationship("Prediction", back_populates="uploaded_file", lazy="raise")
