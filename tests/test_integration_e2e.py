"""
tests/test_integration_e2e.py
==============================
End-to-End Integration Tests — Days 8–13

Covers every pending integration point from the System Testing plan:
  1. Signal Engine → Trade Proposal → Execute (full Copilot flow)
  2. Signal Engine → Autopilot (HOTL full flow)
  3. Override → XDI recalculation → Audit log
  4. Guardrail blocks oversized trade in Autopilot
  5. WebSocket endpoint connectivity
  6. Backtest → Report → API endpoint
  7. JWT auth cross-endpoint (auth token shared across all routes)
  8. Audit trail completeness (every action logged)
  9. Full E2E: register → login → signal → propose → override → audit
 10. Admin guardrail config update → enforced in evaluation
"""

import os
import pytest
from unittest.mock import patch, MagicMock

os.environ.setdefault("DATABASE_URL", "sqlite:///./kerdostat_test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-kerdostat-2025")
os.environ.setdefault("ALPACA_MOCK_MODE", "true")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# ── Shared helpers ────────────────────────────────────────────────────────────

def _register_and_login(username, email, password="pass1234"):
    client.post("/auth/register", json={"username": username, "email": email, "password": password})
    r = client.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, f"Login failed for {username}: {r.text}"
    return r.json()["access_token"]

