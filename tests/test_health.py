from __future__ import annotations

import httpx


class TestHealthEndpoints:
    async def test_liveness(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/v1/health/live")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_readiness(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/v1/health/ready")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_health_check(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["environment"] == "test"
        assert "uptime_seconds" in body
        assert "version" in body

        deps = body["dependencies"]
        assert deps["database"]["status"] == "ok"
        assert deps["redis"]["status"] == "ok"
        assert deps["database"]["error"] is None
        assert deps["redis"]["error"] is None

    async def test_health_check_details(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/v1/health")
        body = resp.json()
        assert isinstance(body["active_users"], int)
        assert body["active_users"] >= 0
        assert body["started_at"] is not None
