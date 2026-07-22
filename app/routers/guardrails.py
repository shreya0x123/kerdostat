from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.auth import get_current_user
from app.models.models import User

router = APIRouter(prefix="/guardrails", tags=["Guardrails"])

guardrail_config = {
    "max_per_trade_pct": 5.0,
    "max_daily_loss_pct": 3.0,
    "max_risk_score": 7.0,
    "simulated_portfolio": 1000000,
    "rsi_oversold": 35,
    "rsi_overbought": 65,
}

class GuardrailConfig(BaseModel):
    max_per_trade_pct: float = 5.0
    max_daily_loss_pct: float = 3.0
    max_risk_score: float = 7.0
    simulated_portfolio: float = 1000000
    rsi_oversold: int = 35
    rsi_overbought: int = 65

@router.get("/config", response_model=GuardrailConfig, summary="Get current guardrail thresholds")
def get_guardrail_config(current_user: User = Depends(get_current_user)):
    return GuardrailConfig(**guardrail_config)

@router.put("/config", response_model=GuardrailConfig, summary="Update guardrail thresholds (admin only)")
def update_guardrail_config(config: GuardrailConfig, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Admin role required to update guardrails.")
    guardrail_config.update(config.model_dump())
    return GuardrailConfig(**guardrail_config)
