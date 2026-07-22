from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import TradeProposal, User
from app.services.signal_engine import run_signal_pipeline

router = APIRouter(prefix="/signal", tags=["Signal"])

class SignalRequest(BaseModel):
    symbol: str
    period: Optional[str] = "6mo"

class SignalResponse(BaseModel):
    symbol: str
    signal_found: bool
    direction: Optional[str] = None
    date: Optional[str] = None
    price_inr: Optional[float] = None
    rsi: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    risk_score: Optional[float] = None
    ema_20_inr: Optional[float] = None
    ema_50_inr: Optional[float] = None
    atr_14_inr: Optional[float] = None
    xdi_justification: Optional[str] = None
    proposal_id: Optional[int] = None

@router.post("/generate", response_model=SignalResponse, summary="Generate trade signal with XDI justification")
def generate_signal(
    request: SignalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        result = run_signal_pipeline(request.symbol)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signal engine error: {str(e)}")

    if result["signal"] is None:
        return SignalResponse(symbol=request.symbol, signal_found=False)

    signal = result["signal"]
    xdi = result["xdi"]

    proposal = TradeProposal(
        symbol=signal["symbol"],
        action=signal["direction"],
        quantity=float(max(1, int(1000000 * 0.05 / signal["price_inr"]))),
        risk_score=signal["risk_score"],
        indicator_summary=f"RSI={signal['rsi']}, MACD={signal['macd_line']:.4f}",
        status="PENDING"
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)

    # ── Autopilot Trigger (HOTL) ──────────────────────────────────────────────
    if getattr(current_user, "mode", "COPILOT") == "AUTOPILOT":
        from app.services.autopilot import evaluate_and_execute_autopilot
        evaluate_and_execute_autopilot(proposal, current_user, db)

    return SignalResponse(
        symbol=signal["symbol"],
        signal_found=True,
        direction=signal["direction"],
        date=signal["date"],
        price_inr=signal["price_inr"],
        rsi=signal["rsi"],
        macd_line=signal["macd_line"],
        macd_signal=signal["macd_signal"],
        risk_score=signal["risk_score"],
        ema_20_inr=signal["ema_20_inr"],
        ema_50_inr=signal["ema_50_inr"],
        atr_14_inr=signal["atr_14_inr"],
        xdi_justification=xdi,
        proposal_id=proposal.id
    )
