import uuid

from fastapi import APIRouter, Depends, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import get_current_user
from app.modules.uploaded_files.schemas import FileDetailResponse, FileListResponse, UploadResponse
from app.modules.uploaded_files.service import UploadService
from app.modules.users.models import User

router = APIRouter()


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UploadResponse:
    return await UploadService(session).upload(current_user, file)


@router.get("", response_model=FileListResponse)
async def list_files(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FileListResponse:
    return await UploadService(session).list_user_files(current_user)


@router.get("/{file_id}", response_model=FileDetailResponse)
async def get_file(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FileDetailResponse:
    return await UploadService(session).get_file(current_user, file_id)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await UploadService(session).delete_upload(current_user, file_id)
