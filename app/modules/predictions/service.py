import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import PredictionLogEvent
from app.modules.predictions.repository import PredictionRepository
from app.modules.predictions.schemas import PredictionListResponse, PredictionResponse
from app.modules.uploaded_files.repository import UploadedFileRepository
from app.modules.users.models import User

logger = logging.getLogger(__name__)


class PredictionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._predictions = PredictionRepository(session)
        self._files = UploadedFileRepository(session)

    async def predict(self, user: User, file_id: uuid.UUID) -> PredictionResponse:
        uploaded_file = await self._files.get_by_id(file_id)
        if uploaded_file is None or uploaded_file.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found",
            )

        prediction = await self._predictions.create(
            requested_by_id=user.id,
            uploaded_file_id=file_id,
        )
        await self._predictions.add_log(
            prediction.id, PredictionLogEvent.CREATED, "Prediction requested",
        )
        await self._session.flush()

        from app.modules.predictions.tasks import run_prediction
        run_prediction.delay(str(prediction.id))

        await self._predictions.add_log(
            prediction.id,
            PredictionLogEvent.STATUS_CHANGED,
            "Enqueued for background processing",
        )

        await self._session.commit()
        await self._session.refresh(prediction)
        return PredictionResponse.model_validate(prediction)

    async def list_predictions(self, user: User) -> PredictionListResponse:
        records = await self._predictions.get_by_owner(user.id)
        return PredictionListResponse(
            predictions=[PredictionResponse.model_validate(r) for r in records],
            total=len(records),
        )

    async def get_prediction(self, user: User, prediction_id: uuid.UUID) -> PredictionResponse:
        record = await self._predictions.get_by_id(prediction_id)
        if record is None or record.requested_by_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prediction not found",
            )
        return PredictionResponse.model_validate(record)



