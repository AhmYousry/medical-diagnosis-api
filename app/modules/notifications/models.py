from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.db.enums import NotificationStatus, NotificationType
from app.db.types import pg_enum

if TYPE_CHECKING:
    from app.modules.users.models import User


class Notification(BaseModel):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_recipient_status", "recipient_id", "status"),
        Index("ix_notifications_type", "type"),
        Index("ix_notifications_created_at", "created_at"),
    )

    recipient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        "type",
        pg_enum(NotificationType, "notification_type"),
        nullable=False,
        default=NotificationType.SYSTEM,
        server_default=NotificationType.SYSTEM.value,
    )
    status: Mapped[NotificationStatus] = mapped_column(
        pg_enum(NotificationStatus, "notification_status"),
        nullable=False,
        default=NotificationStatus.UNREAD,
        server_default=NotificationStatus.UNREAD.value,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    recipient: Mapped[User] = relationship("User", back_populates="notifications", lazy="raise")
