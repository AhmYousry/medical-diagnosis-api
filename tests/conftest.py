from __future__ import annotations

import base64
import tempfile
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient, Response
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from app.core.config import settings
from app.core.dependencies import get_redis
from app.db.base import Base
from app.db.session import get_db_session
from app.main import create_app


def _make_test_app(db_engine, redis_client):
    """Build a minimal FastAPI app for testing (no custom middlewares)."""
    from app.api.v1.router import api_router
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    test_app = FastAPI(title="Test API", version="0.1.0")
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=settings.cors_expose_headers,
    )
    test_app.include_router(api_router, prefix=settings.api_v1_prefix)

    from sqlalchemy.ext.asyncio import async_sessionmaker as _asm

    async def _get_session_override():
        async with _asm(
            bind=db_engine,
            expire_on_commit=False,
            autoflush=False,
        )() as session:
            yield session

    test_app.dependency_overrides[get_db_session] = _get_session_override
    test_app.dependency_overrides[get_redis] = lambda: redis_client
    test_app.state.redis = redis_client

    return test_app


# ---------------------------------------------------------------------------
# Testcontainers – session-scoped (sync)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def postgres_container() -> PostgresContainer:
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def redis_container() -> RedisContainer:
    with RedisContainer("redis:7-alpine") as r:
        yield r


# ---------------------------------------------------------------------------
# Override global settings
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def override_settings(
    postgres_container: PostgresContainer,
    redis_container: RedisContainer,
) -> None:
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    settings.postgres_host = host
    settings.postgres_port = int(port)
    settings.postgres_user = postgres_container.username
    settings.postgres_password = postgres_container.password
    settings.postgres_db = postgres_container.dbname

    settings.redis_host = redis_container.get_container_host_ip()
    settings.redis_port = int(redis_container.get_exposed_port(6379))
    settings.redis_db = 1

    settings.rate_limit_enabled = False
    settings.environment = "test"
    settings.debug = False
    settings.json_logs = False
    settings.upload_dir = tempfile.mkdtemp(prefix="meddiag_")


# ---------------------------------------------------------------------------
# Schema setup – session-scoped (lazy, used by db_engine)
# ---------------------------------------------------------------------------

_engine_schema: Any = None


@pytest.fixture(scope="session")
def db_schema(override_settings: None) -> None:
    """Create all tables once at session level using a sync-style approach."""
    import asyncio

    async def _init():
        engine = create_async_engine(settings.database_url, echo=False)
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_init())
    yield
    asyncio.run(_cleanup())


async def _cleanup():
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ---------------------------------------------------------------------------
# Per-test async engine, session, redis, app, client
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_engine(db_schema: None) -> AsyncIterator[Any]:
    """Fresh engine per test (no pooling, same event loop as test)."""
    engine = create_async_engine(
        settings.database_url,
        poolclass=None,
        echo=False,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def redis_client(override_settings: None) -> AsyncIterator[Redis]:
    r = Redis.from_url(settings.redis_url, decode_responses=True)
    await r.flushdb()
    yield r
    await r.aclose()


@pytest_asyncio.fixture
async def client(
    db_engine,
    redis_client: Redis,
) -> AsyncIterator[AsyncClient]:
    test_app = _make_test_app(db_engine, redis_client)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Test image data
# ---------------------------------------------------------------------------

TEST_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
)


@pytest.fixture
def test_png_bytes() -> bytes:
    return TEST_PNG


@pytest.fixture
def test_image_file(tmp_path: Path) -> Path:
    p = tmp_path / "test.png"
    p.write_bytes(TEST_PNG)
    return p


@pytest.fixture
def upload_dir() -> Path:
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Helper: create a user
# ---------------------------------------------------------------------------

async def _create_user(
    session: AsyncSession,
    email: str,
    password: str,
    full_name: str,
    role: str = "user",
) -> Any:
    from app.modules.auth.security import hash_password_async
    from app.modules.users.models import User

    pw_hash = await hash_password_async(password)
    user = User(email=email, full_name=full_name, password_hash=pw_hash, role=role)
    session.add(user)
    await session.flush()
    return user


def _make_auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _login_user(
    client: AsyncClient,
    email: str,
    password: str,
) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    data = resp.json()
    return data["access_token"]


async def _register_user(
    client: AsyncClient,
    email: str,
    password: str,
    full_name: str = "Test User",
) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Pre-created test user + auth headers
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def regular_user_token(client: AsyncClient) -> str:
    data = await _register_user(client, "regular@test.com", "secret123", "Regular User")
    if "access_token" not in data:
        return await _login_user(client, "regular@test.com", "secret123")
    return data["access_token"]


@pytest_asyncio.fixture
async def admin_user_token(client: AsyncClient, db_engine) -> str:
    data = await _register_user(client, "admin@test.com", "admin1234", "Admin User")
    if "access_token" not in data:
        data = await _login_user(client, "admin@test.com", "admin1234")
    token = data if isinstance(data, str) else data["access_token"]

    from app.db.enums import UserRole
    from app.modules.users.models import User
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    async with AsyncSession(bind=db_engine) as s:
        result = await s.execute(select(User).where(User.email == "admin@test.com"))
        user = result.scalar_one()
        user.role = UserRole.ADMIN
        await s.commit()

    return token


@pytest_asyncio.fixture
async def auth_headers(regular_user_token: str) -> dict[str, str]:
    return _make_auth_header(regular_user_token)


@pytest_asyncio.fixture
async def admin_headers(admin_user_token: str) -> dict[str, str]:
    return _make_auth_header(admin_user_token)


# ---------------------------------------------------------------------------
# Upload a test file and return the file id
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def uploaded_file_id(client: AsyncClient, auth_headers: dict[str, str]) -> uuid.UUID:
    resp = await client.post(
        "/api/v1/uploads/upload",
        files={"file": ("test.png", TEST_PNG, "image/png")},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return uuid.UUID(resp.json()["id"])


# ---------------------------------------------------------------------------
# Mock the AI prediction HTTP endpoint
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _mock_ai_service(request: pytest.FixtureRequest):
    marker = request.node.get_closest_marker("real_ai")
    if marker is not None:
        yield
        return

    import respx
    from httpx import Response

    url = settings.ai_service_url.rstrip("/")
    router = respx.post(f"{url}/")
    router.respond(
        status_code=200,
        json={"Predicted class": "Normal", "confidence": 95.5},
    )
    yield
    respx.clear()


# ---------------------------------------------------------------------------
# Patch Celery's delay() to do nothing by default
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _patch_celery(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "app.modules.predictions.tasks.run_prediction.delay",
        lambda prediction_id: None,
    )


# ---------------------------------------------------------------------------
# pytest-asyncio mode
# ---------------------------------------------------------------------------

def pytest_configure(config: pytest.Config) -> None:
    config.option.asyncio_mode = "auto"
