from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import DoctorVerificationStatus, PredictionLogEvent, UserRole
from app.db.session import get_db_session
from app.modules.admin.schemas import (
    AdminDoctorListResponse,
    AdminPredictionListResponse,
    AdminPredictionResponse,
    AdminUserListResponse,
    PaginationParams,
    PredictionLogListResponse,
)
from app.modules.admin.service import AdminService
from app.modules.auth.dependencies import require_roles
from app.modules.users.models import User

router = APIRouter(dependencies=[Depends(require_roles(UserRole.ADMIN))])


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    pagination: PaginationParams = Depends(),
    role: UserRole | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None, min_length=2),
    session: AsyncSession = Depends(get_db_session),
) -> AdminUserListResponse:
    return await AdminService(session).list_users(
        pagination=pagination, role=role, status=status, search=search
    )


@router.get("/doctors", response_model=AdminDoctorListResponse)
async def list_doctors(
    pagination: PaginationParams = Depends(),
    verification_status: DoctorVerificationStatus | None = Query(None),
    specialization: str | None = Query(None, min_length=2),
    search: str | None = Query(None, min_length=2),
    session: AsyncSession = Depends(get_db_session),
) -> AdminDoctorListResponse:
    return await AdminService(session).list_doctors(
        pagination=pagination,
        verification_status=verification_status,
        specialization=specialization,
        search=search,
    )


@router.get("/predictions", response_model=AdminPredictionListResponse)
async def list_predictions(
    pagination: PaginationParams = Depends(),
    status_filter: str | None = Query(None, alias="status"),
    user_id: uuid.UUID | None = Query(None),
    search: str | None = Query(None, min_length=2),
    session: AsyncSession = Depends(get_db_session),
) -> AdminPredictionListResponse:
    return await AdminService(session).list_predictions(
        pagination=pagination,
        status_filter=status_filter,
        user_id=user_id,
        search=search,
    )


@router.get("/predictions/{prediction_id}", response_model=AdminPredictionResponse)
async def get_prediction(
    prediction_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AdminPredictionResponse:
    return await AdminService(session).get_prediction(prediction_id)


@router.get("/predictions/{prediction_id}/logs", response_model=PredictionLogListResponse)
async def list_prediction_logs(
    prediction_id: uuid.UUID,
    pagination: PaginationParams = Depends(),
    event: PredictionLogEvent | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
) -> PredictionLogListResponse:
    return await AdminService(session).list_prediction_logs(
        prediction_id=prediction_id,
        pagination=pagination,
        event=event,
    )
