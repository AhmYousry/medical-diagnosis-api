from __future__ import annotations

import time
from typing import cast

from redis.asyncio import Redis
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings


class RateLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._prefix = "ratelimit:"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if not settings.rate_limit_enabled:
            await self.app(scope, receive, send)
            return

        redis: Redis | None = getattr(scope.get("app"), "state", None) and getattr(
            scope["app"].state, "redis", None
        )
        if redis is None:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")
        method = scope.get("method", "GET")
        client_info = scope.get("client")
        client_host = client_info[0] if client_info else "unknown"
        headers = dict(scope.get("headers", []))

        key = self._build_key(path, headers, client_host)
        max_reqs, window = self._get_limits(path)

        try:
            current = await self._check_limit(redis, key, max_reqs, window)
            remaining = max_reqs - current

            if current >= max_reqs:
                body_json = (
                    '{"detail":"Too many requests. Please try again later.",'
                    f'"retry_after_seconds":{window}}}'
                ).encode()
                headers_out = [
                    (b"content-type", b"application/json"),
                    (b"x-ratelimit-limit", str(max_reqs).encode()),
                    (b"x-ratelimit-remaining", b"0"),
                    (b"x-ratelimit-reset", str(int(time.time()) + window).encode()),
                ]
                resp_message = {
                    "type": "http.response.start",
                    "status": 429,
                    "headers": headers_out,
                }
                resp_body = {
                    "type": "http.response.body",
                    "body": body_json,
                }
                await send(resp_message)
                await send(resp_body)
                return

            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    h = dict(message.get("headers", []))
                    h[b"x-ratelimit-limit"] = str(max_reqs).encode()
                    h[b"x-ratelimit-remaining"] = str(max(0, remaining)).encode()
                    h[b"x-ratelimit-reset"] = str(int(time.time()) + window).encode()
                    message["headers"] = list(h.items())
                await send(message)

            await self.app(scope, receive, send_wrapper)
        except Exception:
            await self.app(scope, receive, send)

    def _build_key(self, path: str, headers: dict, client_host: str) -> str:
        if path.startswith(settings.api_v1_prefix + "/auth"):
            return f"{self._prefix}auth:{client_host}"
        token = headers.get(b"authorization", b"")
        user_id = "anonymous"
        if token.startswith(b"Bearer "):
            import hashlib
            user_id = hashlib.sha256(token).hexdigest()[:16]
        return f"{self._prefix}user:{user_id}"

    def _get_limits(self, path: str) -> tuple[int, int]:
        if path.startswith(settings.api_v1_prefix + "/auth"):
            return (
                settings.rate_limit_auth_max_requests,
                settings.rate_limit_auth_window_seconds,
            )
        return (
            settings.rate_limit_max_requests,
            settings.rate_limit_window_seconds,
        )

    async def _check_limit(
        self, redis: Redis, key: str, max_reqs: int, window: int
    ) -> int:
        now = int(time.time())
        window_start = now - window

        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window + 60)
        _, count, _, _ = await pipe.execute()
        return cast(int, count)
