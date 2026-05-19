from __future__ import annotations

import httpx

from tests.conftest import TEST_PNG


class TestUploadFile:
    async def test_upload_success(self, client: httpx.AsyncClient, auth_headers: dict) -> None:
        resp = await client.post(
            "/api/v1/uploads/upload",
            files={"file": ("test.png", TEST_PNG, "image/png")},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert body["original_filename"] == "test.png"
        assert body["content_type"] == "image/png"
        assert body["status"] == "stored"

    async def test_upload_requires_auth(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/uploads/upload",
            files={"file": ("test.png", TEST_PNG, "image/png")},
        )
        assert resp.status_code == 401

    async def test_upload_unsupported_content_type(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post(
            "/api/v1/uploads/upload",
            files={"file": ("test.txt", TEST_PNG, "text/plain")},
            headers=auth_headers,
        )
        assert resp.status_code == 415

    async def test_upload_content_type_mismatch(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.post(
            "/api/v1/uploads/upload",
            files={"file": ("fake.png", b"not-an-image-content", "image/png")},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestListFiles:
    async def test_list_files_empty(self, client: httpx.AsyncClient, auth_headers: dict) -> None:
        resp = await client.get("/api/v1/uploads", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["files"], list)
        assert body["total"] >= 0

    async def test_list_files_after_upload(
        self, client: httpx.AsyncClient, auth_headers: dict, uploaded_file_id: str
    ) -> None:
        resp = await client.get("/api/v1/uploads", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["files"]) >= 1
        assert body["files"][0]["id"] == str(uploaded_file_id)

    async def test_list_files_isolation(
        self, client: httpx.AsyncClient, auth_headers: dict, uploaded_file_id: str
    ) -> None:
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "other@test.com",
                "password": "otherpass123",
                "full_name": "Other User",
            },
        )
        other_token = reg.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        resp = await client.get("/api/v1/uploads", headers=other_headers)
        assert resp.status_code == 200
        assert resp.json()["files"] == []


class TestGetFile:
    async def test_get_file_success(
        self, client: httpx.AsyncClient, auth_headers: dict, uploaded_file_id: str
    ) -> None:
        resp = await client.get(f"/api/v1/uploads/{uploaded_file_id}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(uploaded_file_id)
        assert body["original_filename"] == "test.png"

    async def test_get_file_not_found(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get(
            "/api/v1/uploads/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_get_file_unauthorized_access(
        self, client: httpx.AsyncClient, auth_headers: dict, uploaded_file_id: str
    ) -> None:
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "other2@test.com",
                "password": "otherpass123",
                "full_name": "Other User 2",
            },
        )
        other_token = reg.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        resp = await client.get(f"/api/v1/uploads/{uploaded_file_id}", headers=other_headers)
        assert resp.status_code == 404


class TestDeleteFile:
    async def test_delete_file_success(
        self, client: httpx.AsyncClient, auth_headers: dict, uploaded_file_id: str
    ) -> None:
        resp = await client.delete(f"/api/v1/uploads/{uploaded_file_id}", headers=auth_headers)
        assert resp.status_code == 204

    async def test_delete_already_deleted(
        self, client: httpx.AsyncClient, auth_headers: dict, uploaded_file_id: str
    ) -> None:
        await client.delete(f"/api/v1/uploads/{uploaded_file_id}", headers=auth_headers)
        resp = await client.delete(f"/api/v1/uploads/{uploaded_file_id}", headers=auth_headers)
        assert resp.status_code == 404

    async def test_delete_other_users_file(
        self, client: httpx.AsyncClient, auth_headers: dict, uploaded_file_id: str
    ) -> None:
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "other3@test.com",
                "password": "otherpass123",
                "full_name": "Other User 3",
            },
        )
        other_token = reg.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        resp = await client.delete(f"/api/v1/uploads/{uploaded_file_id}", headers=other_headers)
        assert resp.status_code == 404
