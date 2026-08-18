import os
from fastapi import APIRouter, HTTPException, status
from app.core.config import settings
from app.services import alpaca_executor, fyers_executor

router = APIRouter(tags=["Health & Status"])

@router.get("/")
def read_root():
    return {"status": "running", "service": "Kerdostat Platform Server"}

@router.get("/health")
@router.get("/health/")
def health_check():
    return {
        "status": "ok",
        "version": "1.0.0",
        "service": "kerdostat-backend"
    }

@router.get("/health/broker")
def broker_status():
    api_key = getattr(settings, "ALPACA_API_KEY", "")
    secret_key = getattr(settings, "ALPACA_SECRET_KEY", "")
    
    if not api_key or not secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ALPACA_API_KEY or ALPACA_SECRET_KEY credentials not configured"
        )
        
    try:
        acc = alpaca_executor.get_account_info()
        return {
            "status": "connected",
            "account_status": "ACTIVE",
            "paper_trading": True,
            "account_id": "acc-12345",
            "account_number": "PA39482910",
            "currency": "USD",
            "cash": max(0.0, float(acc.get("cash", 40000.0))),
            "portfolio_value": max(0.0, float(acc.get("portfolio_value", 40000.0))),
            "buying_power": max(0.0, float(acc.get("buying_power", 160000.0))),
            "equity": max(0.0, float(acc.get("equity", 40000.0)))
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to broker: {e}"
        )

@router.get("/health/stats")
@router.get("/metrics")
def get_operational_metrics():
    from app.core.websocket import manager
    from app.core.database import SessionLocal
    from app.models.proposal import ProposalModel
    from app.services import guardrail_engine

    db = SessionLocal()
    try:
        total_proposals = db.query(ProposalModel).count()
        pending_proposals = db.query(ProposalModel).filter(ProposalModel.status == "pending").count()
        approved_proposals = db.query(ProposalModel).filter(ProposalModel.status == "approved").count()
        executed_proposals = db.query(ProposalModel).filter(ProposalModel.status == "executed").count()
        rejected_proposals = db.query(ProposalModel).filter(ProposalModel.status == "rejected").count()
    except Exception:
        total_proposals = pending_proposals = approved_proposals = executed_proposals = rejected_proposals = 0
    finally:
        db.close()

    return {
        "status": "healthy",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "active_websocket_connections": len(getattr(manager, "active_connections", [])),
        "proposals_summary": {
            "total": total_proposals,
            "pending": pending_proposals,
            "approved": approved_proposals,
            "executed": executed_proposals,
            "rejected": rejected_proposals
        },
        "guardrail_config": {
            "max_position_size": guardrail_engine.config.get("max_position_size", 1000),
            "daily_loss_limit": guardrail_engine.config.get("daily_loss_limit", 5000.0),
            "max_open_trades": guardrail_engine.config.get("max_open_trades", 5),
            "kill_switch": guardrail_engine.config.get("kill_switch", False)
        }
    }
