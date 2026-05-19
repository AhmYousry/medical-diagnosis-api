from __future__ import annotations

import uuid

import httpx
import pytest


class TestRegister:
    async def test_register_success(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@test.com",
                "password": "strongpass123",
                "full_name": "New User",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"
        assert body["user"]["email"] == "newuser@test.com"
        assert body["user"]["role"] == "user"
        assert "id" in body["user"]

    async def test_register_duplicate_email(self, client: httpx.AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "dup@test.com",
                "password": "strongpass123",
                "full_name": "Dup User",
            },
        )
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "dup@test.com",
                "password": "otherpass456",
                "full_name": "Dup User 2",
            },
        )
        assert resp.status_code == 409
        assert "already registered" in resp.json()["detail"].lower()

    async def test_register_email_normalized(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "  Mixed@Case.COM  ",
                "password": "strongpass123",
                "full_name": "Case Test",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["user"]["email"] == "mixed@case.com"

    async def test_register_short_password(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "shortpw@test.com",
                "password": "1234567",
                "full_name": "Short PW",
            },
        )
        assert resp.status_code == 422

    async def test_register_missing_fields(self, client: httpx.AsyncClient) -> None:
        resp = await client.post("/api/v1/auth/register", json={})
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success(self, client: httpx.AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "logintest@test.com",
                "password": "mypassword123",
                "full_name": "Login Test",
            },
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "logintest@test.com", "password": "mypassword123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: httpx.AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrongpw@test.com",
                "password": "correctpw123",
                "full_name": "Wrong PW",
            },
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "wrongpw@test.com", "password": "wrongpassword"},
        )
        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower()

    async def test_login_nonexistent_email(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "doesnotexist@test.com",
                "password": "somepassword123",
            },
        )
        assert resp.status_code == 401

    async def test_login_email_normalized(self, client: httpx.AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "case@test.com",
                "password": "mypassword123",
                "full_name": "Case Login",
            },
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "  CASE@test.COM  ", "password": "mypassword123"},
        )
        assert resp.status_code == 200

    async def test_login_via_token_endpoint(self, client: httpx.AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "tokenuser@test.com",
                "password": "secret123",
                "full_name": "Token User",
            },
        )
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "tokenuser@test.com", "password": "secret123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body


class TestGetMe:
    async def test_get_me_authenticated(self, client: httpx.AsyncClient, auth_headers: dict) -> None:
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "regular@test.com"
        assert body["role"] == "user"

    async def test_get_me_unauthenticated(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_get_me_invalid_token(self, client: httpx.AsyncClient) -> None:
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalidtoken"},
        )
        assert resp.status_code == 401


class TestAdminEndpoint:
    async def test_admin_access_allowed(self, client: httpx.AsyncClient, admin_headers: dict) -> None:
        resp = await client.get("/api/v1/auth/admin", headers=admin_headers)
        assert resp.status_code == 200

    async def test_admin_access_denied_for_regular_user(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get("/api/v1/auth/admin", headers=auth_headers)
        assert resp.status_code == 403

    async def test_admin_access_unauthenticated(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/v1/auth/admin")
        assert resp.status_code == 401


class TestRefreshToken:
    async def test_refresh_success(self, client: httpx.AsyncClient) -> None:
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "refreshtest@test.com",
                "password": "strongpass123",
                "full_name": "Refresh Test",
            },
        )
        refresh_token = reg.json()["refresh_token"]

        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["refresh_token"] != refresh_token  # rotated

    async def test_refresh_invalid_token(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "a" * 32},
        )
        assert resp.status_code == 401

    async def test_refresh_reused_token(self, client: httpx.AsyncClient) -> None:
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "reuse@test.com",
                "password": "strongpass123",
                "full_name": "Reuse Test",
            },
        )
        refresh_token = reg.json()["refresh_token"]

        await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 401


class TestDoctorEndpoint:
    async def test_doctor_endpoint_with_approved_doctor(
        self, client: httpx.AsyncClient, db_engine
    ) -> None:
        reg = await client.post(
            "/api/v1/doctors/register",
            json={
                "email": "approved@doc.com",
                "password": "docpassword123",
                "full_name": "Dr. Approved",
                "license_number": "LIC-APPROVED",
                "specialization": "Cardiology",
            },
        )
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        profile_id = reg.json()["doctor_profile"]["id"]

        admin_reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "approving@admin.com",
                "password": "adminpass123",
                "full_name": "Approving Admin",
            },
        )
        admin_token = admin_reg.json()["access_token"]

        from app.db.enums import UserRole
        from app.modules.users.models import User
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession

        async with AsyncSession(bind=db_engine) as s:
            result = await s.execute(
                select(User).where(User.email == "approving@admin.com")
            )
            user = result.scalar_one()
            user.role = UserRole.ADMIN
            await s.commit()

        resp = await client.post(
            f"/api/v1/doctors/admin/{profile_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

        resp = await client.get(
            "/api/v1/auth/doctor",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_doctor_endpoint_denied_for_regular_user(
        self, client: httpx.AsyncClient, auth_headers: dict
    ) -> None:
        resp = await client.get("/api/v1/auth/doctor", headers=auth_headers)
        assert resp.status_code == 403