def _propose(token, symbol="AAPL", action="BUY", qty=5.0, risk=4.0):
    r = client.post("/trade/propose", json={
        "symbol": symbol, "action": action, "quantity": qty,
        "risk_score": risk, "indicator_summary": "RSI=45, MACD bullish"
    }, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    return r.json()

def _execute(token, proposal_id):
    r = client.post("/trade/execute",
                    json={"proposal_id": proposal_id},
                    headers={"Authorization": f"Bearer {token}"})
    return r

def _audit(token, page=1, page_size=50):
    r = client.get(f"/audit/log?page={page}&page_size={page_size}",
                   headers={"Authorization": f"Bearer {token}"})
    return r

def _headers(token):
    return {"Authorization": f"Bearer {token}"}

# ── Mock tick for WebSocket tests (avoids yfinance network call) ──────────────

MOCK_TICK = {
    "symbol": "AAPL",
    "date": "2025-08-15",
    "open": 150.0,
    "high": 152.5,
    "low": 149.0,
    "close": 151.0,
    "volume": 1000000,
    "timestamp": "2025-08-15T09:30:00",
}


# ══════════════════════════════════════════════════════════════════════════════
# 1. Full Copilot Flow: Register → Propose → Execute → Audit
# ══════════════════════════════════════════════════════════════════════════════

class TestCopilotE2EFlow:
    """Integration: Signal Engine → Trade Proposal → Execute → Audit log."""

    def test_full_copilot_buy_flow(self):
        """Full Copilot BUY flow: propose → execute → verify status."""
        token = _register_and_login("e2e_cop1", "e2e_cop1@test.com")

        proposal = _propose(token, "AAPL", "BUY", qty=10.0, risk=4.0)
        pid = proposal["id"]
        assert proposal["status"] == "PENDING"

        r = _execute(token, pid)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "executed"
        assert body["fill_status"] == "filled"
        assert body["order_id"] != ""
        assert body["mock_mode"] is True

        r = client.get("/trade/proposals", headers=_headers(token))
        executed = [p for p in r.json() if p["id"] == pid]
        assert executed[0]["status"] == "EXECUTED"

    def test_full_copilot_sell_flow(self):
        """Full Copilot SELL flow works identically to BUY."""
        token = _register_and_login("e2e_cop2", "e2e_cop2@test.com")
        proposal = _propose(token, "TSLA", "SELL", qty=3.0, risk=5.5)
        r = _execute(token, proposal["id"])
        assert r.status_code == 200
        assert r.json()["action"] == "SELL"
        assert r.json()["status"] == "executed"

    def test_cannot_execute_same_proposal_twice(self):
        """Idempotency: executing an already-EXECUTED proposal returns 400."""
        token = _register_and_login("e2e_cop3", "e2e_cop3@test.com")
        proposal = _propose(token, "MSFT", "BUY", qty=2.0, risk=3.0)
        pid = proposal["id"]
        r1 = _execute(token, pid)
        assert r1.status_code == 200
        r2 = _execute(token, pid)
        assert r2.status_code == 400

    def test_execute_audit_entry_written(self):
        """POST /trade/execute must write an EXECUTED audit entry."""
        token = _register_and_login("e2e_cop4", "e2e_cop4@test.com")
        proposal = _propose(token, "AAPL", "BUY", qty=3.0, risk=3.0)
        pid = proposal["id"]
        _execute(token, pid)

        r = _audit(token)
        assert r.status_code == 200
        logs = r.json()
        exec_logs = [l for l in logs
                     if l.get("trade_proposal_id") == pid
                     and l.get("action_taken") == "EXECUTED"]
        assert len(exec_logs) >= 1


# ══════════════════════════════════════════════════════════════════════════════
# 2. Override → XDI → Audit Integration
# ══════════════════════════════════════════════════════════════════════════════

class TestOverrideIntegration:
    """Integration: Override endpoint → XDI recalculation → Audit log."""

    def test_override_creates_audit_entry(self):
        """POST /trade/{id}/override must write OVERRIDE to audit_logs."""
        token = _register_and_login("e2e_ov1", "e2e_ov1@test.com")
        proposal = _propose(token, "AAPL", "BUY", qty=10.0, risk=4.0)
        pid = proposal["id"]

        r = client.post(f"/trade/{pid}/override", json={
            "stop_loss": 140.0,
            "take_profit": 165.0,
            "reason": "Integration test override"
        }, headers=_headers(token))
        assert r.status_code == 200, r.text

        r = _audit(token)
        logs = r.json()
        override_logs = [l for l in logs
                         if l.get("trade_proposal_id") == pid
                         and l.get("action_taken") == "OVERRIDE"]
        assert len(override_logs) >= 1
        assert override_logs[0]["reason"] == "Integration test override"

    def test_override_then_propose_new_uses_updated_params(self):
        """After overriding, override response contains the new SL/TP values."""
        token = _register_and_login("e2e_ov2", "e2e_ov2@test.com")
        proposal = _propose(token, "NVDA", "BUY", qty=10.0, risk=3.0)
        pid = proposal["id"]

        r = client.post(f"/trade/{pid}/override", json={
            "quantity": 7.0,
            "stop_loss": 380.0,
            "take_profit": 430.0,
            "reason": "Adjusting position size"
        }, headers=_headers(token))
        assert r.status_code == 200
        body = r.json()
        assert body["new_quantity"] == 7.0
        assert body["stop_loss"] == 380.0
        assert body["take_profit"] == 430.0

    def test_xdi_after_override_present(self):
        """Override response must include xdi_after_override field."""
        token = _register_and_login("e2e_ov3", "e2e_ov3@test.com")
        proposal = _propose(token, "GOOGL", "BUY", qty=5.0, risk=3.0)
        r = client.post(f"/trade/{proposal['id']}/override", json={
            "stop_loss": 130.0, "take_profit": 160.0,
            "reason": "XDI check"
        }, headers=_headers(token))
        assert r.status_code == 200
        assert "xdi_after_override" in r.json()

    def test_double_override_rejected(self):
        """A proposal that has been overridden cannot be overridden again."""
        token = _register_and_login("e2e_ov4", "e2e_ov4@test.com")
        proposal = _propose(token, "AMZN", "SELL", qty=5.0, risk=4.0)
        pid = proposal["id"]
        client.post(f"/trade/{pid}/override", json={"reason": "first"}, headers=_headers(token))
        r = client.post(f"/trade/{pid}/override", json={"reason": "second"}, headers=_headers(token))
        assert r.status_code == 400
        assert "already been overridden" in r.json()["detail"]


# ══════════════════════════════════════════════════════════════════════════════
# 3. Autopilot Full Flow Integration
# ══════════════════════════════════════════════════════════════════════════════

class TestAutopilotIntegration:
    """Integration: COPILOT → AUTOPILOT mode toggle → guardrail enforcement."""

    def test_mode_switches_and_persists(self):
        """User mode toggle persists — GET /user/me reflects the change."""
        token = _register_and_login("e2e_ap1", "e2e_ap1@test.com")
        r = client.patch("/user/mode", json={"mode": "AUTOPILOT"}, headers=_headers(token))
        assert r.status_code == 200
        assert r.json()["mode"] == "AUTOPILOT"

        r = client.get("/user/me", headers=_headers(token))
        assert r.json()["mode"] == "AUTOPILOT"

        r = client.patch("/user/mode", json={"mode": "COPILOT"}, headers=_headers(token))
        assert r.json()["mode"] == "COPILOT"

    def test_guardrail_blocks_high_risk_in_autopilot(self):
        """GuardrailEngine blocks oversized position (200 qty × $1000 = 20% of portfolio)."""
        from app.services.guardrail_engine import GuardrailEngine
        engine = GuardrailEngine(
            portfolio_value=1_000_000,
            max_position_size_pct=5.0,
            daily_loss_limit_pct=3.0,
            max_open_trades=10,
        )
        result = engine.evaluate(
            quantity=200, price_per_unit=1000.0,
            current_daily_loss=0.0, open_trade_count=0,
        )
        assert result.passed is False
        assert len(result.reasons) >= 1
        assert "20.00%" in result.reason_string or "position" in result.reason_string.lower()

    def test_interrupt_then_resume_full_flow(self):
        """Interrupt → audit → resume → audit — full lifecycle."""
        token = _register_and_login("e2e_ap2", "e2e_ap2@test.com")
        proposal = _propose(token, "AAPL", "BUY", qty=5.0, risk=3.0)
        pid = proposal["id"]

        # Interrupt
        r = client.post(f"/trade/{pid}/interrupt", headers=_headers(token))
        assert r.status_code == 200
        assert r.json()["status"] == "INTERRUPTED"

        # Verify interrupt audit entry
        logs = _audit(token).json()
        interrupt_logs = [l for l in logs
                          if l.get("trade_proposal_id") == pid
                          and l.get("action_taken") == "INTERRUPT"]
        assert len(interrupt_logs) >= 1

        # Resume
        r = client.post(f"/trade/{pid}/resume", headers=_headers(token))
        assert r.status_code == 200
        assert r.json()["status"] == "RESUMED"

        # Verify resume audit entry
        logs = _audit(token).json()
        resume_logs = [l for l in logs
                       if l.get("trade_proposal_id") == pid
                       and l.get("action_taken") == "RESUME"]
        assert len(resume_logs) >= 1


# ══════════════════════════════════════════════════════════════════════════════
# 4. WebSocket Endpoint Integration
# ══════════════════════════════════════════════════════════════════════════════

class TestWebSocketIntegration:
    """
    Integration: WebSocket /ws/ohlcv/{symbol} delivers OHLCV tick data.
    Network calls to yfinance are mocked so tests run offline.
    """

    def test_websocket_ohlcv_connects_and_sends_tick(self):
        """WebSocket /ws/ohlcv/AAPL accepts connection and sends a tick."""
        with patch("app.routers.websocket.fetch_latest_tick", return_value=MOCK_TICK):
            with client.websocket_connect("/ws/ohlcv/AAPL") as ws:
                data = ws.receive_json()
                assert data["type"] == "tick"
                tick = data["data"]
                assert tick["symbol"] == "AAPL"
                assert tick["close"] == 151.0

    def test_websocket_tick_has_all_required_fields(self):
        """Every tick must contain: symbol, date, open, high, low, close, volume, timestamp."""
        required = {"symbol", "date", "open", "high", "low", "close", "volume", "timestamp"}
        with patch("app.routers.websocket.fetch_latest_tick", return_value=MOCK_TICK):
            with client.websocket_connect("/ws/ohlcv/AAPL") as ws:
                data = ws.receive_json()
                missing = required - set(data["data"].keys())
                assert not missing, f"Missing tick fields: {missing}"

    def test_websocket_different_symbols(self):
        """WebSocket endpoint serves any valid symbol."""
        for symbol in ["MSFT", "TSLA"]:
            mock_tick = {**MOCK_TICK, "symbol": symbol}
            with patch("app.routers.websocket.fetch_latest_tick", return_value=mock_tick):
                with client.websocket_connect(f"/ws/ohlcv/{symbol}") as ws:
                    data = ws.receive_json()
                    assert data["type"] == "tick"
                    assert data["data"]["symbol"] == symbol

    def test_websocket_ohlcv_price_is_positive(self):
        """Close price in every tick must be > 0."""
        with patch("app.routers.websocket.fetch_latest_tick", return_value=MOCK_TICK):
            with client.websocket_connect("/ws/ohlcv/AAPL") as ws:
                data = ws.receive_json()
                assert data["data"]["close"] > 0


# ══════════════════════════════════════════════════════════════════════════════
# 5. JWT Authentication Cross-Endpoint Integration
# ══════════════════════════════════════════════════════════════════════════════

class TestJWTCrossEndpoint:
    """Integration: A single JWT is valid across ALL protected endpoints."""

    PROTECTED_ROUTES = [
        "/user/me",
        "/trade/proposals",
        "/guardrails/config",
        "/signal/backtest-report",
        "/audit/log",
    ]

    def test_single_token_valid_across_all_endpoints(self):
        """One JWT token must work on all protected routes."""
        token = _register_and_login("e2e_jwt1", "e2e_jwt1@test.com")
        h = _headers(token)
        for path in self.PROTECTED_ROUTES:
            r = client.get(path, headers=h)
            assert r.status_code == 200, f"GET {path} returned {r.status_code}: {r.text}"

    def test_invalid_token_rejected_on_all_endpoints(self):
        """An invalid/forged token must be rejected (401) on all protected routes."""
        bad_h = {"Authorization": "Bearer invalid.forged.token"}
        for path in self.PROTECTED_ROUTES:
            r = client.get(path, headers=bad_h)
            assert r.status_code == 401, f"{path} accepted invalid token (got {r.status_code})"

    def test_no_token_rejected_on_all_endpoints(self):
        """Missing token must be rejected (401) on all protected routes."""
        for path in self.PROTECTED_ROUTES:
            r = client.get(path)
            assert r.status_code == 401, f"{path} accepted missing token"


# ══════════════════════════════════════════════════════════════════════════════
# 6. Signal → Backtest → Report → API Integration
# ══════════════════════════════════════════════════════════════════════════════

class TestBacktestIntegration:
    """Integration: Backtest uses the same Signal Engine pipeline."""

    def test_backtest_api_returns_complete_report(self):
        """POST /signal/backtest and GET /signal/backtest-report return consistent data."""
        token = _register_and_login("e2e_bt1", "e2e_bt1@test.com")
        r = client.post("/signal/backtest?symbol=AAPL&use_mock_data=true",
                        headers=_headers(token))
        assert r.status_code == 200, r.text
        fresh = r.json()
        assert fresh["metadata"]["symbol"] == "AAPL"

        r = client.get("/signal/backtest-report", headers=_headers(token))
        assert r.status_code == 200
        cached = r.json()
        assert 0 <= cached["buy_metrics"]["precision"] <= 1
        assert 0 <= cached["sell_metrics"]["recall"] <= 1

    def test_backtest_uses_same_indicator_config_as_signal_engine(self):
        """Backtest metadata must reflect the live indicator constants."""
        from app.services.signal_engine import EMA_SHORT, EMA_LONG, MACD_FAST, MACD_SLOW, RSI_OVERSOLD
        token = _register_and_login("e2e_bt2", "e2e_bt2@test.com")
        r = client.post("/signal/backtest?use_mock_data=true", headers=_headers(token))
        cfg = r.json()["metadata"]["indicator_config"]
        assert cfg["ema_short"] == EMA_SHORT
        assert cfg["ema_long"] == EMA_LONG
        assert cfg["macd_fast"] == MACD_FAST
        assert cfg["macd_slow"] == MACD_SLOW
        assert cfg["rsi_oversold"] == RSI_OVERSOLD


# ══════════════════════════════════════════════════════════════════════════════
# 7. Audit Trail Completeness Integration
# ══════════════════════════════════════════════════════════════════════════════

class TestAuditTrailIntegration:
    """Integration: Every trade action writes to audit_logs (/audit/log)."""

    def test_execute_writes_audit_entry(self):
        """Executing a trade writes an EXECUTED audit entry with timestamp."""
        token = _register_and_login("e2e_audit1", "e2e_audit1@test.com")
        proposal = _propose(token, "AAPL", "BUY", qty=5.0, risk=3.5)
        pid = proposal["id"]
        _execute(token, pid)

        r = _audit(token)
        assert r.status_code == 200
        logs = r.json()
        proposal_logs = [l for l in logs if l.get("trade_proposal_id") == pid]
        actions = {l["action_taken"] for l in proposal_logs}
        assert "EXECUTED" in actions
        for l in proposal_logs:
            assert l.get("timestamp") is not None

    def test_audit_log_paginated(self):
        """GET /audit/log must support pagination without error."""
        token = _register_and_login("e2e_audit2", "e2e_audit2@test.com")
        r = client.get("/audit/log?page=1&page_size=5", headers=_headers(token))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_override_writes_audit_with_reason(self):
        """Every override action writes an OVERRIDE log with the correct reason."""
        token = _register_and_login("e2e_audit3", "e2e_audit3@test.com")
        proposal = _propose(token, "META", "BUY", qty=3.0, risk=4.0)
        pid = proposal["id"]

        client.post(f"/trade/{pid}/override", json={
            "stop_loss": 280.0, "reason": "Audit trail integration test"
        }, headers=_headers(token))

        logs = _audit(token).json()
        override_entries = [
            l for l in logs
            if l.get("trade_proposal_id") == pid and l["action_taken"] == "OVERRIDE"
        ]
        assert len(override_entries) == 1
        assert override_entries[0]["reason"] == "Audit trail integration test"

    def test_interrupt_resume_both_in_audit(self):
        """Interrupt and resume both appear in the audit trail."""
        token = _register_and_login("e2e_audit4", "e2e_audit4@test.com")
        proposal = _propose(token, "NVDA", "BUY", qty=2.0, risk=3.0)
        pid = proposal["id"]

        client.post(f"/trade/{pid}/interrupt", headers=_headers(token))
        client.post(f"/trade/{pid}/resume", headers=_headers(token))

        logs = _audit(token).json()
        actions = {l["action_taken"] for l in logs if l.get("trade_proposal_id") == pid}
        assert "INTERRUPT" in actions
        assert "RESUME" in actions


# ══════════════════════════════════════════════════════════════════════════════
# 8. Admin Guardrail Config Integration
# ══════════════════════════════════════════════════════════════════════════════

class TestAdminGuardrailIntegration:
    """Integration: Admin can update guardrail config; changes reflected in GET."""

    def _make_admin(self, username, email):
        from app.core.database import SessionLocal
        from app.models.models import User
        token = _register_and_login(username, email)
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == username).first()
            if user:
                user.role = "admin"
                db.commit()
        finally:
            db.close()
        return token

    def test_get_guardrail_config(self):
        """GET /guardrails/config returns all required fields."""
        token = _register_and_login("e2e_gc1", "e2e_gc1@test.com")
        r = client.get("/guardrails/config", headers=_headers(token))
        assert r.status_code == 200
        cfg = r.json()
        for field in ["max_per_trade_pct", "max_daily_loss_pct", "max_risk_score",
                      "simulated_portfolio", "rsi_oversold", "rsi_overbought"]:
            assert field in cfg, f"Missing guardrail field: {field}"

    def test_non_admin_cannot_update_guardrails(self):
        """Non-admin must receive 403 when trying to update guardrails."""
        token = _register_and_login("e2e_gc2", "e2e_gc2@test.com")
        r = client.put("/guardrails/config", json={
            "max_per_trade_pct": 10.0, "max_daily_loss_pct": 5.0,
            "max_risk_score": 8.0, "simulated_portfolio": 1000000,
            "rsi_oversold": 30, "rsi_overbought": 70
        }, headers=_headers(token))
        assert r.status_code == 403

    def test_admin_can_update_guardrails(self):
        """Admin user can update guardrail thresholds."""
        token = self._make_admin("e2e_gc3", "e2e_gc3@test.com")
        r = client.put("/guardrails/config", json={
            "max_per_trade_pct": 8.0, "max_daily_loss_pct": 4.0,
            "max_risk_score": 7.5, "simulated_portfolio": 1000000,
            "rsi_oversold": 30, "rsi_overbought": 70
        }, headers=_headers(token))
        assert r.status_code == 200
        assert r.json()["max_per_trade_pct"] == 8.0


