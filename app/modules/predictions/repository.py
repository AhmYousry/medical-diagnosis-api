import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import PredictionLogEvent, PredictionStatus
from app.modules.predictions.models import Prediction, PredictionLog


class PredictionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, requested_by_id: uuid.UUID, uploaded_file_id: uuid.UUID) -> Prediction:
        record = Prediction(
            requested_by_id=requested_by_id,
            uploaded_file_id=uploaded_file_id,
            status=PredictionStatus.PENDING,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_by_id(self, prediction_id: uuid.UUID) -> Prediction | None:
        result = await self._session.execute(
            select(Prediction).where(Prediction.id == prediction_id)
        )
        return result.scalar_one_or_none()

    async def get_by_owner(self, owner_id: uuid.UUID) -> list[Prediction]:
        result = await self._session.execute(
            select(Prediction)
            .where(Prediction.requested_by_id == owner_id)
            .order_by(Prediction.created_at.desc())
        )
        return list(result.scalars().all())

    async def mark_processing(self, prediction_id: uuid.UUID) -> None:
        await self._session.execute(
            update(Prediction)
            .where(Prediction.id == prediction_id)
            .values(status=PredictionStatus.PROCESSING)
        )

    async def mark_completed(
        self,
        prediction_id: uuid.UUID,
        predicted_label: str,
        confidence_score: Decimal,
        result: dict | None = None,
        model_name: str | None = None,
        model_version: str | None = None,
    ) -> None:
        await self._session.execute(
            update(Prediction)
            .where(Prediction.id == prediction_id)
            .values(
                status=PredictionStatus.COMPLETED,
                predicted_label=predicted_label,
                confidence_score=confidence_score,
                result=result,
                model_name=model_name,
                model_version=model_version,
                completed_at=datetime.now(UTC),
            )
        )

    async def mark_failed(self, prediction_id: uuid.UUID, error_message: str) -> None:
        await self._session.execute(
            update(Prediction)
            .where(Prediction.id == prediction_id)
            .values(
                status=PredictionStatus.FAILED,
                error_message=error_message,
                completed_at=datetime.now(UTC),
            )
        )

    async def add_log(
        self,
        prediction_id: uuid.UUID,
        event: PredictionLogEvent,
        message: str | None = None,
        actor_user_id: uuid.UUID | None = None,
    ) -> None:
        log = PredictionLog(
            prediction_id=prediction_id,
            event=event,
            message=message,
            actor_user_id=actor_user_id,
        )
        self._session.add(log)
