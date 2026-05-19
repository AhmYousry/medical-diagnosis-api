import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import UploadedFileStatus
from app.infrastructure.storage import (
    compute_checksum,
    delete_file,
    generate_storage_key,
    save_file,
)
from app.modules.uploaded_files.repository import UploadedFileRepository
from app.modules.uploaded_files.schemas import FileDetailResponse, FileListResponse, UploadResponse
from app.modules.uploaded_files.validation import deep_validate_image, validate_content_type, validate_file_size
from app.modules.users.models import User


class UploadService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = UploadedFileRepository(session)

    async def upload(self, user: User, file: UploadFile) -> UploadResponse:
        content_type = validate_content_type(file.content_type or "application/octet-stream")
        content = await file.read()
        size_bytes = validate_file_size(len(content))
        deep_validate_image(content, content_type)

        checksum = compute_checksum(content)
        storage_key = generate_storage_key(user.id, file.filename or "untitled")

        await save_file(content, storage_key)

        try:
            record = await self._repo.create(
                owner_id=user.id,
                storage_key=storage_key,
                original_filename=file.filename or "untitled",
                content_type=content_type,
                size_bytes=size_bytes,
                checksum_sha256=checksum,
            )
            await self._repo.update_status(record.id, UploadedFileStatus.STORED)
            await self._session.commit()
            await self._session.refresh(record)
        except Exception:
            await self._session.rollback()
            await delete_file(storage_key)
            raise

        return UploadResponse.model_validate(record)

    async def list_user_files(self, user: User) -> FileListResponse:
        records = await self._repo.get_by_owner(user.id)
        return FileListResponse(
            files=[FileDetailResponse.model_validate(r) for r in records],
            total=len(records),
        )

    async def get_file(self, user: User, file_id: uuid.UUID) -> FileDetailResponse:
        record = await self._repo.get_by_id(file_id)
        if record is None or record.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found",
            )
        return FileDetailResponse.model_validate(record)

    async def delete_upload(self, user: User, file_id: uuid.UUID) -> None:
        record = await self._repo.get_by_id(file_id)
        if record is None or record.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found",
            )

        await delete_file(record.storage_key)
        await self._repo.delete(record.id)
        await self._session.commit()
