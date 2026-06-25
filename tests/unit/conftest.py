"""
Shared fixtures for unit tests.

Environment variables and the redis.Redis patch are applied BEFORE any
user_service module is imported so that:
  1. create_app() finds all required env vars.
  2. user_service.extensions.redis_client uses a MagicMock instead of a
     live Redis connection.
"""
import os
from unittest.mock import MagicMock, patch

# ── Required environment variables ───────────────────────────────────────────
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("MYSQL_USER", "test_user")
os.environ.setdefault("MYSQL_PASSWORD", "test_pass")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("MYSQL_DATABASE", "test_db")
os.environ.setdefault("JWT_SECRET_KEY", "unit-test-jwt-secret")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")

# ── Patch redis.Redis before any user_service module is imported ──────────────
mock_redis_instance = MagicMock()
_redis_patch = patch("redis.Redis", return_value=mock_redis_instance)
_redis_patch.start()

# ── Application imports (safe after env + patch) ──────────────────────────────
import pytest
from sqlalchemy.pool import StaticPool

from user_service.main import create_app
from user_service.extensions.db import db as _db


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app():
    """
    Session-scoped Flask app backed by an in-memory SQLite database.
    StaticPool keeps a single connection alive for the whole test session.
    """
    application = create_app(db_url="sqlite://")
    application.config["TESTING"] = True
    application.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    application.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }
    application.config["JWT_SECRET_KEY"] = "unit-test-jwt-secret"

    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture()
def client(app):
    """Function-scoped test client."""
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app):
    """Roll back and truncate all tables after every test for isolation."""
    with app.app_context():
        yield
        _db.session.rollback()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


@pytest.fixture()
def mock_redis():
    """Return the shared mock Redis instance with a clean call history."""
    mock_redis_instance.reset_mock()
    return mock_redis_instance
