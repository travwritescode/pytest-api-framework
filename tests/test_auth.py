import allure
from httpx import AsyncClient

from helpers.factories import register_user, unique_email


@allure.feature("Auth")
class TestRegister:
    @allure.story("Register")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description(
        "Registering with a valid email and password returns 201 with the user's id, "
        "email, is_active, and created_at fields. Verifies that hashed_password is "
        "never exposed in the response."
    )
    async def test_register_returns_201_with_user_fields(self, client: AsyncClient):
        resp = await register_user(client)

        assert resp.status_code == 201
        body = resp.json()
        assert body["id"] is not None
        assert "@" in body["email"]
        assert body["is_active"] is True
        assert "created_at" in body
        assert "hashed_password" not in body

    @allure.story("Register")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description(
        "Attempting to register a second account with an already-registered email "
        "returns 409 Conflict with a detail message indicating the account exists. "
        "Ensures the unique email constraint is enforced at the API level."
    )
    async def test_register_duplicate_email_returns_409(self, client: AsyncClient):
        email = unique_email()
        await register_user(client, email=email)

        resp = await register_user(client, email=email)

        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    @allure.story("Register")
    @allure.severity(allure.severity_level.MINOR)
    @allure.description(
        "Submitting a registration payload with a malformed email string (missing @ "
        "and domain) returns 422 Unprocessable Entity. Pydantic's EmailStr validator "
        "rejects the value before it reaches the database."
    )
    async def test_register_invalid_email_returns_422(self, client: AsyncClient):
        resp = await register_user(client, email="not-an-email")

        assert resp.status_code == 422


@allure.feature("Auth")
class TestLogin:
    @allure.story("Login")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description(
        "Logging in with valid credentials returns 200 with a JWT access_token and "
        "token_type of 'bearer'. The token can then be used as a Bearer header to "
        "authenticate subsequent requests."
    )
    async def test_login_returns_bearer_token(self, client: AsyncClient):
        email = unique_email()
        await register_user(client, email=email)

        resp = await client.post(
            "/auth/login", data={"username": email, "password": "TestPass123!"}
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    @allure.story("Login")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description(
        "Logging in with a correct email but wrong password returns 401 Unauthorized. "
        "The API does not distinguish between wrong password and unknown email to avoid "
        "leaking account existence information."
    )
    async def test_login_wrong_password_returns_401(self, client: AsyncClient):
        email = unique_email()
        await register_user(client, email=email)

        resp = await client.post(
            "/auth/login", data={"username": email, "password": "WrongPass!"}
        )

        assert resp.status_code == 401

    @allure.story("Login")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description(
        "Attempting to log in with an email that has never been registered returns 401. "
        "The same status code is used as for a wrong password, preventing enumeration "
        "of valid accounts."
    )
    async def test_login_unknown_email_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/auth/login",
            data={"username": unique_email(), "password": "TestPass123!"},
        )

        assert resp.status_code == 401

    @allure.story("Login")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description(
        "Logging in to an account with is_active=False returns 403 Forbidden with "
        "'Account is inactive'. The user's is_active flag is set directly in the "
        "database to simulate administrative deactivation, since no deactivation "
        "endpoint exists yet."
    )
    async def test_login_inactive_account_returns_403(
        self, client: AsyncClient, db_session
    ):
        email = unique_email()
        await register_user(client, email=email)

        # Deactivate the user directly — there's no API endpoint for this yet.
        # Direct DB manipulation is appropriate here: we're testing the login
        # response to an already-inactive account, not the deactivation flow.
        from app.models.user import User

        user = db_session.query(User).filter(User.email == email).first()
        user.is_active = False
        db_session.commit()

        resp = await client.post(
            "/auth/login", data={"username": email, "password": "TestPass123!"}
        )

        assert resp.status_code == 403
        assert resp.json()["detail"] == "Account is inactive"
