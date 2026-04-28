import allure
import pytest
from httpx import AsyncClient

from helpers.factories import auth_headers, create_task, login, register_user, unique_email

EXPECTED_TASK_FIELDS = {
    "id", "title", "description", "status", "priority",
    "due_date", "owner_id", "created_at", "updated_at",
}


@allure.feature("Tasks")
class TestCreateTask:
    @allure.story("Create")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_create_minimal_task_returns_201_with_defaults(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await create_task(client, auth_headers, title="Buy groceries")

        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Buy groceries"
        assert body["status"] == "todo"
        assert body["priority"] == "medium"
        assert body["description"] is None
        assert body["due_date"] is None

    @allure.story("Create")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_create_task_with_all_fields(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await create_task(
            client,
            auth_headers,
            title="Full task",
            description="A detailed description",
            status="in_progress",
            priority="high",
            due_date="2026-12-31",
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Full task"
        assert body["description"] == "A detailed description"
        assert body["status"] == "in_progress"
        assert body["priority"] == "high"
        assert body["due_date"] == "2026-12-31"

    @allure.story("Create")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_create_task_response_contract(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await create_task(client, auth_headers)

        assert resp.status_code == 201
        assert set(resp.json().keys()) == EXPECTED_TASK_FIELDS


@allure.feature("Tasks")
class TestGetTask:
    @allure.story("Read")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_get_task_by_id_returns_correct_task(
        self, client: AsyncClient, auth_headers: dict
    ):
        created = (await create_task(client, auth_headers, title="Fetch me")).json()

        resp = await client.get(f"/tasks/{created['id']}", headers=auth_headers)

        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]
        assert resp.json()["title"] == "Fetch me"

    @allure.story("Read")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_get_nonexistent_task_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.get("/tasks/99999", headers=auth_headers)

        assert resp.status_code == 404


@allure.feature("Tasks")
class TestUpdateTask:
    @allure.story("Update")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_partial_update_only_changes_specified_fields(
        self, client: AsyncClient, auth_headers: dict
    ):
        created = (
            await create_task(
                client, auth_headers, title="Original", status="todo", priority="low"
            )
        ).json()

        resp = await client.put(
            f"/tasks/{created['id']}",
            json={"title": "Updated"},
            headers=auth_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Updated"
        assert body["status"] == "todo"
        assert body["priority"] == "low"

    @allure.story("Update")
    @allure.severity(allure.severity_level.MINOR)
    async def test_update_task_with_same_values_is_idempotent(
        self, client: AsyncClient, auth_headers: dict
    ):
        created = (await create_task(client, auth_headers, title="Stable")).json()

        resp = await client.put(
            f"/tasks/{created['id']}",
            json={"title": "Stable"},
            headers=auth_headers,
        )

        assert resp.status_code == 200
        assert resp.json()["title"] == "Stable"


@allure.feature("Tasks")
class TestDeleteTask:
    @allure.story("Delete")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_delete_task_returns_204(
        self, client: AsyncClient, auth_headers: dict
    ):
        created = (await create_task(client, auth_headers)).json()

        resp = await client.delete(f"/tasks/{created['id']}", headers=auth_headers)

        assert resp.status_code == 204

    @allure.story("Delete")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_deleted_task_returns_404_not_500(
        self, client: AsyncClient, auth_headers: dict
    ):
        created = (await create_task(client, auth_headers)).json()
        await client.delete(f"/tasks/{created['id']}", headers=auth_headers)

        resp = await client.get(f"/tasks/{created['id']}", headers=auth_headers)

        assert resp.status_code == 404

    @allure.story("Delete")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_deleted_task_absent_from_list(
        self, client: AsyncClient, auth_headers: dict
    ):
        created = (await create_task(client, auth_headers, title="Gone")).json()
        await client.delete(f"/tasks/{created['id']}", headers=auth_headers)

        resp = await client.get("/tasks", headers=auth_headers)

        ids = [t["id"] for t in resp.json()]
        assert created["id"] not in ids


@allure.feature("Tasks")
class TestFullCrudChain:
    @allure.story("CRUD Chain")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_register_login_create_update_delete(self, client: AsyncClient):
        email = unique_email()
        await register_user(client, email=email)
        token = await login(client, email)
        headers = auth_headers(token)

        created = (await create_task(client, headers, title="Chain task")).json()
        task_id = created["id"]
        assert created["status"] == "todo"

        updated = (
            await client.put(
                f"/tasks/{task_id}", json={"status": "done"}, headers=headers
            )
        ).json()
        assert updated["status"] == "done"

        await client.delete(f"/tasks/{task_id}", headers=headers)

        list_resp = await client.get("/tasks", headers=headers)
        ids = [t["id"] for t in list_resp.json()]
        assert task_id not in ids
