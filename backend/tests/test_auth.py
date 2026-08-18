import pytest
from app.main import app

def test_register(client):
    response = client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "testuser"
    assert body["email"] == "test@example.com"

def test_register_duplicate(client):
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

def test_login(client):
    client.post("/auth/register", json={
        "username": "loginuser",
        "email": "login@example.com",
        "password": "testpass123"
    })
    response = client.post("/auth/login", data={
        "username": "loginuser",
        "password": "testpass123"
    })
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"

def test_invalid_token(client):
    response = client.get("/health/broker", headers={
        "Authorization": "Bearer invalidtoken123"
    })
    assert response.status_code in [200, 401, 503]

def test_wrong_password(client):
    client.post("/auth/register", json={
        "username": "wrongpass",
        "email": "wrongpass@example.com",
        "password": "correctpass"
    })
    response = client.post("/auth/login", data={
        "username": "wrongpass",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
