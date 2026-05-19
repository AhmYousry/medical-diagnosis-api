import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import get_current_user
from app.modules.predictions.schemas import PredictionListResponse, PredictionResponse
from app.modules.predictions.service import PredictionService
from app.modules.users.models import User

router = APIRouter()


@router.post("/{file_id}", response_model=PredictionResponse, status_code=status.HTTP_202_ACCEPTED)
async def predict(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PredictionResponse:
    return await PredictionService(session).predict(current_user, file_id)


@router.get("", response_model=PredictionListResponse)
async def list_predictions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PredictionListResponse:
    return await PredictionService(session).list_predictions(current_user)


@router.get("/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(
    prediction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PredictionResponse:
    return await PredictionService(session).get_prediction(current_user, prediction_id)
