from __future__ import annotations

import logging
import time
import uuid

from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger("requests")
app_logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        trace_id = str(uuid.uuid4())
        start = time.perf_counter()
        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        query = scope.get("query_string", b"").decode()
        client_info = scope.get("client")
        client_host = client_info[0] if client_info else "unknown"
        status_code = [200]

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code[0] = message["status"]
                h = dict(message.get("headers", []))
                h[b"x-trace-id"] = trace_id.encode()
                message["headers"] = list(h.items())
            await send(message)

        await self.app(scope, receive, send_wrapper)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        extra = {
            "trace_id": trace_id,
            "duration_ms": duration_ms,
            "status_code": status_code[0],
            "method": method,
            "path": path + (f"?{query}" if query else ""),
            "client_host": client_host,
        }

        full_path = path + (f"?{query}" if query else "")
        if status_code[0] >= 500:
            app_logger.error(
                "%s %s \u2192 %d (%s ms)",
                method,
                full_path,
                status_code[0],
                duration_ms,
                extra=extra,
            )
        elif status_code[0] >= 400:
            app_logger.warning(
                "%s %s \u2192 %d (%s ms)",
                method,
                full_path,
                status_code[0],
                duration_ms,
                extra=extra,
            )
        else:
            logger.info(
                "%s %s \u2192 %d (%s ms)",
                method,
                full_path,
                status_code[0],
                duration_ms,
                extra=extra,
            )
