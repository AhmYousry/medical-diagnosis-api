from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import NotificationStatus, NotificationType
from app.modules.notifications.models import Notification


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        recipient_id: uuid.UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> Notification:
        notification = Notification(
            recipient_id=recipient_id,
            notification_type=notification_type,
            title=title,
            message=message,
            payload=payload,
        )
        self.session.add(notification)
        await self.session.flush()
        return notification

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        limit: int = 100,
    ) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.recipient_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_for_user(
        self,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Notification | None:
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_unread(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count(Notification.id))
            .where(
                Notification.recipient_id == user_id,
                Notification.status == NotificationStatus.UNREAD,
            )
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def mark_read(self, notification: Notification) -> None:
        if notification.status == NotificationStatus.READ:
            return
        notification.status = NotificationStatus.READ
        notification.read_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        stmt = (
            update(Notification)
            .where(
                Notification.recipient_id == user_id,
                Notification.status == NotificationStatus.UNREAD,
            )
            .values(status=NotificationStatus.READ, read_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0
