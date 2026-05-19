from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import DoctorVerificationStatus, PredictionLogEvent, UserRole
from app.modules.admin.repositories import AdminRepository
from app.modules.admin.schemas import (
    AdminDoctorListResponse,
    AdminDoctorResponse,
    AdminPredictionListResponse,
    AdminPredictionResponse,
    AdminUserListResponse,
    AdminUserResponse,
    PaginationParams,
    PredictionLogListResponse,
    PredictionLogResponse,
)


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AdminRepository(session)

    async def list_users(
        self,
        pagination: PaginationParams,
        role: UserRole | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> AdminUserListResponse:
        users, total = await self._repo.list_users(
            page=pagination.page,
            size=pagination.size,
            sort_by=pagination.sort_by,
            sort_order=pagination.sort_order,
            role=role,
            status=status,
            search=search,
        )

        items = [
            AdminUserResponse(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                role=u.role,
                status=u.status,
                is_email_verified=u.is_email_verified,
                created_at=u.created_at,
                updated_at=u.updated_at,
                doctor_profile_id=u.doctor_profile.id if u.doctor_profile else None,
                doctor_verification_status=u.doctor_profile.verification_status
                if u.doctor_profile
                else None,
                doctor_specialization=u.doctor_profile.specialization
                if u.doctor_profile
                else None,
            )
            for u in users
        ]

        return AdminUserListResponse(
            items=items,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=self._repo.calculate_pages(total, pagination.size),
        )

    async def list_doctors(
        self,
        pagination: PaginationParams,
        verification_status: DoctorVerificationStatus | None = None,
        specialization: str | None = None,
        search: str | None = None,
    ) -> AdminDoctorListResponse:
        profiles, total = await self._repo.list_doctors(
            page=pagination.page,
            size=pagination.size,
            sort_by=pagination.sort_by,
            sort_order=pagination.sort_order,
            verification_status=verification_status,
            specialization=specialization,
            search=search,
        )

        items = [
            AdminDoctorResponse(
                id=p.id,
                user_id=p.user_id,
                email=p.user.email,
                full_name=p.user.full_name,
                license_number=p.license_number,
                specialization=p.specialization,
                clinic_name=p.clinic_name,
                bio=p.bio,
                verification_status=p.verification_status,
                rejection_reason=p.rejection_reason,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in profiles
        ]

        return AdminDoctorListResponse(
            items=items,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=self._repo.calculate_pages(total, pagination.size),
        )

    async def list_predictions(
        self,
        pagination: PaginationParams,
        status_filter: str | None = None,
        user_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> AdminPredictionListResponse:
        predictions, total = await self._repo.list_predictions(
            page=pagination.page,
            size=pagination.size,
            sort_by=pagination.sort_by,
            sort_order=pagination.sort_order,
            status_filter=status_filter,
            user_id=user_id,
            search=search,
        )

        items = [
            AdminPredictionResponse(
                id=p.id,
                uploaded_file_id=p.uploaded_file_id,
                requested_by_id=p.requested_by_id,
                requested_by_email=p.requested_by.email,
                requested_by_name=p.requested_by.full_name,
                status=p.status,
                model_name=p.model_name,
                model_version=p.model_version,
                predicted_label=p.predicted_label,
                confidence_score=p.confidence_score,
                result=p.result,
                error_message=p.error_message,
                completed_at=p.completed_at,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in predictions
        ]

        return AdminPredictionListResponse(
            items=items,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=self._repo.calculate_pages(total, pagination.size),
        )

    async def get_prediction(self, prediction_id: uuid.UUID) -> AdminPredictionResponse:
        prediction = await self._repo.get_prediction_by_id(prediction_id)
        if prediction is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prediction not found",
            )

        return AdminPredictionResponse(
            id=prediction.id,
            uploaded_file_id=prediction.uploaded_file_id,
            requested_by_id=prediction.requested_by_id,
            requested_by_email=prediction.requested_by.email,
            requested_by_name=prediction.requested_by.full_name,
            status=prediction.status,
            model_name=prediction.model_name,
            model_version=prediction.model_version,
            predicted_label=prediction.predicted_label,
            confidence_score=prediction.confidence_score,
            result=prediction.result,
            error_message=prediction.error_message,
            completed_at=prediction.completed_at,
            created_at=prediction.created_at,
            updated_at=prediction.updated_at,
        )

    async def list_prediction_logs(
        self,
        prediction_id: uuid.UUID,
        pagination: PaginationParams,
        event: PredictionLogEvent | None = None,
    ) -> PredictionLogListResponse:
        prediction = await self._repo.get_prediction_by_id(prediction_id)
        if prediction is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prediction not found",
            )

        logs, total = await self._repo.list_prediction_logs(
            prediction_id=prediction_id,
            page=pagination.page,
            size=pagination.size,
            event_filter=event,
        )

        items = [
            PredictionLogResponse(
                id=log.id,
                prediction_id=log.prediction_id,
                actor_user_id=log.actor_user_id,
                actor_name=log.actor.full_name if log.actor else None,
                event=log.event,
                message=log.message,
                metadata=log.metadata_,
                created_at=log.created_at,
            )
            for log in logs
        ]

        return PredictionLogListResponse(
            items=items,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=self._repo.calculate_pages(total, pagination.size),
        )
