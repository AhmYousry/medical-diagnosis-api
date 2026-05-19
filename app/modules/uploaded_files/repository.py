import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import UploadedFileStatus
from app.modules.uploaded_files.models import UploadedFile


class UploadedFileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        owner_id: uuid.UUID,
        storage_key: str,
        original_filename: str,
        content_type: str,
        size_bytes: int,
        checksum_sha256: str | None = None,
    ) -> UploadedFile:
        record = UploadedFile(
            owner_id=owner_id,
            storage_key=storage_key,
            original_filename=original_filename,
            content_type=content_type,
            size_bytes=size_bytes,
            checksum_sha256=checksum_sha256,
            status=UploadedFileStatus.PENDING,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_by_id(self, file_id: uuid.UUID) -> UploadedFile | None:
        result = await self._session.execute(
            select(UploadedFile).where(UploadedFile.id == file_id)
        )
        return result.scalar_one_or_none()

    async def get_by_owner(self, owner_id: uuid.UUID) -> list[UploadedFile]:
        result = await self._session.execute(
            select(UploadedFile)
            .where(UploadedFile.owner_id == owner_id)
            .order_by(UploadedFile.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(self, file_id: uuid.UUID, status: UploadedFileStatus) -> None:
        await self._session.execute(
            update(UploadedFile)
            .where(UploadedFile.id == file_id)
            .values(status=status)
        )

    async def delete(self, file_id: uuid.UUID) -> UploadedFile | None:
        record = await self.get_by_id(file_id)
        if record is not None:
            await self._session.delete(record)
            await self._session.flush()
        return record
