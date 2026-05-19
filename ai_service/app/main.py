from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(
        title="Medical Diagnosis AI Service",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    @app.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "service": "ai-service"}

    return app

