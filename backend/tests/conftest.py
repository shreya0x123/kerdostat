import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Enforce mock mode for all test suite runs
os.environ["MOCK_ALPACA"] = "true"
os.environ["MOCK_FYERS"] = "true"

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app, Base, get_db

from sqlalchemy.pool import StaticPool

TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(autouse=True)
def enforce_mock_mode(monkeypatch):
    monkeypatch.setenv("MOCK_ALPACA", "true")
    monkeypatch.setenv("MOCK_FYERS", "true")

@pytest.fixture(name="db")
def session_fixture():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(name="client")
def client_fixture(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture(name="auth_client")
def auth_client_fixture(client):
    client.post("/auth/register", json={
        "name": "Test Trader",
        "email": "test@trader.com",
        "password": "securepassword"
    })
    client.post("/auth/login", json={
        "email": "test@trader.com",
        "password": "securepassword"
    })
    return client
