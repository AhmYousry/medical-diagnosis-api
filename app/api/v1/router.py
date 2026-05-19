from fastapi import APIRouter

from app.api.v1.routes import health
from app.modules.admin.routes import router as admin_router
from app.modules.auth.routes import router as auth_router
from app.modules.doctors.routes import router as doctors_router
from app.modules.uploaded_files.routes import router as upload_router
from app.modules.predictions.routes import router as prediction_router

api_router = APIRouter()
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(doctors_router, prefix="/doctors", tags=["doctors"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(upload_router, prefix="/uploads", tags=["uploads"])
api_router.include_router(prediction_router, prefix="/predict", tags=["predictions"])