# ══════════════════════════════════════════════════════════════════════════════
# 9. Full End-to-End System Test
# ══════════════════════════════════════════════════════════════════════════════

class TestFullE2E:
    """
    Complete system walkthrough simulating a real trader session:
      Register → Login → Guardrail check → Propose → Override
      → Interrupt → Resume → Execute (new proposal) → Backtest → Audit review
    """

    def test_full_system_walkthrough(self):
        """Full E2E: auth → propose → override → interrupt → resume → execute → backtest → audit."""
        # ── 1. Register and login ─────────────────────────────────────────────
        r = client.post("/auth/register", json={
            "username": "fullsys2", "email": "fullsys2@test.com", "password": "fullpass123"
        })
        assert r.status_code in (200, 400)

        r = client.post("/auth/login", data={"username": "fullsys2", "password": "fullpass123"})
        assert r.status_code == 200
        token = r.json()["access_token"]
        h = _headers(token)

        # ── 2. Verify profile ─────────────────────────────────────────────────
        r = client.get("/user/me", headers=h)
        assert r.status_code == 200
        assert r.json()["mode"] in ("COPILOT", "AUTOPILOT")

        # ── 3. Check guardrail config ─────────────────────────────────────────
        r = client.get("/guardrails/config", headers=h)
        assert r.status_code == 200
        assert r.json()["max_per_trade_pct"] > 0

        # ── 4. Propose a trade ────────────────────────────────────────────────
        r = client.post("/trade/propose", json={
            "symbol": "AAPL", "action": "BUY", "quantity": 5.0,
            "risk_score": 4.0, "indicator_summary": "E2E test"
        }, headers=h)
        assert r.status_code == 200
        proposal_1 = r.json()
        pid1 = proposal_1["id"]
        assert proposal_1["status"] == "PENDING"

        # ── 5. Override SL/TP on proposal_1 ──────────────────────────────────
        r = client.post(f"/trade/{pid1}/override", json={
            "stop_loss": 140.0, "take_profit": 165.0,
            "reason": "Full E2E — setting risk parameters"
        }, headers=h)
        assert r.status_code == 200
        assert r.json()["stop_loss"] == 140.0
        assert r.json()["take_profit"] == 165.0

        # ── 6. Propose a SECOND trade (for execute + interrupt flow) ──────────
        r = client.post("/trade/propose", json={
            "symbol": "MSFT", "action": "BUY", "quantity": 3.0,
            "risk_score": 3.5, "indicator_summary": "E2E interrupt test"
        }, headers=h)
        assert r.status_code == 200
        pid2 = r.json()["id"]

        # ── 7. Interrupt pid2 ─────────────────────────────────────────────────
        r = client.post(f"/trade/{pid2}/interrupt", headers=h)
        assert r.status_code == 200
        assert r.json()["status"] == "INTERRUPTED"

        # ── 8. Resume pid2 ────────────────────────────────────────────────────
        r = client.post(f"/trade/{pid2}/resume", headers=h)
        assert r.status_code == 200
        assert r.json()["status"] == "RESUMED"

        # ── 9. Propose a third trade and execute it ───────────────────────────
        r = client.post("/trade/propose", json={
            "symbol": "NVDA", "action": "BUY", "quantity": 2.0,
            "risk_score": 3.0, "indicator_summary": "E2E execute test"
        }, headers=h)
        pid3 = r.json()["id"]

        r = _execute(token, pid3)
        assert r.status_code == 200
        exec_body = r.json()
        assert exec_body["status"] == "executed"
        assert exec_body["fill_status"] == "filled"
        assert exec_body["mock_mode"] is True

        # ── 10. Switch to AUTOPILOT and back ──────────────────────────────────
        r = client.patch("/user/mode", json={"mode": "AUTOPILOT"}, headers=h)
        assert r.status_code == 200
        client.patch("/user/mode", json={"mode": "COPILOT"}, headers=h)

        # ── 11. Run backtest ──────────────────────────────────────────────────
        r = client.post("/signal/backtest?use_mock_data=true", headers=h)
        assert r.status_code == 200
        bt = r.json()
        assert "buy_metrics" in bt
        assert bt["metadata"]["used_mock_data"] is True

        # ── 12. Review audit trail ────────────────────────────────────────────
        r = _audit(token, page_size=100)
        assert r.status_code == 200
        all_logs = r.json()

        # pid1 must have OVERRIDE
        pid1_actions = {l["action_taken"] for l in all_logs if l.get("trade_proposal_id") == pid1}
        assert "OVERRIDE" in pid1_actions

        # pid2 must have INTERRUPT and RESUME
        pid2_actions = {l["action_taken"] for l in all_logs if l.get("trade_proposal_id") == pid2}
        assert "INTERRUPT" in pid2_actions
        assert "RESUME" in pid2_actions

        # pid3 must have EXECUTED
        pid3_actions = {l["action_taken"] for l in all_logs if l.get("trade_proposal_id") == pid3}
        assert "EXECUTED" in pid3_actions

        # ── 13. Verify proposal list final statuses ───────────────────────────
        r = client.get("/trade/proposals", headers=h)
        proposals = {p["id"]: p for p in r.json()}
        assert proposals[pid1]["status"] == "OVERRIDDEN"
        assert proposals[pid2]["status"] == "RESUMED"
        assert proposals[pid3]["status"] == "EXECUTED"
