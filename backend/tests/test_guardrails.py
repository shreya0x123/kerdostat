import pytest
from app.main import ProposalModel, AuditLogModel
from datetime import datetime, timezone

def test_guardrail_max_position_size(client, db):
    # Setup a proposal with qty > 1000 (which exceeds default max_position_size of 1000)
    payload = {
        "symbol": "AAPL",
        "signal": "BUY",
        "qty": 1001,
        "SL": 170.0,
        "TP": 190.0,
        "XAIReason": "Test maximum position size"
    }
    resp = client.post("/trade/proposals", json=payload)
    prop_id = resp.json()["id"]

    # Try to approve the proposal, should fail with HTTP 400
    action_payload = {"action": "approve"}
    resp = client.patch(f"/trade/{prop_id}/action", json=action_payload)
    assert resp.status_code == 400
    assert "Guardrail breach" in resp.json()["detail"]
    assert "exceeds maximum position size limit" in resp.json()["detail"]

    # Verify override check for quantity
    override_payload = {
        "symbol": "AAPL",
        "qty": 1200,
        "SL": 170.0,
        "TP": 190.0,
        "entry_price": 175.0,
        "proposal_id": prop_id
    }
    resp = client.post(f"/trade/{prop_id}/override", json=override_payload)
    assert resp.status_code == 400
    assert "Guardrail breach" in resp.json()["detail"]
    assert "exceeds maximum position size limit" in resp.json()["detail"]


def test_guardrail_max_open_trades(client, db):
    # Seed 5 approved proposals in the database (since default max_open_trades is 5)
    for i in range(5):
        prop = ProposalModel(
            id=f"approved-prop-{i}",
            symbol=f"SYM{i}",
            signal="BUY",
            qty=10,
            SL=100.0,
            TP=110.0,
            status="approved"
        )
        db.add(prop)
    db.commit()

    # Create a 6th pending proposal
    payload = {
        "symbol": "AAPL",
        "signal": "BUY",
        "qty": 100,
        "SL": 170.0,
        "TP": 190.0,
        "XAIReason": "6th open trade"
    }
    resp = client.post("/trade/proposals", json=payload)
    prop_id = resp.json()["id"]

    # Try to approve it, should fail due to max open trades limit
    action_payload = {"action": "approve"}
    resp = client.patch(f"/trade/{prop_id}/action", json=action_payload)
    assert resp.status_code == 400
    assert "Guardrail breach" in resp.json()["detail"]
    assert "Number of concurrent open trades" in resp.json()["detail"]


def test_guardrail_daily_loss_limit_single(client, db):
    # Single trade risk exceeds 5000.0 limit
    # We increase qty to 500 so that even if price is around 180 and SL is 130:
    # risk = abs(180 - 130) * 500 = 25000.0 (capped at 180 * 500 = 90000.0, which is still 25000.0 > 5000.0)
    payload = {
        "symbol": "AAPL",
        "signal": "BUY",
        "qty": 500,
        "SL": 130.0,
        "TP": 220.0,
        "XAIReason": "High risk trade"
    }
    resp = client.post("/trade/proposals", json=payload)
    prop_id = resp.json()["id"]

    # Try to approve it
    action_payload = {"action": "approve"}
    resp = client.patch(f"/trade/{prop_id}/action", json=action_payload)
    assert resp.status_code == 400
    assert "Guardrail breach" in resp.json()["detail"]
    assert "Trade risk of" in resp.json()["detail"]
    assert "over the daily limit" in resp.json()["detail"]


def test_guardrail_daily_loss_limit_cumulative(client, db):
    # Create and approve a proposal with risk = abs(200 - 170) * 100 = 3000.0 (below limit)
    # To avoid guardrail checks blocking the initial approved trade during mock DB seed,
    # we can directly insert it into the DB/audit logs as approved.
    
    # 1. Add approved proposal to DB
    prop1 = ProposalModel(
        id="prop-risk-1",
        symbol="SYM1",
        signal="BUY",
        qty=100,
        SL=170.0,
        TP=230.0,
        status="approved"
    )
    db.add(prop1)
    
    # 2. Add a matching successful audit log for today
    today_str = datetime.now(timezone.utc).isoformat()
    log1 = AuditLogModel(
        id="log-risk-1",
        timestamp=today_str,
        symbol="SYM1",
        action_type="APPROVE",
        qty=100,
        price=200.0, # entry price
        status="SUCCESS",
        user="trader@kerdostat.com"
    )
    db.add(log1)
    db.commit()

    # Now, attempt to approve another trade with risk = abs(200 - 170) * 100 = 3000.0
    # Cumulative risk would be 3000 + 3000 = 6000 (exceeds 5000.0 daily limit)
    payload = {
        "symbol": "SYM2",
        "signal": "BUY",
        "qty": 100,
        "SL": 170.0,
        "TP": 230.0,
        "XAIReason": "Second risk trade"
    }
    resp = client.post("/trade/proposals", json=payload)
    prop_id = resp.json()["id"]

    # Force checking price to be 200 by custom override or fallback
    # In action endpoint, candles will close around 200, so risk is ~3000.
    # Let's verify via override endpoint to be precise about price:
    override_payload = {
        "symbol": "SYM2",
        "qty": 100,
        "SL": 170.0,
        "TP": 230.0,
        "entry_price": 200.0,
        "proposal_id": prop_id
    }
    resp = client.post(f"/trade/{prop_id}/override", json=override_payload)
    assert resp.status_code == 400
    assert "Guardrail breach" in resp.json()["detail"]
    assert "Trade risk of" in resp.json()["detail"]
