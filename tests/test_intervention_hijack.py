"""
tests/test_intervention_hijack.py
===================================
Day 10 — Tests for Intervention Hijack (override-aware XDI).
Verifies that changing SL/TP/quantity changes the XDI output appropriately.
"""

import pytest
from app.services.signal_engine import generate_override_aware_xdi, generate_xdi


# ── Minimal fake signal for deterministic tests ───────────────────────────────

def _make_signal(symbol="AAPL", direction="BUY", price=150.0):
    return {
        "symbol": symbol,
        "direction": direction,
        "date": "2025-01-15",
        "price_inr": price,
        "rsi": 28.5,
        "macd_line": 0.12,
        "macd_signal": 0.08,
        "macd_histogram": 0.04,
        "ema_20_inr": 148.0,
        "ema_50_inr": 145.0,
        "atr_14_inr": 3.5,
        "risk_score": 4.0,
        "macd_bullish": True,
        "ema_bullish": True,
    }


class TestOverrideAwareXDI:

    def test_base_xdi_generated_without_override(self):
        """generate_xdi must produce a non-empty explanation."""
        signal = _make_signal()
        xdi = generate_xdi(signal)
        assert isinstance(xdi, str)
        assert len(xdi) > 50
        assert "BUY" in xdi

    def test_override_aware_xdi_contains_base_content(self):
        """Override-aware XDI must include the base XDI as a prefix."""
        signal = _make_signal()
        base = generate_xdi(signal)
        override_xdi = generate_override_aware_xdi(signal, {"reason": "testing"})
        assert override_xdi.startswith(base[:50])

    def test_stop_loss_override_appears_in_output(self):
        """Setting stop_loss must appear in the override XDI explanation."""
        signal = _make_signal(price=150.0)
        xdi = generate_override_aware_xdi(signal, {"stop_loss": 140.0, "reason": "tight SL"})
        assert "140.00" in xdi or "140" in xdi
        assert "Stop-loss" in xdi or "stop" in xdi.lower()

    def test_take_profit_override_appears_in_output(self):
        """Setting take_profit must appear in the override XDI explanation."""
        signal = _make_signal(price=150.0)
        xdi = generate_override_aware_xdi(signal, {"take_profit": 165.0, "reason": "TP set"})
        assert "165.00" in xdi or "165" in xdi
        assert "Take-profit" in xdi or "take" in xdi.lower()

    def test_quantity_override_appears_in_output(self):
        """Setting new quantity must appear in the override XDI explanation."""
        signal = _make_signal()
        xdi = generate_override_aware_xdi(signal, {"quantity": 5, "reason": "reduce size"})
        assert "5" in xdi
        assert "Quantity" in xdi or "overridden" in xdi.lower()

    def test_risk_reward_ratio_computed_when_sl_and_tp_set(self):
        """When both SL and TP are set, R:R ratio must appear in output."""
        signal = _make_signal(price=150.0)
        xdi = generate_override_aware_xdi(signal, {
            "stop_loss": 140.0,     # risk $10
            "take_profit": 170.0,   # reward $20 → R:R = 1:2
            "reason": "defined risk"
        })
        assert "Risk:Reward" in xdi or "1:" in xdi

    def test_reason_appears_in_override_output(self):
        """The trader's override reason must be quoted in the explanation."""
        signal = _make_signal()
        xdi = generate_override_aware_xdi(signal, {"reason": "conviction trade"})
        assert "conviction trade" in xdi

    def test_override_section_marker_present(self):
        """The override section must start with the standard marker."""
        signal = _make_signal()
        xdi = generate_override_aware_xdi(signal, {"stop_loss": 145.0, "reason": "test"})
        assert "TRADER OVERRIDE APPLIED" in xdi

    def test_no_override_params_no_override_section(self):
        """Empty override_params dict must not add any override section."""
        signal = _make_signal()
        xdi = generate_override_aware_xdi(signal, {})
        assert "TRADER OVERRIDE APPLIED" not in xdi

    def test_different_sl_produces_different_xdi(self):
        """Two different SL values must produce different XDI output."""
        signal = _make_signal()
        xdi1 = generate_override_aware_xdi(signal, {"stop_loss": 140.0, "reason": "x"})
        xdi2 = generate_override_aware_xdi(signal, {"stop_loss": 130.0, "reason": "x"})
        assert xdi1 != xdi2

    def test_sell_signal_override(self):
        """Override-aware XDI must work for SELL signals too."""
        signal = _make_signal(direction="SELL", price=180.0)
        signal["macd_bullish"] = False
        signal["ema_bullish"] = False
        signal["rsi"] = 75.0
        xdi = generate_override_aware_xdi(signal, {
            "stop_loss": 185.0,
            "take_profit": 170.0,
            "reason": "bearish breakout"
        })
        assert "TRADER OVERRIDE APPLIED" in xdi
        assert "185" in xdi


# ── Integration test for override endpoint ────────────────────────────────────

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _setup_override_scenario(username="overrideusr10", email="ov10@ex.com"):
    client.post("/auth/register", json={"username": username, "email": email, "password": "ovpass123"})
    r = client.post("/auth/login", data={"username": username, "password": "ovpass123"})
    token = r.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    # Propose a trade
    r = client.post("/trade/propose", json={
        "symbol": "AAPL", "action": "BUY", "quantity": 10.0,
        "risk_score": 4.0, "indicator_summary": "RSI=30"
    }, headers=headers)
    proposal_id = r.json()["id"]
    return token, headers, proposal_id


class TestOverrideEndpoint:

    def test_override_returns_xdi_after_override_field(self):
        """POST /trade/{id}/override must return xdi_after_override field."""
        _, headers, pid = _setup_override_scenario("ov10a", "ov10a@ex.com")
        r = client.post(f"/trade/{pid}/override", json={
            "stop_loss": 140.0,
            "take_profit": 165.0,
            "reason": "Setting tighter risk parameters"
        }, headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "xdi_after_override" in body
        # xdi_after_override can be None if signal pipeline doesn't fire, but field must exist

    def test_override_sl_tp_stored_correctly(self):
        """Override must persist SL and TP in the response."""
        _, headers, pid = _setup_override_scenario("ov10b", "ov10b@ex.com")
        r = client.post(f"/trade/{pid}/override", json={
            "stop_loss": 138.0,
            "take_profit": 158.0,
            "reason": "Adjusted levels"
        }, headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert body["stop_loss"] == 138.0
        assert body["take_profit"] == 158.0

    def test_invalid_sl_tp_returns_422(self):
        """Override where SL >= TP must be rejected."""
        _, headers, pid = _setup_override_scenario("ov10c", "ov10c@ex.com")
        r = client.post(f"/trade/{pid}/override", json={
            "stop_loss": 170.0,
            "take_profit": 150.0,  # SL > TP — invalid
            "reason": "Bad params"
        }, headers=headers)
        assert r.status_code == 422
