import sys
from pathlib import Path
from uuid import uuid4

# Make the sibling flowstate-api directory importable without requiring a package install.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "flowstate-api"))

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
