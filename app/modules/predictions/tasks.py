from __future__ import annotations

import asyncio
import logging
import uuid
from decimal import Decimal

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db.models  # noqa: F401 (ensure all models are loaded before mapper config)

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.ws_manager import publish_prediction_update
from app.db.enums import PredictionLogEvent
from app.infrastructure.ai_client import AIServiceClient, AIServiceError
from app.infrastructure.storage import read_file
from app.modules.predictions.repository import PredictionRepository
from app.modules.uploaded_files.repository import UploadedFileRepository

logger = logging.getLogger(__name__)


def _create_session_factory():
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(bind=engine, expire_on_commit=False)



def _parse_confidence(value: object) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


async def _execute_prediction(db: AsyncSession, prediction_id: uuid.UUID) -> None:
    repo = PredictionRepository(db)
    prediction = await repo.get_by_id(prediction_id)
    if prediction is None:
        raise ValueError(f"Prediction {prediction_id} not found")

    await repo.mark_processing(prediction_id)
    await repo.add_log(prediction_id, PredictionLogEvent.STATUS_CHANGED, "Worker processing")
    await db.flush()

    # notify browser — processing started
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    await publish_prediction_update(redis, str(prediction_id), {
        "prediction_id": str(prediction_id),
        "status": "processing",
    })
    await redis.aclose()

    files_repo = UploadedFileRepository(db)
    uploaded_file = await files_repo.get_by_id(prediction.uploaded_file_id)
    if uploaded_file is None:
        raise ValueError(f"File {prediction.uploaded_file_id} not found")

    image_bytes = await read_file(uploaded_file.storage_key)

    await repo.add_log(
        prediction_id,
        PredictionLogEvent.MODEL_INVOKED,
        f"Calling AI at {settings.ai_service_url}",
    )
    await db.flush()

    ai = AIServiceClient(base_url=settings.ai_service_url, timeout=settings.ai_request_timeout)
    ai_result = await ai.predict(image_bytes, filename=uploaded_file.original_filename)

    predicted_label = ai_result.get("Predicted class", "unknown")
    confidence = _parse_confidence(ai_result.get("confidence"))

    await repo.mark_completed(
        prediction_id,
        predicted_label=predicted_label,
        confidence_score=confidence,
        result=ai_result,
        model_name="CheXNet",
    )
    await repo.add_log(
        prediction_id,
        PredictionLogEvent.COMPLETED,
        f"Prediction: {predicted_label} ({confidence}%)",
    )

    await db.commit()

    # notify browser — completed
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    await publish_prediction_update(redis, str(prediction_id), {
        "prediction_id": str(prediction_id),
        "status": "completed",
        "predicted_label": predicted_label,
        "confidence_score": float(confidence),
        "result": ai_result,
    })
    await redis.aclose()


async def _fail_prediction(db: AsyncSession, prediction_id: uuid.UUID, error: str) -> None:
    repo = PredictionRepository(db)
    prediction = await repo.get_by_id(prediction_id)
    if prediction is None:
        return
    await repo.mark_failed(prediction_id, error)
    await repo.add_log(prediction_id, PredictionLogEvent.FAILED, error)
    await db.commit()

    # notify browser — failed
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    await publish_prediction_update(redis, str(prediction_id), {
        "prediction_id": str(prediction_id),
        "status": "failed",
        "error_message": error,
    })
    await redis.aclose()


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    queue="predictions",
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
)
def run_prediction(self, prediction_id: str) -> None:
    pid = uuid.UUID(prediction_id)

    async def _run(session_factory) -> None:
        async with session_factory() as session:
            await _execute_prediction(session, pid)

    session_factory = _create_session_factory()
    try:
        asyncio.run(_run(session_factory))
    except AIServiceError:
        logger.warning("Retrying prediction %s (attempt %d/4)", prediction_id, self.request.retries + 1)
        raise self.retry()
    except Exception as exc:
        error_msg = str(exc)
        logger.exception("Permanent failure for prediction %s: %s", prediction_id, error_msg)
        try:
            async def _mark_failed(sf) -> None:
                async with sf() as session:
                    await _fail_prediction(session, pid, error_msg)
            asyncio.run(_mark_failed(_create_session_factory()))
        except Exception:
            logger.exception("Failed to mark prediction %s as failed", prediction_id)
