from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import NotificationStatus, NotificationType


class NotificationResponse(BaseModel):
    # populate_by_name lets us read from the Python attribute name
    # (notification_type) while presenting it as `type` in JSON to the client.
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    title: str
    message: str
    type: NotificationType = Field(
        validation_alias="notification_type",
        serialization_alias="type",
    )
    status: NotificationStatus
    payload: dict[str, Any] | None = None
    read_at: datetime | None = None
    created_at: datetime


class UnreadCountResponse(BaseModel):
    unread: int


class MessageResponse(BaseModel):
    message: str
