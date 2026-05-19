import logging

from httpx import AsyncClient, Timeout, HTTPError

from app.core.config import settings
from app.infrastructure.retry import retry_async

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    pass


class AIServiceClient:
    def __init__(
        self,
        base_url: str = settings.ai_service_url,
        timeout: float = 120.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = Timeout(timeout)

    async def predict(self, image_bytes: bytes, filename: str = "image.jpg") -> dict:
        async def _do_predict() -> dict:
            async with AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
                files = {"image_data": (filename, image_bytes, "application/octet-stream")}
                response = await client.post("/", files=files)
                if response.status_code >= 500:
                    raise AIServiceError(
                        f"AI service error: {response.status_code} {response.text}"
                    )
                if response.status_code >= 400:
                    data = response.json()
                    raise AIServiceError(
                        data.get("error", f"AI request failed: {response.status_code}")
                    )
                return response.json()

        return await retry_async(
            _do_predict,
            max_retries=settings.ai_retry_max_retries,
            base_delay=settings.ai_retry_base_delay,
        )

    async def health(self) -> dict:
        async with AsyncClient(base_url=self._base_url, timeout=5.0) as client:
            response = await client.get("/")
            response.raise_for_status()
            return {"status": "ok", "response": response.text}
