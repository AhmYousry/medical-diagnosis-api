from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.db.enums import EmailTokenType
from app.db.types import pg_enum

if TYPE_CHECKING:
    from app.modules.users.models import User


class RefreshToken(BaseModel):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_token_hash", "token_hash", unique=True),
        Index("ix_refresh_tokens_expires_at", "expires_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_token_hash: Mapped[str | None] = mapped_column(String(64))

    user: Mapped[User] = relationship("User", back_populates="refresh_tokens", lazy="raise")


class EmailToken(BaseModel):
    """One-time tokens for email verification and password reset."""

    __tablename__ = "email_tokens"
    __table_args__ = (
        Index("ix_email_tokens_token_hash", "token_hash", unique=True),
        Index("ix_email_tokens_user_id_type", "user_id", "token_type"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    token_type: Mapped[EmailTokenType] = mapped_column(
        pg_enum(EmailTokenType, "email_token_type"),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship("User", lazy="raise")
