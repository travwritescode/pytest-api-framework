import allure
from httpx import AsyncClient

from helpers.factories import create_task, unique_email


@allure.feature("Validation")
class TestTaskCreateValidation:
    @allure.story("Task Create")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description(
        "Submitting a task creation request with an empty string title returns 422. "
        "Pydantic's min_length=1 constraint on the title field rejects the value "
        "before it reaches the database."
    )
    async def test_empty_title_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await create_task(client, auth_headers, title="")
        assert resp.status_code == 422

    @allure.story("Task Create")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description(
        "Submitting a task creation request with a title of 201 characters returns 422. "
        "Pydantic's max_length=200 constraint rejects values exceeding the limit. "
        "See the companion test confirming 200 characters is valid."
    )
    async def test_title_exceeding_max_length_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await create_task(client, auth_headers, title="x" * 201)
        assert resp.status_code == 422

    @allure.story("Task Create")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description(
        "Submitting a task creation request with a title of exactly 200 characters "
        "returns 201. Confirms the boundary value is accepted and the max_length=200 "
        "constraint is inclusive."
    )
    async def test_title_at_max_length_is_valid(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await create_task(client, auth_headers, title="x" * 200)
        assert resp.status_code == 201

    @allure.story("Task Create")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description(
        "Submitting a task creation request with a status value not in the TaskStatus "
        "enum ('not_a_status') returns 422. Pydantic rejects unknown enum values before "
        "any database operation occurs."
    )
    async def test_invalid_status_enum_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await create_task(client, auth_headers, status="not_a_status")
        assert resp.status_code == 422

    @allure.story("Task Create")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description(
        "Submitting a task creation request with a priority value not in the "
        "TaskPriority enum ('urgent') returns 422. Valid values are 'low', 'medium', "
        "and 'high'."
    )
    async def test_invalid_priority_enum_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await create_task(client, auth_headers, priority="urgent")
        assert resp.status_code == 422


@allure.feature("Validation")
class TestTaskUpdateValidation:
    @allure.story("Task Update")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description(
        "Sending a PUT request with title set to an empty string returns 422. "
        "Confirms the min_length=1 constraint applies to updates as well as creates — "
        "an existing title cannot be blanked out via the update endpoint."
    )
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
    @allure.description(
        "Sending a PUT request with an invalid status value returns 422. Confirms "
        "that TaskUpdate applies the same enum validation as TaskCreate, preventing "
        "tasks from being updated to an invalid state."
    )
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
    @allure.description(
        "Submitting a registration payload with a malformed email ('not-an-email') "
        "returns 422. Pydantic's EmailStr validator rejects the value, ensuring only "
        "valid email addresses can be registered."
    )
    async def test_register_with_invalid_email_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/auth/register", json={"email": "not-an-email", "password": "Pass123!"}
        )
        assert resp.status_code == 422

    @allure.story("Register")
    @allure.severity(allure.severity_level.MINOR)
    @allure.description(
        "Submitting a registration payload with no password field returns 422. "
        "Pydantic requires both email and password to be present; omitting a required "
        "field is rejected before any application logic runs."
    )
    async def test_register_missing_password_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/auth/register", json={"email": unique_email()}
        )
        assert resp.status_code == 422

    @allure.story("Login")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description(
        "Sending a login request with a JSON body instead of form-encoded data returns "
        "422. The /auth/login endpoint uses OAuth2PasswordRequestForm which requires "
        "application/x-www-form-urlencoded content type, not application/json."
    )
    async def test_login_with_json_body_returns_422(self, client: AsyncClient):
        # Login expects form-encoded data, not JSON.
        resp = await client.post(
            "/auth/login",
            json={"username": unique_email(), "password": "Pass123!"},
        )
        assert resp.status_code == 422
