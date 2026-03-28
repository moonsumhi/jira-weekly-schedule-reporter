"""
Test configuration and fixtures for backoffice tests.
Uses mongomock_motor for async MongoDB mocking.
"""
import os
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from bson import ObjectId

# Set env vars before importing app modules that load Settings.
# Remove any extra vars that pydantic-settings would reject.
for _extra in ("APP_DB_USER", "APP_DB_PASS"):
    os.environ.pop(_extra, None)

os.environ.setdefault("JIRA_BASE_URL", "https://test.atlassian.net")
os.environ.setdefault("JIRA_EMAIL", "test@test.com")
os.environ.setdefault("JIRA_API_TOKEN", "test_token")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("JWT_SECRET_KEY", "testsecretkey1234567890")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("APP_DB_NAME", "test_backoffice")

import mongomock_motor
from fastapi.testclient import TestClient

from app.main import app
from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.core.security import hash_password, create_access_token
from app.routers.auth import get_current_user


# ── Mock MongoDB client ─────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_mongo(monkeypatch):
    """Replace MongoClientManager with an in-memory mongomock client."""
    mock_client = mongomock_motor.AsyncMongoMockClient()
    monkeypatch.setattr(MongoClientManager, "_client", mock_client)
    yield mock_client
    # cleanup: close mock (no-op for mongomock)


# ── Auth helpers ────────────────────────────────────────────────────────────

def make_token(email: str) -> str:
    return create_access_token(subject=email)


ADMIN_EMAIL = "admin@test.com"
USER_EMAIL = "user@test.com"


@pytest.fixture
def admin_user() -> UserPublic:
    return UserPublic(id=str(ObjectId()), email=ADMIN_EMAIL, full_name="Admin", is_admin=True)


@pytest.fixture
def regular_user() -> UserPublic:
    return UserPublic(id=str(ObjectId()), email=USER_EMAIL, full_name="User", is_admin=False)


@pytest.fixture
def admin_client(admin_user):
    """TestClient authenticated as admin."""
    app.dependency_overrides[get_current_user] = lambda: admin_user
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def user_client(regular_user):
    """TestClient authenticated as regular (non-admin) user."""
    app.dependency_overrides[get_current_user] = lambda: regular_user
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def anon_client():
    """Unauthenticated TestClient."""
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        yield client


# ── DB seed helpers ─────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def pending_user_id(mock_mongo):
    """Insert a PENDING user into the mock DB and return its _id string."""
    db = mock_mongo[os.environ["APP_DB_NAME"]]
    result = await db["pending_users"].insert_one({
        "email": "pending@test.com",
        "full_name": "Pending User",
        "hashed_password": hash_password("password123"),
        "status": "PENDING",
        "requested_at": datetime.now(timezone.utc),
        "reviewed_at": None,
        "reviewed_by": None,
        "reject_reason": None,
    })
    return str(result.inserted_id)


@pytest_asyncio.fixture
async def approved_user_id(mock_mongo):
    """Insert an APPROVED pending entry into the mock DB."""
    db = mock_mongo[os.environ["APP_DB_NAME"]]
    result = await db["pending_users"].insert_one({
        "email": "approved@test.com",
        "full_name": "Approved User",
        "hashed_password": hash_password("password123"),
        "status": "APPROVED",
        "requested_at": datetime.now(timezone.utc),
        "reviewed_at": datetime.now(timezone.utc),
        "reviewed_by": ADMIN_EMAIL,
        "reject_reason": None,
    })
    return str(result.inserted_id)


@pytest_asyncio.fixture
async def rejected_user_id(mock_mongo):
    """Insert a REJECTED pending entry into the mock DB."""
    db = mock_mongo[os.environ["APP_DB_NAME"]]
    result = await db["pending_users"].insert_one({
        "email": "rejected@test.com",
        "full_name": "Rejected User",
        "hashed_password": hash_password("password123"),
        "status": "REJECTED",
        "requested_at": datetime.now(timezone.utc),
        "reviewed_at": datetime.now(timezone.utc),
        "reviewed_by": ADMIN_EMAIL,
        "reject_reason": "Policy violation",
    })
    return str(result.inserted_id)
