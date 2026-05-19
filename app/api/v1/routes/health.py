from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_redis
from app.db.session import engine, get_db_session
from app.modules.auth.repositories import UserRepository

_startup_time = datetime.now(UTC)

router = APIRouter()


@router.get("")
async def health_check(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> dict:
    db_ok = redis_ok = False
    db_error = redis_error = None
    user_count = 0

    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
        count = await UserRepository(db).count_active()
        user_count = count
    except Exception as exc:
        db_error = str(exc)

    try:
        await redis.ping()
        redis_ok = True
    except Exception as exc:
        redis_error = str(exc)

    uptime = (datetime.now(UTC) - _startup_time).total_seconds()
    overall = "healthy" if db_ok and redis_ok else "degraded"

    return {
        "status": overall,
        "version": "0.1.0",
        "uptime_seconds": round(uptime, 1),
        "started_at": _startup_time.isoformat(),
        "environment": settings.environment,
        "dependencies": {
            "database": {"status": "ok" if db_ok else "error", "error": db_error},
            "redis": {"status": "ok" if redis_ok else "error", "error": redis_error},
        },
        "active_users": user_count,
    }


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    await redis.ping()
    return {"status": "ok"}
