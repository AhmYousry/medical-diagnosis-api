from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.middleware.logging_middleware import RequestLoggingMiddleware
from app.core.middleware.rate_limit import RateLimitMiddleware
from app.core.middleware.security_headers import SecurityHeadersMiddleware
from app.core.redis import create_redis_client
from app.db.session import engine

import app.db.models  # noqa: F401 (ensure all models are loaded before mapper config)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "Starting up — environment=%s debug=%s",
        settings.environment,
        settings.debug,
    )
    app.state.redis = create_redis_client()
    yield
    logger.info("Shutting down")
    await cast(Redis, app.state.redis).aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    setup_logging()

    _is_local = settings.environment == "local"

    app = FastAPI(
        title=settings.project_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if _is_local else None,
        redoc_url="/redoc" if _is_local else None,
        openapi_url="/openapi.json" if _is_local else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=settings.cors_expose_headers,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    logger.info("API initialized — prefix=%s", settings.api_v1_prefix)
    return app


app = create_app()
