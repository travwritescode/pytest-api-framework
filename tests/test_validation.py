import allure
from httpx import AsyncClient

from helpers.factories import create_task, unique_email


@allure.feature("Validation")
class TestTaskCreateValidation:
    @allure.story("Task Create")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_empty_title_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await create_task(client, auth_headers, title="")
        assert resp.status_code == 422

    @allure.story("Task Create")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_title_exceeding_max_length_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await create_task(client, auth_headers, title="x" * 201)
        assert resp.status_code == 422

    @allure.story("Task Create")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_title_at_max_length_is_valid(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await create_task(client, auth_headers, title="x" * 200)
        assert resp.status_code == 201

    @allure.story("Task Create")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_invalid_status_enum_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await create_task(client, auth_headers, status="not_a_status")
        assert resp.status_code == 422

    @allure.story("Task Create")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_invalid_priority_enum_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await create_task(client, auth_headers, priority="urgent")
        assert resp.status_code == 422


@allure.feature("Validation")
class TestTaskUpdateValidation:
    @allure.story("Task Update")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_update_with_empty_title_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        created = (await create_task(client, auth_headers)).json()

        resp = await client.put(
            f"/tasks/{created['id']}", json={"title": ""}, headers=auth_headers
        )
        assert resp.status_code == 422

    @allure.story("Task Update")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_update_with_invalid_status_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        created = (await create_task(client, auth_headers)).json()

        resp = await client.put(
            f"/tasks/{created['id']}",
            json={"status": "not_a_status"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


@allure.feature("Validation")
class TestAuthValidation:
    @allure.story("Register")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_register_with_invalid_email_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/auth/register", json={"email": "not-an-email", "password": "Pass123!"}
        )
        assert resp.status_code == 422

    @allure.story("Register")
    @allure.severity(allure.severity_level.MINOR)
    async def test_register_missing_password_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/auth/register", json={"email": unique_email()}
        )
        assert resp.status_code == 422

    @allure.story("Login")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_login_with_json_body_returns_422(self, client: AsyncClient):
        # Login expects form-encoded data, not JSON.
        resp = await client.post(
            "/auth/login",
            json={"username": unique_email(), "password": "Pass123!"},
        )
        assert resp.status_code == 422
