"""
Thin async helpers that wrap the flowstate-api endpoints.

Each function makes exactly one HTTP call and returns the parsed JSON body.
They exist solely to keep test bodies readable — setup noise stays here,
assertions stay in the tests.
"""

from uuid import uuid4

from httpx import AsyncClient


def unique_email() -> str:
    return f"user_{uuid4().hex[:8]}@example.com"


async def register_user(
    client: AsyncClient,
    email: str | None = None,
    password: str = "TestPass123!",
) -> dict:
    """POST /auth/register — returns the UserResponse dict."""
    payload = {"email": email or unique_email(), "password": password}
    resp = await client.post("/auth/register", json=payload)
    return resp


async def login(
    client: AsyncClient,
    email: str,
    password: str = "TestPass123!",
) -> str:
    """POST /auth/login — returns the raw bearer token string."""
    resp = await client.post(
        "/auth/login", data={"username": email, "password": password}
    )
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    """Build the Authorization header dict from a bearer token."""
    return {"Authorization": f"Bearer {token}"}


async def create_task(
    client: AsyncClient,
    headers: dict,
    title: str = "Test task",
    **overrides,
) -> dict:
    """POST /tasks — returns the TaskResponse dict."""
    payload = {"title": title, **overrides}
    resp = await client.post("/tasks", json=payload, headers=headers)
    return resp
