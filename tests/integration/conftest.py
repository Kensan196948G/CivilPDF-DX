"""Integration test fixtures — full-stack API flow tests."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/console/backend"))

# Production-safety validation must see strong test secrets.
os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-value-32bytes-minimum")
os.environ.setdefault("TIMESTAMP_HMAC_KEY", "unit-test-hmac-key-value-32bytes-minimum")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base, get_db
from auth.jwt import get_password_hash
from middleware.rate_limit import reset_all
from models.user import User, UserRole, UserStatus

SQLALCHEMY_TEST_URL = "sqlite:///./test_integration.db"

engine_test = create_engine(
    SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(autouse=True)
def _reset_rate_limiter_between_tests():
    """Keep per-IP counters isolated between tests (TestClient shares 127.0.0.1)."""
    reset_all()
    yield
    reset_all()


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True, scope="package")
def _override_db():
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine_test)
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_user():
    db = TestingSessionLocal()
    user = User(
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        hashed_password=get_password_hash("Admin1234!"),
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture
def admin_token(client, admin_user):
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": "admin@example.com", "password": "Admin1234!"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
