import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UploadResponse(BaseModel):
    id: uuid.UUID
    storage_key: str
    original_filename: str
    content_type: str
    size_bytes: int
    checksum_sha256: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FileDetailResponse(BaseModel):
    id: uuid.UUID
    storage_key: str
    original_filename: str
    content_type: str
    size_bytes: int
    checksum_sha256: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FileListResponse(BaseModel):
    files: list[FileDetailResponse]
    total: int
