from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_name: str = "Medical Diagnosis API"
    environment: str = "local"
    debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    api_v1_prefix: str = "/api/v1"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "medical_diagnosis"
    postgres_user: str = "medical_user"
    postgres_password: str = Field(default="change-me", repr=False)

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    ai_service_url: str = "http://ai-model:5000"
    ai_retry_max_retries: int = 3
    ai_retry_base_delay: float = 1.0
    ai_request_timeout: float = 120.0

    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    celery_task_soft_time_limit: int = 300
    celery_task_time_limit: int = 330

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_dir: str = Field(default="./logs", validation_alias="LOG_DIR")
    log_max_bytes: int = Field(default=10_485_760, validation_alias="LOG_MAX_BYTES")
    log_backup_count: int = Field(default=10, validation_alias="LOG_BACKUP_COUNT")
    json_logs: bool = Field(default=False, validation_alias="JSON_LOGS")

    cors_origins: list[str] = Field(default=["http://localhost"], validation_alias="CORS_ORIGINS")
    cors_allow_credentials: bool = Field(default=True, validation_alias="CORS_ALLOW_CREDENTIALS")
    cors_expose_headers: list[str] = Field(default=["X-Trace-Id"], validation_alias="CORS_EXPOSE_HEADERS")

    rate_limit_enabled: bool = Field(default=True, validation_alias="RATE_LIMIT_ENABLED")
    rate_limit_max_requests: int = Field(default=100, validation_alias="RATE_LIMIT_MAX_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, validation_alias="RATE_LIMIT_WINDOW_SECONDS")
    rate_limit_auth_max_requests: int = Field(default=20, validation_alias="RATE_LIMIT_AUTH_MAX_REQUESTS")
    rate_limit_auth_window_seconds: int = Field(default=60, validation_alias="RATE_LIMIT_AUTH_WINDOW_SECONDS")

    db_pool_size: int = Field(default=20, validation_alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, validation_alias="DB_MAX_OVERFLOW")
    db_pool_recycle_seconds: int = Field(default=1800, validation_alias="DB_POOL_RECYCLE_SECONDS")
    db_pool_timeout: int = Field(default=30, validation_alias="DB_POOL_TIMEOUT")
    db_echo: bool = Field(default=False, validation_alias="DB_ECHO")

    max_request_body_size: int = Field(default=52_428_800, validation_alias="MAX_REQUEST_BODY_SIZE")

    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 50
    allowed_image_types: list[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/tiff",
        "image/dicom",
    ]

    jwt_secret_key: str = Field(default="change-this-secret-use-at-least-32-characters", repr=False)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.environment != "local" and self.jwt_secret_key == "change-this-secret-use-at-least-32-characters":
            raise ValueError("JWT_SECRET_KEY must be changed outside local environments")
        if len(self.jwt_secret_key) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return self

    @property
    def database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
