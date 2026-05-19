import magic
from fastapi import HTTPException, status

from app.core.config import settings
from app.infrastructure.storage import file_size_mb

MAX_SIZE_BYTES = settings.max_upload_size_mb * 1024 * 1024


def validate_content_type(content_type: str) -> str:
    if content_type not in settings.allowed_image_types:
        allowed = ", ".join(settings.allowed_image_types)
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{content_type}'. Allowed: {allowed}",
        )
    return content_type


def validate_file_size(size_bytes: int) -> int:
    if size_bytes > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.max_upload_size_mb}MB "
                   f"(got {file_size_mb(size_bytes):.1f}MB)",
        )
    return size_bytes


def deep_validate_image(content: bytes, declared_type: str) -> None:
    detected = magic.from_buffer(content, mime=True)
    if detected != declared_type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Declared content type '{declared_type}' does not match "
                   f"detected type '{detected}'",
        )
