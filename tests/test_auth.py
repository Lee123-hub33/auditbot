# tests/test_auth.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_upload_requires_auth():
    """Unauthenticated upload must be rejected."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/documents/upload")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_weak_password_rejected():
    """Password without uppercase/digit/special char must fail validation."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/auth/register", json={
            "email": "weak@example.com",
            "password": "weakpassword",
        })
        assert resp.status_code == 422
