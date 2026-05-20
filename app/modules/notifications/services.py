from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import NotificationType
from app.modules.notifications.models import Notification
from app.modules.notifications.repository import NotificationRepository


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = NotificationRepository(session)

    async def list_for_user(self, user_id: uuid.UUID) -> list[Notification]:
        return await self.repo.list_for_user(user_id)

    async def unread_count(self, user_id: uuid.UUID) -> int:
        return await self.repo.count_unread(user_id)

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> None:
        notification = await self.repo.get_for_user(notification_id, user_id)
        if notification is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )
        await self.repo.mark_read(notification)
        await self.session.commit()

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        updated = await self.repo.mark_all_read(user_id)
        await self.session.commit()
        return updated

    async def create(
        self,
        *,
        recipient_id: uuid.UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> Notification:
        notification = await self.repo.create(
            recipient_id=recipient_id,
            notification_type=notification_type,
            title=title,
            message=message,
            payload=payload,
        )
        await self.session.commit()
        return notification
