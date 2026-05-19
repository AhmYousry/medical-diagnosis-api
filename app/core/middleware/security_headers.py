from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"x-xss-protection", b"0"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                    (b"cross-origin-resource-policy", b"same-origin"),
                    (b"cross-origin-opener-policy", b"same-origin"),
                ]
                scheme = scope.get("scheme", "http")
                if scheme == "https":
                    headers.append(
                        (b"strict-transport-security", b"max-age=63072000; includeSubDomains")
                    )
                    headers.append(
                        (b"content-security-policy", b"default-src 'self'; frame-ancestors 'none'")
                    )
                existing = dict(message.get("headers", []))
                existing.update(dict(headers))
                message["headers"] = list(existing.items())
            await send(message)

        await self.app(scope, receive, send_wrapper)
