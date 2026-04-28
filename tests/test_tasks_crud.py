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
    @allure.description(
        "Creating a task with only a title returns 201 and applies the correct defaults: "
        "status='todo', priority='medium', description=null, due_date=null. Confirms "
        "the API does not require optional fields."
    )
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
    @allure.description(
        "Creating a task with all optional fields populated (description, status, "
        "priority, due_date) returns 201 and round-trips every value correctly. "
        "Confirms no field is silently dropped or coerced."
    )
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
    @allure.description(
        "The task creation response contains exactly the expected set of fields: "
        "id, title, description, status, priority, due_date, owner_id, created_at, "
        "updated_at. This is a contract test — any field added or removed from "
        "TaskResponse will cause this test to fail immediately."
    )
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
    @allure.description(
        "Fetching a task by its ID returns 200 with the correct task. Confirms the "
        "GET /tasks/{id} endpoint resolves the right record and that the response "
        "matches what was created."
    )
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
    @allure.description(
        "Requesting a task ID that does not exist returns 404. Verifies the API "
        "handles missing resources gracefully rather than returning 500 or an empty "
        "200 response."
    )
    async def test_get_nonexistent_task_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.get("/tasks/99999", headers=auth_headers)

        assert resp.status_code == 404


@allure.feature("Tasks")
class TestUpdateTask:
    @allure.story("Update")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description(
        "Sending a PUT request with only a title field updates the title and leaves "
        "all other fields (status, priority) unchanged. Confirms the endpoint supports "
        "partial updates — only fields present in the body are modified."
    )
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
    @allure.description(
        "Updating a task with the same values it already has returns 200 with an "
        "unchanged response. Verifies that the update operation is idempotent — "
        "repeating it has no unintended side effects."
    )
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
    @allure.description(
        "Deleting an existing task returns 204 No Content, confirming the operation "
        "succeeded. The API uses soft deletion — the row is marked is_deleted=True "
        "rather than removed from the database."
    )
    async def test_delete_task_returns_204(
        self, client: AsyncClient, auth_headers: dict
    ):
        created = (await create_task(client, auth_headers)).json()

        resp = await client.delete(f"/tasks/{created['id']}", headers=auth_headers)

        assert resp.status_code == 204

    @allure.story("Delete")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description(
        "Fetching a soft-deleted task by ID returns 404, not 500. Verifies that the "
        "get_task_or_404 helper correctly filters out is_deleted=True rows and that "
        "deleted data does not cause a server error."
    )
    async def test_deleted_task_returns_404_not_500(
        self, client: AsyncClient, auth_headers: dict
    ):
        created = (await create_task(client, auth_headers)).json()
        await client.delete(f"/tasks/{created['id']}", headers=auth_headers)

        resp = await client.get(f"/tasks/{created['id']}", headers=auth_headers)

        assert resp.status_code == 404

    @allure.story("Delete")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description(
        "After a task is deleted, it no longer appears in the GET /tasks list response. "
        "Confirms the list endpoint's is_deleted=False filter works correctly and that "
        "soft-deleted tasks are fully hidden from the user."
    )
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
    @allure.description(
        "End-to-end journey test: register a new user, log in to obtain a token, "
        "create a task, update its status from 'todo' to 'done', delete it, then "
        "confirm it is absent from the task list. Exercises the full authenticated "
        "CRUD lifecycle in a single flow."
    )
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
