import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PredictionResponse(BaseModel):
    id: uuid.UUID
    uploaded_file_id: uuid.UUID
    requested_by_id: uuid.UUID
    status: str
    model_name: str | None
    model_version: str | None
    predicted_label: str | None
    confidence_score: Decimal | None
    result: dict | None
    error_message: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PredictionListResponse(BaseModel):
    predictions: list[PredictionResponse]
    total: int
