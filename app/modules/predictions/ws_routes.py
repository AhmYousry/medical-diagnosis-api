"""
WebSocket endpoint: ws://.../api/v1/predict/{prediction_id}/ws?token=<access_token>
"""
from __future__ import annotations

import json
import logging
import uuid

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.ws_manager import ws_manager
from app.db.session import get_db_session_ctx
from app.modules.auth.repositories import UserRepository
from app.modules.auth.tokens import decode_access_token
from app.modules.predictions.repository import PredictionRepository

logger = logging.getLogger(__name__)
ws_router = APIRouter()


async def _authenticate_ws(token: str) -> uuid.UUID:
    """Validate JWT and return user_id. Raises WebSocketException on failure."""
    try:
        payload = decode_access_token(token)
        return uuid.UUID(str(payload.get("sub", "")))
    except (jwt.PyJWTError, ValueError) as exc:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token") from exc


@ws_router.websocket("/{prediction_id}/ws")
async def prediction_ws(prediction_id: uuid.UUID, websocket: WebSocket) -> None:
    # ── 1. Auth via query param (browsers can't set WS headers) ──
    token = websocket.query_params.get("token", "")
    user_id = await _authenticate_ws(token)

    # ── 2. Verify prediction belongs to this user ──────────────────
    async with get_db_session_ctx() as session:
        prediction = await PredictionRepository(session).get_by_id(prediction_id)
        if prediction is None or prediction.requested_by_id != user_id:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Not found")

        # If already terminal — send final state immediately and close
        if prediction.status in ("completed", "failed"):
            await websocket.accept()
            await websocket.send_text(json.dumps({
                "prediction_id": str(prediction_id),
                "status": prediction.status,
                "predicted_label": prediction.predicted_label,
                "confidence_score": float(prediction.confidence_score) if prediction.confidence_score else None,
                "result": prediction.result,
                "error_message": prediction.error_message,
            }))
            await websocket.close()
            return

    # ── 3. Subscribe to Redis and stream updates ───────────────────
    redis = websocket.app.state.redis
    await websocket.accept()
    logger.info("WS opened prediction=%s user=%s", prediction_id, user_id)

    try:
        await ws_manager.listen(redis, str(prediction_id), websocket)
    except WebSocketDisconnect:
        logger.info("WS closed prediction=%s", prediction_id)
    finally:
        ws_manager.disconnect(str(prediction_id), websocket)
