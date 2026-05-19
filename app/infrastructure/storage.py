"""
Storage backend — supports local disk and S3-compatible object stores
(AWS S3, Cloudflare R2, MinIO).

Set STORAGE_BACKEND=s3 and the S3_* environment variables to enable S3.
Default is STORAGE_BACKEND=local (files saved to UPLOAD_DIR).
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from app.core.config import settings

# ── helpers ──────────────────────────────────────────────────────────────────


def generate_storage_key(user_id: uuid.UUID, original_filename: str) -> str:
    ext = Path(original_filename).suffix.lower() or ".bin"
    return f"users/{user_id}/{uuid.uuid4().hex}{ext}"


def compute_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def file_size_mb(size_bytes: int) -> float:
    return size_bytes / (1024 * 1024)


# ── public API ────────────────────────────────────────────────────────────────


async def save_file(content: bytes, storage_key: str) -> str:
    """Persist *content* at *storage_key*. Returns the storage key."""
    if settings.storage_backend == "s3":
        return await _s3_save(content, storage_key)
    return await _local_save(content, storage_key)


async def delete_file(storage_key: str) -> None:
    if settings.storage_backend == "s3":
        await _s3_delete(storage_key)
    else:
        await _local_delete(storage_key)


def get_file_url(storage_key: str) -> str:
    """Return a public-facing URL for the file (S3 only).
    For local storage returns an empty string — serve files via the API."""
    if settings.storage_backend == "s3" and settings.s3_public_url:
        return f"{settings.s3_public_url.rstrip('/')}/{storage_key}"
    return ""


# ── local backend ─────────────────────────────────────────────────────────────


def _local_abs(storage_key: str) -> Path:
    return Path(settings.upload_dir) / storage_key


async def _local_save(content: bytes, storage_key: str) -> str:
    path = _local_abs(storage_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    loop = __import__("asyncio").get_event_loop()
    await loop.run_in_executor(None, path.write_bytes, content)
    return storage_key


async def _local_delete(storage_key: str) -> None:
    path = _local_abs(storage_key)
    if path.exists():
        path.unlink()
        _remove_empty_parents(path.parent)


def _remove_empty_parents(path: Path) -> None:
    for parent in path.parents:
        if parent == Path(settings.upload_dir):
            break
        try:
            parent.rmdir()
        except OSError:
            break


# ── S3 backend ────────────────────────────────────────────────────────────────


def _s3_client_kwargs() -> dict:
    kwargs: dict = {
        "region_name": settings.s3_region,
        "aws_access_key_id": settings.s3_access_key_id,
        "aws_secret_access_key": settings.s3_secret_access_key,
    }
    if settings.s3_endpoint_url:  # Cloudflare R2 or MinIO
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    return kwargs


async def _s3_save(content: bytes, storage_key: str) -> str:
    import aioboto3  # type: ignore[import]

    session = aioboto3.Session()
    async with session.client("s3", **_s3_client_kwargs()) as s3:
        await s3.put_object(
            Bucket=settings.s3_bucket_name,
            Key=storage_key,
            Body=content,
        )
    return storage_key


async def _s3_delete(storage_key: str) -> None:
    import aioboto3  # type: ignore[import]

    session = aioboto3.Session()
    async with session.client("s3", **_s3_client_kwargs()) as s3:
        await s3.delete_object(Bucket=settings.s3_bucket_name, Key=storage_key)
