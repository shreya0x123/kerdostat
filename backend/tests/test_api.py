import pytest
from app.main import UserModel, ProposalModel, AuditLogModel, SystemStateModel

def test_login(client, db):
    # TC-01: Login / Auth validation
    # 1. Register a new user
    register_payload = {
        "name": "Test Trader",
        "email": "test@trader.com",
        "password": "securepassword"
    }
    resp = client.post("/auth/register", json=register_payload)
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@trader.com"

    # 2. Login with valid credentials
    login_payload = {
        "email": "test@trader.com",
        "password": "securepassword"
    }
    resp = client.post("/auth/login", json=login_payload)
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@trader.com"
    assert "access_token" in client.cookies

    # 3. Login with invalid password
    bad_login = {
        "email": "test@trader.com",
        "password": "wrongpassword"
    }
    resp = client.post("/auth/login", json=bad_login)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"


def test_propose(auth_client, db):
    # TC-02: Proposal creation / retrieval
    payload = {
        "symbol": "BTCUSD",
        "signal": "BUY",
        "qty": 5,
        "SL": 60000.0,
        "TP": 70000.0,
        "XAIReason": "Strong breakout on weekly chart"
    }
    resp = auth_client.post("/trade/proposals", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "BTCUSD"
    assert data["status"] == "pending"
    
    # Verify retrieval
    resp = auth_client.get("/trade/proposals")
    assert resp.status_code == 200
    props = resp.json()
    assert len(props) > 0
    assert any(p["symbol"] == "BTCUSD" for p in props)


def test_approve(auth_client, db):
    # TC-03: HITL Proposal Approval
    # 1. Create a proposal
    payload = {
        "symbol": "AAPL",
        "signal": "BUY",
        "qty": 100,
        "SL": 175.0,
        "TP": 190.0,
        "XAIReason": "Bullish divergence"
    }
    resp = auth_client.post("/trade/proposals", json=payload)
    prop_id = resp.json()["id"]

    # 2. Approve proposal
    action_payload = {"action": "approve"}
    resp = auth_client.patch(f"/trade/{prop_id}/action", json=action_payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    # 3. Verify audit log was created
    audit_logs = db.query(AuditLogModel).filter(AuditLogModel.symbol == "AAPL").all()
    assert len(audit_logs) == 1
    assert audit_logs[0].action_type == "APPROVE"


def test_reject(auth_client, db):
    # TC-04: HITL Proposal Rejection
    # 1. Create a proposal
    payload = {
        "symbol": "MSFT",
        "signal": "SELL",
        "qty": 50,
        "SL": 420.0,
        "TP": 380.0,
        "XAIReason": "Overbought daily RSI"
    }
    resp = auth_client.post("/trade/proposals", json=payload)
    prop_id = resp.json()["id"]

    # 2. Reject proposal
    action_payload = {"action": "reject"}
    resp = auth_client.patch(f"/trade/{prop_id}/action", json=action_payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    # 3. Verify audit log was created
    audit_logs = db.query(AuditLogModel).filter(AuditLogModel.symbol == "MSFT").all()
    assert len(audit_logs) == 1
    assert audit_logs[0].action_type == "REJECT"


def test_override(auth_client, db):
    # TC-05: Manual override validation (pauses autopilot and sets status to PAUSED)
    # 1. Create proposal
    payload = {
        "symbol": "TSLA",
        "signal": "BUY",
        "qty": 100,
        "SL": 160.0,
        "TP": 190.0,
        "XAIReason": "Earnings run-up"
    }
    resp = auth_client.post("/trade/proposals", json=payload)
    prop_id = resp.json()["id"]

    # 2. Set mode to autopilot
    auth_client.post("/trade/mode", json={"mode": "autopilot"})

    # 3. Trigger manual override (hijack)
    override_payload = {
        "symbol": "TSLA",
        "qty": 120,
        "SL": 165.0,
        "TP": 185.0,
        "entry_price": 170.0,
        "proposal_id": prop_id
    }
    resp = auth_client.post(f"/trade/{prop_id}/override", json=override_payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # 4. Verify system mode has fallen back to copilot
    mode_resp = auth_client.get("/trade/mode")
    assert mode_resp.json()["mode"] == "copilot"

    # 5. Verify proposal status is now paused
    prop = db.query(ProposalModel).filter(ProposalModel.id == prop_id).first()
    assert prop.status == "paused"
    assert prop.qty == 120
    assert prop.SL == 165.0
    assert prop.TP == 185.0

    # 6. Verify audit log created for override
    logs = db.query(AuditLogModel).filter(AuditLogModel.symbol == "TSLA").all()
    assert any(log.action_type == "HIJACK_EXECUTE" for log in logs)


def test_autopilot_toggle(auth_client, db):
    # TC-06: System mode toggle
    # Start: copilot
    resp = auth_client.get("/trade/mode")
    assert resp.json()["mode"] == "copilot"

    # Toggle to autopilot
    resp = auth_client.post("/trade/mode", json={"mode": "autopilot"})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "autopilot"

    # Check mode status
    resp = auth_client.get("/trade/mode")
    assert resp.json()["mode"] == "autopilot"

    # Toggle back to copilot
    resp = auth_client.post("/trade/mode", json={"mode": "copilot"})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "copilot"


def test_override_fyers(auth_client, db):
    # Create proposal for an Indian symbol
    payload = {
        "symbol": "RELIANCE.NS",
        "signal": "BUY",
        "qty": 50,
        "SL": 2400.0,
        "TP": 2600.0,
        "XAIReason": "Strong dynamic support"
    }
    resp = auth_client.post("/trade/proposals", json=payload)
    prop_id = resp.json()["id"]

    # Trigger manual override (hijack)
    override_payload = {
        "symbol": "RELIANCE.NS",
        "qty": 60,
        "SL": 2410.0,
        "TP": 2590.0,
        "entry_price": 2450.0,
        "proposal_id": prop_id
    }
    resp = auth_client.post(f"/trade/{prop_id}/override", json=override_payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # Verify proposal status is now approved (since mode is copilot by default)
    prop = db.query(ProposalModel).filter(ProposalModel.id == prop_id).first()
    assert prop.status == "approved"
    assert prop.qty == 60

    # Verify audit log created
    logs = db.query(AuditLogModel).filter(AuditLogModel.symbol == "RELIANCE.NS").all()
    assert any(log.action_type == "HIJACK_EXECUTE" for log in logs)


def test_approve_fyers(auth_client, db):
    # 1. Create proposal for Indian symbol mapped in select_executor_by_symbol
    payload = {
        "symbol": "TCS",
        "signal": "BUY",
        "qty": 20,
        "SL": 3000.0,
        "TP": 3500.0,
        "XAIReason": "Indian sector momentum"
    }
    resp = auth_client.post("/trade/proposals", json=payload)
    prop_id = resp.json()["id"]

    # 2. Approve proposal
    action_payload = {"action": "approve"}
    resp = auth_client.patch(f"/trade/{prop_id}/action", json=action_payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    # 3. Verify audit log was created
    audit_logs = db.query(AuditLogModel).filter(AuditLogModel.symbol == "TCS").all()
    assert len(audit_logs) == 1
    assert audit_logs[0].action_type == "APPROVE"
