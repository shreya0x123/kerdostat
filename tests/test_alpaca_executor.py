"""
tests/test_alpaca_executor.py
==============================
Day 8 — Tests for AlpacaExecutor (mock mode).

All tests run with ALPACA_MOCK_MODE=true so no real Alpaca credentials are needed.
"""

import os
import pytest

# Force mock mode before importing the executor module
os.environ["ALPACA_MOCK_MODE"] = "true"

from app.services.alpaca_executor import AlpacaExecutor, OrderResult, FillStatus


@pytest.fixture(autouse=True)
def mock_executor():
    """Always return a fresh mock-mode executor."""
    os.environ["ALPACA_MOCK_MODE"] = "true"
    return AlpacaExecutor()


# ── AlpacaExecutor unit tests (mock mode) ─────────────────────────────────────

class TestAlpacaExecutorMockMode:

    def setup_method(self):
        os.environ["ALPACA_MOCK_MODE"] = "true"
        self.executor = AlpacaExecutor()

    def test_is_mock_true_when_env_set(self):
        """Executor must report mock mode when ALPACA_MOCK_MODE=true."""
        assert self.executor.is_mock is True

    def test_submit_buy_returns_order_result(self):
        """submit_buy must return an OrderResult with a valid order_id."""
        result = self.executor.submit_buy("AAPL", 10)
        assert isinstance(result, OrderResult)
        assert result.order_id != ""
        assert result.symbol == "AAPL"
        assert result.side == "buy"
        assert result.qty == 10
        assert result.status == "accepted"
        assert result.mock is True

    def test_submit_sell_returns_order_result(self):
        """submit_sell must return an OrderResult."""
        result = self.executor.submit_sell("TSLA", 5)
        assert isinstance(result, OrderResult)
        assert result.order_id != ""
        assert result.symbol == "TSLA"
        assert result.side == "sell"
        assert result.qty == 5
        assert result.status == "accepted"
        assert result.mock is True

    def test_submit_buy_zero_qty_raises(self):
        """Submitting qty=0 must raise ValueError."""
        with pytest.raises(ValueError, match="qty must be positive"):
            self.executor.submit_buy("AAPL", 0)

    def test_submit_sell_negative_qty_raises(self):
        """Submitting negative qty must raise ValueError."""
        with pytest.raises(ValueError, match="qty must be positive"):
            self.executor.submit_sell("AAPL", -1)

    def test_poll_order_status_returns_filled(self):
        """After submitting, polling the order should return 'filled'."""
        order = self.executor.submit_buy("MSFT", 3)
        status = self.executor.poll_order_status(order.order_id)
        assert status == "filled"

    def test_poll_order_status_unknown_id(self):
        """Polling a non-existent order_id returns 'unknown'."""
        status = self.executor.poll_order_status("nonexistent-uuid-0000")
        assert status == "unknown"

    def test_get_fill_status_returns_fill_status(self):
        """get_fill_status must return a FillStatus dataclass."""
        order = self.executor.submit_sell("NVDA", 2)
        fill = self.executor.get_fill_status(order.order_id)
        assert isinstance(fill, FillStatus)
        assert fill.order_id == order.order_id
        assert fill.status == "filled"
        assert fill.filled_qty == 2
        assert fill.avg_fill_price is not None
        assert fill.mock is True

    def test_get_fill_status_unknown_id(self):
        """get_fill_status for unknown order returns status='unknown'."""
        fill = self.executor.get_fill_status("unknown-order-id")
        assert fill.status == "unknown"
        assert fill.filled_qty == 0.0
        assert fill.avg_fill_price is None

    def test_multiple_orders_independent(self):
        """Two separate orders must have different order IDs."""
        a = self.executor.submit_buy("AAPL", 1)
        b = self.executor.submit_buy("AAPL", 1)
        assert a.order_id != b.order_id

    def test_symbol_uppercased(self):
        """Symbol must be stored upper-case regardless of input."""
        result = self.executor.submit_buy("aapl", 1)
        assert result.symbol == "AAPL"


# ── Integration test via FastAPI client ───────────────────────────────────────

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _auth_token(username="execuser8", email="exec8@example.com", password="execpass123"):
    client.post("/auth/register", json={"username": username, "email": email, "password": password})
    r = client.post("/auth/login", data={"username": username, "password": password})
    return r.json().get("access_token", "")


def _propose(token, symbol="AAPL", action="BUY", qty=10.0, risk=4.0):
    r = client.post(
        "/trade/propose",
        json={"symbol": symbol, "action": action, "quantity": qty,
              "risk_score": risk, "indicator_summary": "RSI=55, MACD bullish"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


class TestExecuteEndpoint:

    def setup_method(self):
        os.environ["ALPACA_MOCK_MODE"] = "true"

    def test_execute_buy_proposal_succeeds(self):
        """POST /trade/execute on a valid PENDING BUY proposal returns 200."""
        token = _auth_token("ex8buy", "ex8buy@ex.com")
        pid = _propose(token, "AAPL", "BUY")
        r = client.post(
            "/trade/execute",
            json={"proposal_id": pid},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "executed"
        assert body["order_id"] != ""
        assert body["symbol"] == "AAPL"
        assert body["action"] == "BUY"
        assert body["fill_status"] == "filled"
        assert body["mock_mode"] is True

    def test_execute_sell_proposal_succeeds(self):
        """POST /trade/execute on a valid PENDING SELL proposal returns 200."""
        token = _auth_token("ex8sell", "ex8sell@ex.com")
        pid = _propose(token, "TSLA", "SELL")
        r = client.post(
            "/trade/execute",
            json={"proposal_id": pid},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "executed"
        assert body["fill_status"] == "filled"

    def test_execute_same_proposal_twice_fails(self):
        """Executing an already-executed proposal must return 400."""
        token = _auth_token("ex8twice", "ex8twice@ex.com")
        pid = _propose(token, "MSFT", "BUY")
        client.post("/trade/execute", json={"proposal_id": pid},
                    headers={"Authorization": f"Bearer {token}"})
        r = client.post("/trade/execute", json={"proposal_id": pid},
                        headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 400

    def test_execute_nonexistent_proposal_returns_404(self):
        """Executing a non-existent proposal_id must return 404."""
        token = _auth_token("ex8none", "ex8none@ex.com")
        r = client.post("/trade/execute", json={"proposal_id": 999999},
                        headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 404

    def test_execute_without_token_returns_401(self):
        """Unauthenticated execute request must return 401."""
        r = client.post("/trade/execute", json={"proposal_id": 1})
        assert r.status_code == 401
