"""
Shared test fixtures for ORION Architekt-AT test suite.
Provides database isolation with transaction rollback after each test.
"""

import os

import pytest


def pytest_configure(config):
    """Set up test environment variables before any test modules are imported.

    This hook runs before test collection and module imports, ensuring that
    the correct DATABASE_URL is set before api.main is imported and calls
    Base.metadata.create_all().
    """
    # Fall back to SQLite when no explicit database URL is provided
    os.environ.setdefault("DATABASE_URL", "sqlite:///./test_orion.db")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")
    os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-do-not-use-in-production")
    os.environ.setdefault("TESTING", "true")


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all database tables once per test session and clean up afterwards."""
    from api.database import Base, engine

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

    # Remove SQLite test database file if it was created
    db_url = os.environ.get("DATABASE_URL", "")
    if "sqlite" in db_url and "test_orion.db" in db_url:
        if os.path.exists("test_orion.db"):
            os.remove("test_orion.db")


@pytest.fixture
def db_session(setup_database):
    """Provide a transactional database session that rolls back after each test.

    Each test function gets a fresh transaction that is rolled back on teardown,
    ensuring complete isolation between tests without recreating the schema.
    """
    from sqlalchemy.orm import Session

    from api.database import engine

    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()
