from __future__ import annotations

import httpx


class TestCreatePrediction:
    async def test_create_prediction_success(
        self, client: httpx.AsyncClient, auth_headers: dict, uploaded_file_id: str
    ) -> None:
        resp = await client.post(
            f"/api/v1/predict/{uploaded_file_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 202
        body = resp.json()
        assert "id" in body
        assert body["status"] == "pending"
        assert body["uploaded_file_id"] == str(uploaded_file_id)

    async def test_create_prediction_nonexistent_file(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post(
            "/api/v1/predict/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_create_prediction_other_users_file(
        self, client: httpx.AsyncClient, auth_headers: dict, uploaded_file_id: str
    ) -> None:
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "other_pred@test.com",
                "password": "otherpass123",
                "full_name": "Other User",
            },
        )
        other_token = reg.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        resp = await client.post(
            f"/api/v1/predict/{uploaded_file_id}",
            headers=other_headers,
        )
        assert resp.status_code == 404

    async def test_create_prediction_requires_auth(
        self, client: httpx.AsyncClient, uploaded_file_id: str
    ) -> None:
        resp = await client.post(
            f"/api/v1/predict/{uploaded_file_id}",
        )
        assert resp.status_code == 401


class TestListPredictions:
    async def test_list_predictions_empty(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get("/api/v1/predict", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["predictions"], list)
        assert body["total"] >= 0

    async def test_list_predictions_with_predictions(
        self, client: httpx.AsyncClient, auth_headers: dict, uploaded_file_id: str
    ) -> None:
        await client.post(
            f"/api/v1/predict/{uploaded_file_id}",
            headers=auth_headers,
        )
        resp = await client.get("/api/v1/predict", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["predictions"]) >= 1
        assert body["predictions"][0]["uploaded_file_id"] == str(uploaded_file_id)

    async def test_list_predictions_isolation(
        self, client: httpx.AsyncClient, auth_headers: dict, uploaded_file_id: str
    ) -> None:
        await client.post(
            f"/api/v1/predict/{uploaded_file_id}",
            headers=auth_headers,
        )

        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "other_list@test.com",
                "password": "otherpass123",
                "full_name": "Other User",
            },
        )
        other_token = reg.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        resp = await client.get("/api/v1/predict", headers=other_headers)
        assert resp.status_code == 200
        assert resp.json()["predictions"] == []


class TestGetPrediction:
    async def test_get_prediction_success(
        self, client: httpx.AsyncClient, auth_headers: dict, uploaded_file_id: str
    ) -> None:
        create = await client.post(
            f"/api/v1/predict/{uploaded_file_id}",
            headers=auth_headers,
        )
        pred_id = create.json()["id"]

        resp = await client.get(f"/api/v1/predict/{pred_id}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == pred_id
        assert body["status"] == "pending"

    async def test_get_prediction_not_found(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get(
            "/api/v1/predict/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_get_prediction_other_user(
        self, client: httpx.AsyncClient, auth_headers: dict, uploaded_file_id: str
    ) -> None:
        create = await client.post(
            f"/api/v1/predict/{uploaded_file_id}",
            headers=auth_headers,
        )
        pred_id = create.json()["id"]

        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "other_get@test.com",
                "password": "otherpass123",
                "full_name": "Other User",
            },
        )
        other_token = reg.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        resp = await client.get(f"/api/v1/predict/{pred_id}", headers=other_headers)
        assert resp.status_code == 404



