from typing import Optional
from pydantic import BaseModel

class ProposalCreateRequest(BaseModel):
    symbol: str
    signal: str
    qty: int
    SL: float
    TP: float
    XAIReason: Optional[str] = None
    risk_score: Optional[float] = 3.0

class ActionRequest(BaseModel):
    action: str

class ModeRequest(BaseModel):
    mode: str

class HijackRequest(BaseModel):
    symbol: str
    qty: int
    SL: float
    TP: float
    entry_price: float
    proposal_id: Optional[str] = None
    side: Optional[str] = "buy"
    order_type: Optional[str] = "limit"

# Alias for semantic clarity in clean architecture
OverrideRequest = HijackRequest
