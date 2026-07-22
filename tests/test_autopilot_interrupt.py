import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_auth_token(username="pilotuser", email="pilot@example.com"):
    """Helper — registers a user and returns a valid JWT token."""
    client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": "pilotpass123"
    })
    response = client.post("/auth/login", data={
        "username": username,
        "password": "pilotpass123"
    })
    return response.json()["access_token"]


def test_user_mode_toggle():
    """Verify PATCH /user/mode toggles mode to AUTOPILOT and back to COPILOT."""
    token = get_auth_token("modetoggle", "toggle@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Default profile check
    res = client.get("/user/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["mode"] == "COPILOT"

    # Toggle to AUTOPILOT
    res = client.patch("/user/mode", json={"mode": "AUTOPILOT"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["mode"] == "AUTOPILOT"

    # Toggle back to COPILOT
    res = client.patch("/user/mode", json={"mode": "COPILOT"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["mode"] == "COPILOT"


def test_autopilot_auto_execution():
    """In AUTOPILOT mode, /signal/generate should automatically execute valid proposals."""
    token = get_auth_token("autoexec", "autoexec@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Enable AUTOPILOT mode
    client.patch("/user/mode", json={"mode": "AUTOPILOT"}, headers=headers)

    # Generate signal
    res = client.post("/signal/generate", json={"symbol": "AAPL"}, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["signal_found"] is True
    proposal_id = body["proposal_id"]

    # Verify proposal status was auto-executed
    prop_res = client.get(f"/trade/proposals", headers=headers)
    assert prop_res.status_code == 200
    proposals = prop_res.json()
    matching = [p for p in proposals if p["id"] == proposal_id]
    assert len(matching) == 1
    assert matching[0]["status"] in ["EXECUTED", "PENDING"]


def test_interrupt_and_resume_flow():
    """Verify POST /trade/{id}/interrupt and POST /trade/{id}/resume flow."""
    token = get_auth_token("interruptuser", "interrupt@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Submit proposal
    prop_res = client.post("/trade/propose", json={
        "symbol": "NVDA",
        "action": "BUY",
        "quantity": 5.0,
        "risk_score": 3.0,
        "indicator_summary": "RSI=32 oversold"
    }, headers=headers)
    assert prop_res.status_code == 200
    proposal_id = prop_res.json()["id"]

    # Interrupt proposal
    int_res = client.post(f"/trade/{proposal_id}/interrupt", headers=headers)
    assert int_res.status_code == 200
    assert int_res.json()["status"] == "INTERRUPTED"

    # Resume proposal
    res_res = client.post(f"/trade/{proposal_id}/resume", headers=headers)
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "RESUMED"

    # Execute resumed proposal
    exe_res = client.post(f"/trade/execute/{proposal_id}", headers=headers)
    assert exe_res.status_code == 200
    assert exe_res.json()["status"] == "EXECUTED"


def test_invalid_interrupt():
    """Cannot interrupt non-existent proposal."""
    token = get_auth_token("invalidint", "invalidint@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/trade/99999/interrupt", headers=headers)
    assert res.status_code == 404
