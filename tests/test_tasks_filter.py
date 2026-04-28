import allure
from httpx import AsyncClient

from helpers.factories import create_task


@allure.feature("Tasks")
class TestStatusFilter:
    @allure.story("Filtering")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_no_filter_returns_all_tasks(
        self, client: AsyncClient, auth_headers: dict
    ):
        await create_task(client, auth_headers, title="Task 1", status="todo")
        await create_task(client, auth_headers, title="Task 2", status="in_progress")
        await create_task(client, auth_headers, title="Task 3", status="done")

        resp = await client.get("/tasks", headers=auth_headers)

        assert resp.status_code == 200
        assert len(resp.json()) == 3

    @allure.story("Filtering")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_status_todo_filter(self, client: AsyncClient, auth_headers: dict):
        await create_task(client, auth_headers, status="todo")
        await create_task(client, auth_headers, status="done")

        resp = await client.get("/tasks?status=todo", headers=auth_headers)

        tasks = resp.json()
        assert resp.status_code == 200
        assert len(tasks) == 1
        assert tasks[0]["status"] == "todo"

    @allure.story("Filtering")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_status_in_progress_filter(
        self, client: AsyncClient, auth_headers: dict
    ):
        await create_task(client, auth_headers, status="in_progress")
        await create_task(client, auth_headers, status="todo")

        resp = await client.get("/tasks?status=in_progress", headers=auth_headers)

        tasks = resp.json()
        assert resp.status_code == 200
        assert all(t["status"] == "in_progress" for t in tasks)

    @allure.story("Filtering")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_status_done_filter(self, client: AsyncClient, auth_headers: dict):
        await create_task(client, auth_headers, status="done")
        await create_task(client, auth_headers, status="todo")

        resp = await client.get("/tasks?status=done", headers=auth_headers)

        tasks = resp.json()
        assert resp.status_code == 200
        assert all(t["status"] == "done" for t in tasks)


@allure.feature("Tasks")
class TestPriorityFilter:
    @allure.story("Filtering")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_priority_high_filter(self, client: AsyncClient, auth_headers: dict):
        await create_task(client, auth_headers, priority="high")
        await create_task(client, auth_headers, priority="low")

        resp = await client.get("/tasks?priority=high", headers=auth_headers)

        tasks = resp.json()
        assert resp.status_code == 200
        assert len(tasks) == 1
        assert tasks[0]["priority"] == "high"

    @allure.story("Filtering")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_priority_low_filter(self, client: AsyncClient, auth_headers: dict):
        await create_task(client, auth_headers, priority="low")
        await create_task(client, auth_headers, priority="high")
        await create_task(client, auth_headers, priority="medium")

        resp = await client.get("/tasks?priority=low", headers=auth_headers)

        tasks = resp.json()
        assert resp.status_code == 200
        assert all(t["priority"] == "low" for t in tasks)


@allure.feature("Tasks")
class TestCombinedFilter:
    @allure.story("Filtering")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_status_and_priority_combined(
        self, client: AsyncClient, auth_headers: dict
    ):
        await create_task(client, auth_headers, status="todo", priority="high")
        await create_task(client, auth_headers, status="todo", priority="low")
        await create_task(client, auth_headers, status="done", priority="high")

        resp = await client.get(
            "/tasks?status=todo&priority=high", headers=auth_headers
        )

        tasks = resp.json()
        assert resp.status_code == 200
        assert len(tasks) == 1
        assert tasks[0]["status"] == "todo"
        assert tasks[0]["priority"] == "high"

    @allure.story("Filtering")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_filter_with_no_matches_returns_empty_list(
        self, client: AsyncClient, auth_headers: dict
    ):
        await create_task(client, auth_headers, status="todo")

        resp = await client.get("/tasks?status=done", headers=auth_headers)

        assert resp.status_code == 200
        assert resp.json() == []


@allure.feature("Tasks")
class TestOrdering:
    @allure.story("Ordering")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_tasks_returned_newest_first(
        self, client: AsyncClient, auth_headers: dict
    ):
        await create_task(client, auth_headers, title="First")
        await create_task(client, auth_headers, title="Second")
        await create_task(client, auth_headers, title="Third")

        resp = await client.get("/tasks", headers=auth_headers)
        created_ats = [t["created_at"] for t in resp.json()]

        # Assert the list is in non-increasing created_at order.
        # SQLite's func.now() has second-level resolution so timestamps may be
        # equal, but the sort direction (desc) should still hold.
        assert created_ats == sorted(created_ats, reverse=True)


@allure.feature("Tasks")
class TestSoftDelete:
    @allure.story("Soft Delete")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_soft_deleted_task_excluded_from_list(
        self, client: AsyncClient, auth_headers: dict
    ):
        visible = (await create_task(client, auth_headers, title="Visible")).json()
        deleted = (await create_task(client, auth_headers, title="Deleted")).json()
        await client.delete(f"/tasks/{deleted['id']}", headers=auth_headers)

        resp = await client.get("/tasks", headers=auth_headers)
        ids = [t["id"] for t in resp.json()]

        assert visible["id"] in ids
        assert deleted["id"] not in ids

    @allure.story("Soft Delete")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_soft_deleted_task_returns_404_not_500(
        self, client: AsyncClient, auth_headers: dict
    ):
        task = (await create_task(client, auth_headers)).json()
        await client.delete(f"/tasks/{task['id']}", headers=auth_headers)

        resp = await client.get(f"/tasks/{task['id']}", headers=auth_headers)

        assert resp.status_code == 404
