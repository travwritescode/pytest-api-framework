from datetime import datetime, timedelta, timezone

import allure
from httpx import AsyncClient
from jose import jwt

from app.config import settings
from helpers.factories import auth_headers, create_task, login, register_user, unique_email


def expired_token(email: str) -> str:
    """Craft a structurally valid JWT whose exp is one hour in the past."""
    payload = {
        "sub": email,
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


TASK_ENDPOINTS = [
    ("GET", "/tasks"),
    ("POST", "/tasks"),
    ("GET", "/tasks/1"),
    ("PUT", "/tasks/1"),
    ("DELETE", "/tasks/1"),
]


@allure.feature("Tasks")
class TestUnauthenticatedAccess:
    @allure.story("Auth Boundaries")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_no_token_returns_401(self, client: AsyncClient):
        resp = await client.get("/tasks")
        assert resp.status_code == 401

    @allure.story("Auth Boundaries")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_malformed_token_returns_401(self, client: AsyncClient):
        headers = {"Authorization": "Bearer this.is.not.a.real.jwt"}
        resp = await client.get("/tasks", headers=headers)
        assert resp.status_code == 401

    @allure.story("Auth Boundaries")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_expired_token_returns_401(self, client: AsyncClient):
        email = unique_email()
        await register_user(client, email=email)

        headers = {"Authorization": f"Bearer {expired_token(email)}"}
        resp = await client.get("/tasks", headers=headers)

        assert resp.status_code == 401


@allure.feature("Tasks")
class TestCrossUserAccess:
    @allure.story("Auth Boundaries")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_get_another_users_task_returns_403(self, client: AsyncClient):
        email_a, email_b = unique_email(), unique_email()
        await register_user(client, email=email_a)
        await register_user(client, email=email_b)

        headers_a = auth_headers(await login(client, email_a))
        headers_b = auth_headers(await login(client, email_b))

        task = (await create_task(client, headers_a, title="User A task")).json()

        resp = await client.get(f"/tasks/{task['id']}", headers=headers_b)
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Access denied"

    @allure.story("Auth Boundaries")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_update_another_users_task_returns_403(self, client: AsyncClient):
        email_a, email_b = unique_email(), unique_email()
        await register_user(client, email=email_a)
        await register_user(client, email=email_b)

        headers_a = auth_headers(await login(client, email_a))
        headers_b = auth_headers(await login(client, email_b))

        task = (await create_task(client, headers_a)).json()

        resp = await client.put(
            f"/tasks/{task['id']}", json={"title": "Hijacked"}, headers=headers_b
        )
        assert resp.status_code == 403

    @allure.story("Auth Boundaries")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_delete_another_users_task_returns_403(self, client: AsyncClient):
        email_a, email_b = unique_email(), unique_email()
        await register_user(client, email=email_a)
        await register_user(client, email=email_b)

        headers_a = auth_headers(await login(client, email_a))
        headers_b = auth_headers(await login(client, email_b))

        task = (await create_task(client, headers_a)).json()

        resp = await client.delete(f"/tasks/{task['id']}", headers=headers_b)
        assert resp.status_code == 403

    @allure.story("Auth Boundaries")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_list_tasks_only_returns_own_tasks(self, client: AsyncClient):
        email_a, email_b = unique_email(), unique_email()
        await register_user(client, email=email_a)
        await register_user(client, email=email_b)

        headers_a = auth_headers(await login(client, email_a))
        headers_b = auth_headers(await login(client, email_b))

        task_a = (await create_task(client, headers_a, title="User A task")).json()
        await create_task(client, headers_b, title="User B task")

        resp = await client.get("/tasks", headers=headers_a)
        ids = [t["id"] for t in resp.json()]

        assert task_a["id"] in ids
        assert all(t["owner_id"] == task_a["owner_id"] for t in resp.json())
