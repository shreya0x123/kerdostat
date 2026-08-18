import os
import pytest

from app.main import app
from app.core.config import settings


# ------------------------------------------------------------------
# Liveness — always passes
# ------------------------------------------------------------------

def test_liveness(client):
    """GET /health should always return 200."""
    resp = client.get("/health/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


# ------------------------------------------------------------------
# Broker smoke test — behaviour depends on env credentials
# ------------------------------------------------------------------

class TestBrokerSmokeTest:
    """
    Grouped so we can skip gracefully when no credentials are configured.
    """

    def test_broker_health_no_credentials(self, client, monkeypatch):
        """
        When credentials are missing, /health/broker must return 503
        with a human-readable detail — never a 500.
        """
        monkeypatch.setattr(settings, "ALPACA_API_KEY", "")
        monkeypatch.setattr(settings, "ALPACA_SECRET_KEY", "")

        resp = client.get("/health/broker")
        assert resp.status_code == 503
        detail = resp.json()["detail"]
        assert "ALPACA_API_KEY" in detail or "credentials" in detail.lower()

    @pytest.mark.skipif(
        not (os.getenv("ALPACA_API_KEY") and os.getenv("ALPACA_SECRET_KEY")),
        reason="ALPACA_API_KEY / ALPACA_SECRET_KEY not set — skipping live smoke test",
    )
    def test_broker_health_live(self, client):
        """
        Live test — only runs when real credentials exist.
        Asserts every field in the AccountSnapshot is present and sane.
        """
        resp = client.get("/health/broker")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        body = resp.json()

        # Connection status
        assert body["status"] == "connected"

        # Account must be active
        assert body["account_status"] == "ACTIVE", (
            f"Account is not ACTIVE: {body['account_status']}"
        )

        # Paper trading flag — we always use paper in this project
        assert body["paper_trading"] is True, (
            "Expected paper trading account — live credentials should not be used."
        )

        # Numeric fields must be non-negative
        for field in ("equity", "cash", "buying_power", "portfolio_value"):
            assert body[field] >= 0, f"{field} should be >= 0, got {body[field]}"

        # Currency sanity
        assert body["currency"] == "USD"

        # Account number must be a non-empty string
        assert isinstance(body["account_number"], str) and body["account_number"]

        print("\n✅ Alpaca smoke test passed:")
        print(f"   Account : {body['account_number']}")
        print(f"   Status  : {body['account_status']}")
        print(f"   Equity  : ${body['equity']:,.2f}")
        print(f"   Cash    : ${body['cash']:,.2f}")
