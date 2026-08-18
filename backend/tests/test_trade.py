import pytest
from app.main import app


def get_auth_token(client):
    """Helper — registers a user and returns a valid JWT token."""
    client.post("/auth/register", json={
        "username": "tradeuser",
        "email": "trade@example.com",
        "password": "tradepass123"
    })
    response = client.post("/auth/login", data={
        "username": "tradeuser",
        "password": "tradepass123"
    })
    return response.json()["access_token"]


def test_propose_trade(client):
    """Authenticated user can submit a trade proposal."""
    token = get_auth_token(client)
    response = client.post("/trade/propose",
        json={
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 10.0,
            "risk_score": 4.5,
            "indicator_summary": "RSI=62, MACD bullish crossover, EMA20 > EMA50"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "AAPL"
    assert body["action"].upper() == "BUY"
    assert body["status"].upper() in ["PENDING", "EXECUTED", "APPROVED"]


def test_propose_trade_no_token(client):
    """Unauthenticated request must be rejected with 401."""
    response = client.post("/trade/propose",
        json={
            "symbol": "TSLA",
            "action": "SELL",
            "quantity": 5.0,
            "risk_score": 7.0,
            "indicator_summary": "RSI=78, overbought"
        }
    )
    assert response.status_code == 401


def test_get_proposals(client):
    """Authenticated user can fetch paginated proposals."""
    token = get_auth_token(client)
    response = client.get(
        "/trade/proposals?page=1&page_size=5",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_proposals_no_token(client):
    """Unauthenticated request to proposals must return 401."""
    response = client.get("/trade/proposals")
    assert response.status_code == 401


def test_get_proposals_filter_by_status(client):
    """Filter proposals by status PENDING."""
    token = get_auth_token(client)
    response = client.get(
        "/trade/proposals?status=PENDING",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    body = response.json()
    for proposal in body:
        assert proposal["status"].upper() in ["PENDING", "PENDING_MANUAL"]
