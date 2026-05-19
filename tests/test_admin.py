from __future__ import annotations

import httpx
import pytest

from tests.conftest import TEST_PNG


class TestAdminListUsers:
    async def test_list_users_success(
        self, client: httpx.AsyncClient, admin_headers: dict
    ) -> None:
        resp = await client.get("/api/v1/admin/users", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] >= 0

    async def test_list_users_role_filter(
        self, client: httpx.AsyncClient, admin_headers: dict
    ) -> None:
        resp = await client.get(
            "/api/v1/admin/users?role=admin", headers=admin_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert all(u["role"] == "admin" for u in body["items"])

    async def test_list_users_denied_for_regular_user(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get("/api/v1/admin/users", headers=auth_headers)
        assert resp.status_code == 403

    async def test_list_users_requires_auth(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/v1/admin/users")
        assert resp.status_code == 401

    async def test_list_users_search(
        self, client: httpx.AsyncClient, admin_headers: dict
    ) -> None:
        resp = await client.get(
            "/api/v1/admin/users?search=regular", headers=admin_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        if body["items"]:
            u = body["items"][0]
            assert "regular" in u["email"] or "regular" in u["full_name"].lower()

    async def test_list_users_pagination(
        self, client: httpx.AsyncClient, admin_headers: dict
    ) -> None:
        resp = await client.get(
            "/api/v1/admin/users?page=1&size=2", headers=admin_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 1
        assert body["size"] == 2
        assert len(body["items"]) <= 2


class TestAdminListDoctors:
    async def test_list_doctors_success(
        self, client: httpx.AsyncClient, admin_headers: dict
    ) -> None:
        resp = await client.get("/api/v1/admin/doctors", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body

    async def test_list_doctors_denied_for_regular_user(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get("/api/v1/admin/doctors", headers=auth_headers)
        assert resp.status_code == 403


class TestAdminPredictions:
    async def test_list_predictions_success(
        self, client: httpx.AsyncClient, admin_headers: dict
    ) -> None:
        resp = await client.get("/api/v1/admin/predictions", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body

    async def test_list_predictions_status_filter(
        self, client: httpx.AsyncClient, admin_headers: dict
    ) -> None:
        resp = await client.get(
            "/api/v1/admin/predictions?status=pending", headers=admin_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert all(p["status"] == "pending" for p in body["items"])

    async def test_get_prediction_not_found(
        self, client: httpx.AsyncClient, admin_headers: dict
    ) -> None:
        resp = await client.get(
            "/api/v1/admin/predictions/00000000-0000-0000-0000-000000000000",
            headers=admin_headers,
        )
        assert resp.status_code == 404

    async def test_get_prediction_logs_not_found(
        self, client: httpx.AsyncClient, admin_headers: dict
    ) -> None:
        resp = await client.get(
            "/api/v1/admin/predictions/00000000-0000-0000-0000-000000000000/logs",
            headers=admin_headers,
        )
        assert resp.status_code == 404

    async def test_admin_full_flow(
        self, client: httpx.AsyncClient, auth_headers: dict, admin_headers: dict
    ) -> None:
        upload = await client.post(
            "/api/v1/uploads/upload",
            files={"file": ("test.png", TEST_PNG, "image/png")},
            headers=auth_headers,
        )
        file_id = upload.json()["id"]

        create = await client.post(
            f"/api/v1/predict/{file_id}",
            headers=auth_headers,
        )
        pred_id = create.json()["id"]

        resp = await client.get(
            f"/api/v1/admin/predictions/{pred_id}", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == pred_id

        resp = await client.get(
            f"/api/v1/admin/predictions/{pred_id}/logs",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        logs = resp.json()
        assert logs["total"] >= 1
        assert logs["items"][0]["event"] in ("created", "pending")
