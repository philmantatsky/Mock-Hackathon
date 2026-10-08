"""Shared test setup.

Tests run against the separate mock_hackathon_test database, never the dev one.
The environment is pinned here, before any app module is imported, so a
developer's own backend/.env cannot change what the tests see.
"""

import os

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://localhost/mock_hackathon_test")
os.environ["PHONE_HMAC_KEY"] = "test-only-key-not-used-anywhere-else-0123456789"
os.environ["API_TOKEN"] = ""
os.environ["DEDUP_MERGE_THRESHOLD"] = "0.90"
os.environ["DEDUP_REVIEW_THRESHOLD"] = "0.70"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import SecretStr  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.config import BACKEND_DIR, get_settings  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _migrated_test_database():
    """Rebuild the test database from the real migrations once per run."""
    assert engine.url.database.endswith("_test"), "refusing to wipe a database that is not a test database"
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")


@pytest.fixture(autouse=True)
def _empty_tables(_migrated_test_database):
    """Every test starts with no visits. The seeded locations stay."""
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE review_items, visits, households"))


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def api_token(monkeypatch):
    """Switch the Bearer check on for one test and return the accepted token."""
    monkeypatch.setattr(get_settings(), "api_token", SecretStr("test-token"))
    return "test-token"
