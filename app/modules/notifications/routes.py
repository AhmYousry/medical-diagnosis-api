from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import get_current_user
from app.modules.notifications.schemas import (
    MessageResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.modules.notifications.services import NotificationService
from app.modules.users.models import User

router = APIRouter()


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list:
    return await NotificationService(session).list_for_user(current_user.id)


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UnreadCountResponse:
    count = await NotificationService(session).unread_count(current_user.id)
    return UnreadCountResponse(unread=count)


@router.post("/{notification_id}/read", response_model=MessageResponse)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    await NotificationService(session).mark_read(notification_id, current_user.id)
    return MessageResponse(message="Notification marked as read")


@router.post("/read-all", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    updated = await NotificationService(session).mark_all_read(current_user.id)
    return MessageResponse(message=f"{updated} notifications marked as read")
