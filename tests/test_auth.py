import allure
from httpx import AsyncClient

from helpers.factories import login, register_user, unique_email


@allure.feature("Auth")
class TestRegister:
    @allure.story("Register")
    @allure.severity(allure.severity_level.CRITICAL)
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
    async def test_register_duplicate_email_returns_409(self, client: AsyncClient):
        email = unique_email()
        await register_user(client, email=email)

        resp = await register_user(client, email=email)

        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    @allure.story("Register")
    @allure.severity(allure.severity_level.MINOR)
    async def test_register_invalid_email_returns_422(self, client: AsyncClient):
        resp = await register_user(client, email="not-an-email")

        assert resp.status_code == 422


@allure.feature("Auth")
class TestLogin:
    @allure.story("Login")
    @allure.severity(allure.severity_level.CRITICAL)
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
    async def test_login_wrong_password_returns_401(self, client: AsyncClient):
        email = unique_email()
        await register_user(client, email=email)

        resp = await client.post(
            "/auth/login", data={"username": email, "password": "WrongPass!"}
        )

        assert resp.status_code == 401

    @allure.story("Login")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_login_unknown_email_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/auth/login",
            data={"username": unique_email(), "password": "TestPass123!"},
        )

        assert resp.status_code == 401

    @allure.story("Login")
    @allure.severity(allure.severity_level.CRITICAL)
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
