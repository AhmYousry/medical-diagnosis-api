from __future__ import annotations

import math
import uuid
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import DoctorVerificationStatus, PredictionLogEvent, UserRole
from app.modules.predictions.models import Prediction, PredictionLog
from app.modules.users.models import DoctorProfile, User


class AdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_users(
        self,
        page: int,
        size: int,
        sort_by: str | None,
        sort_order: str,
        role: UserRole | None,
        status: str | None,
        search: str | None,
    ) -> tuple[list[User], int]:
        query = select(User).options(selectinload(User.doctor_profile))

        if role is not None:
            query = query.where(User.role == role)
        if status is not None:
            query = query.where(User.status == status)
        if search:
            query = query.where(
                or_(User.full_name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%"))
            )

        total_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(total_query)
        total = total_result.scalar_one()

        column = self._resolve_sort_column(User, sort_by, User.created_at)
        order = column.desc() if sort_order == "desc" else column.asc()
        query = query.order_by(order).offset((page - 1) * size).limit(size)

        result = await self._session.execute(query)
        return list(result.scalars().all()), total

    async def list_doctors(
        self,
        page: int,
        size: int,
        sort_by: str | None,
        sort_order: str,
        verification_status: DoctorVerificationStatus | None,
        specialization: str | None,
        search: str | None,
    ) -> tuple[list[DoctorProfile], int]:
        query = (
            select(DoctorProfile)
            .options(selectinload(DoctorProfile.user))
            .join(User, DoctorProfile.user_id == User.id)
        )

        if verification_status is not None:
            query = query.where(DoctorProfile.verification_status == verification_status)
        if specialization:
            query = query.where(DoctorProfile.specialization.ilike(f"%{specialization}%"))
        if search:
            query = query.where(
                or_(
                    User.full_name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                    DoctorProfile.license_number.ilike(f"%{search}%"),
                )
            )

        total_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(total_query)
        total = total_result.scalar_one()

        column = self._resolve_sort_column(DoctorProfile, sort_by, DoctorProfile.created_at)
        order = column.desc() if sort_order == "desc" else column.asc()
        query = query.order_by(order).offset((page - 1) * size).limit(size)

        result = await self._session.execute(query)
        return list(result.scalars().all()), total

    async def list_predictions(
        self,
        page: int,
        size: int,
        sort_by: str | None,
        sort_order: str,
        status_filter: str | None,
        user_id: uuid.UUID | None,
        search: str | None,
    ) -> tuple[list[Prediction], int]:
        query = select(Prediction).options(
            selectinload(Prediction.requested_by),
        )

        if status_filter:
            query = query.where(Prediction.status == status_filter)
        if user_id:
            query = query.where(Prediction.requested_by_id == user_id)
        if search:
            query = query.join(User, Prediction.requested_by_id == User.id).where(
                or_(
                    User.full_name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                )
            )

        total_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(total_query)
        total = total_result.scalar_one()

        column = self._resolve_sort_column(Prediction, sort_by, Prediction.created_at)
        order = column.desc() if sort_order == "desc" else column.asc()
        query = query.order_by(order).offset((page - 1) * size).limit(size)

        result = await self._session.execute(query)
        return list(result.scalars().all()), total

    async def list_prediction_logs(
        self,
        prediction_id: uuid.UUID,
        page: int,
        size: int,
        event_filter: PredictionLogEvent | None,
    ) -> tuple[list[PredictionLog], int]:
        query = (
            select(PredictionLog)
            .options(selectinload(PredictionLog.actor))
            .where(PredictionLog.prediction_id == prediction_id)
        )

        if event_filter is not None:
            query = query.where(PredictionLog.event == event_filter)

        total_query = select(func.count()).select_from(query.subquery())
        total_result = await self._session.execute(total_query)
        total = total_result.scalar_one()

        query = query.order_by(PredictionLog.created_at.desc()).offset((page - 1) * size).limit(size)

        result = await self._session.execute(query)
        return list(result.scalars().all()), total

    async def get_prediction_by_id(self, prediction_id: uuid.UUID) -> Prediction | None:
        result = await self._session.execute(
            select(Prediction)
            .options(selectinload(Prediction.requested_by))
            .where(Prediction.id == prediction_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _resolve_sort_column(model: type, sort_by: str | None, default: Any) -> Any:
        if sort_by is None:
            return default
        column = getattr(model, sort_by, None)
        return column if column is not None else default

    @staticmethod
    def calculate_pages(total: int, size: int) -> int:
        return max(1, math.ceil(total / size))
