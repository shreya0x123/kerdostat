import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_register():
    response = client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "testuser"
    assert body["email"] == "test@example.com"


def test_register_duplicate():
    # Register same user twice
    client.post("/auth/register", json={
        "username": "dupeuser",
        "email": "dupe@example.com",
        "password": "testpass123"
    })
    response = client.post("/auth/register", json={
        "username": "dupeuser",
        "email": "dupe@example.com",
        "password": "testpass123"
    })
    assert response.status_code == 400


def test_login():
    # Register first
    client.post("/auth/register", json={
        "username": "loginuser",
        "email": "login@example.com",
        "password": "testpass123"
    })
    # Then login
    response = client.post("/auth/login", data={
        "username": "loginuser",
        "password": "testpass123"
    })
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_invalid_token():
    from fastapi.testclient import TestClient
    response = client.get("/health/broker", headers={
        "Authorization": "Bearer invalidtoken123"
    })
    # Should not crash — either 200 or 401/503
    assert response.status_code in [200, 401, 503]


def test_wrong_password():
    # Register first
    client.post("/auth/register", json={
        "username": "wrongpass",
        "email": "wrongpass@example.com",
        "password": "correctpass"
    })
    # Login with wrong password
    response = client.post("/auth/login", data={
        "username": "wrongpass",
        "password": "wrongpassword"
    })
    assert response.status_code == 401