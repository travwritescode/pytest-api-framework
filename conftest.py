import sys
import os
from datetime import date
from pathlib import Path
from uuid import uuid4

# Make the sibling flowstate-api directory importable without requiring a package install.
sys.path.insert(0, os.environ.get(
    "FLOWSTATE_API_PATH",
    str(Path(__file__).resolve().parent.parent / "flowstate-api")
))


import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models.task  # noqa: F401 — registers Task with Base.metadata
import app.models.user  # noqa: F401 — registers User with Base.metadata
from app.database import Base
from app.dependencies import get_db
from app.main import app
from helpers.factories import create_task

# ---------------------------------------------------------------------------
# DB isolation strategy
#
# Every test gets its own throwaway SQLite database spun up inside db_session
# and torn down immediately after the test completes. Nothing persists between
# tests.
#
# Key decisions:
#   - sqlite:///:memory:  — zero-cost, no disk I/O, no cleanup scripts needed.
#   - StaticPool          — forces SQLAlchemy to reuse the same connection for
#                           the lifetime of the engine. Without this, httpx's
#                           ASGI transport and the test's own session can end up
#                           on different connections, which means the in-memory
#                           database appears empty to one of them.
#   - PRAGMA foreign_keys=ON — SQLite ignores FK constraints by default; this
#                           enables them so FK violations surface during tests.
#   - Base.metadata.drop_all on teardown — ensures the schema is wiped after
#                           each test so no residual rows can bleed across.
#
# Fixture dependency chain:
#   db_session
#     └── client                   (overrides get_db with the test session)
#           ├── registered_user    (POST /auth/register — unique email per test)
#           │     └── auth_headers (POST /auth/login — returns Bearer token)
#           │           └── seeded_task (POST /tasks via factories.create_task)
#           └── second_user        (second isolated user for cross-user tests)
#                 └── other_auth_headers
# ---------------------------------------------------------------------------


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
async def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def registered_user(client):
    """Registers a unique user and returns (email, password)."""
    email = f"user_{uuid4().hex[:8]}@example.com"
    password = "TestPass123!"
    resp = await client.post("/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text
    return email, password


@pytest.fixture
async def auth_headers(client, registered_user):
    """Returns Bearer auth headers for a freshly registered and logged-in user."""
    email, password = registered_user
    resp = await client.post(
        "/auth/login", data={"username": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def second_user(client):
    """Registers a second unique user and returns (email, password)."""
    email = f"user_{uuid4().hex[:8]}@example.com"
    password = "TestPass123!"
    resp = await client.post("/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text
    return email, password


@pytest.fixture
async def other_auth_headers(client, second_user):
    """Returns Bearer auth headers for the second registered user."""
    email, password = second_user
    resp = await client.post(
        "/auth/login", data={"username": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def seeded_task(client, auth_headers):
    """Seeds a single task owned by the auth_headers user and returns the response JSON."""
    resp = await create_task(
        client,
        auth_headers,
        title="Auto Task",
        description="This is a task created by test automation",
        status="todo",
        priority="low",
        due_date=date.today().isoformat()
    )
    assert resp.status_code == 201, resp.text
    return resp.json()
