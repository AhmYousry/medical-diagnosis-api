import hashlib
import uuid
from pathlib import Path

from app.core.config import settings


def generate_storage_key(user_id: uuid.UUID, original_filename: str) -> str:
    ext = Path(original_filename).suffix.lower() or ".bin"
    sanitized = f"{uuid.uuid4().hex}{ext}"
    return f"users/{user_id}/{sanitized}"


def get_absolute_path(storage_key: str) -> Path:
    return Path(settings.upload_dir) / storage_key


async def save_file(content: bytes, storage_key: str) -> str:
    abs_path = get_absolute_path(storage_key)
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    await _async_write(abs_path, content)
    return storage_key


async def delete_file(storage_key: str) -> None:
    abs_path = get_absolute_path(storage_key)
    if abs_path.exists():
        abs_path.unlink()
        _remove_empty_parents(abs_path.parent)


def compute_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def file_size_mb(size_bytes: int) -> float:
    return size_bytes / (1024 * 1024)


async def _async_write(path: Path, content: bytes) -> None:
    loop = __import__("asyncio").get_event_loop()
    await loop.run_in_executor(None, path.write_bytes, content)


def _remove_empty_parents(path: Path) -> None:
    for parent in path.parents:
        if parent == Path(settings.upload_dir):
            break
        try:
            parent.rmdir()
        except OSError:
            break
