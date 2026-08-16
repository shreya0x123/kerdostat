from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, Literal


# User schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserModeUpdate(BaseModel):
    mode: Literal["COPILOT", "AUTOPILOT"]

class UserResponse(UserBase):
    id: int
    role: Optional[str] = "trader"
    mode: Optional[str] = "COPILOT"
    created_at: datetime

    class Config:
        from_attributes = True

# TradeProposal schemas
class TradeProposalBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    action: str = Field(..., description="BUY or SELL")
    quantity: float = Field(..., gt=0, description="Quantity must be greater than 0")
    risk_score: float = Field(..., ge=0, le=10, description="Risk score between 0 and 10")
    indicator_summary: Optional[str] = None

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        v_upper = v.upper().strip()
        if v_upper not in ["BUY", "SELL"]:
            raise ValueError("Action must be either BUY or SELL")
        return v_upper

class TradeProposalCreate(TradeProposalBase):
    pass

class TradeProposalResponse(TradeProposalBase):
    id: int
    status: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


# AuditLog schemas
class AuditLogBase(BaseModel):
    trade_proposal_id: int
    action_taken: str
    decision_by: str
    reason: Optional[str] = None

class AuditLogCreate(AuditLogBase):
    pass

class AuditLogResponse(AuditLogBase):
    id: int
    mode: Optional[str] = None
    override_delta: Optional[float] = None
    guardrail_hit: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True

class TradeOverrideRequest(BaseModel):
    quantity: Optional[float] = Field(None, gt=0)
    stop_loss: Optional[float] = Field(None, gt=0)
    take_profit: Optional[float] = Field(None, gt=0)
    reason: str = Field(..., min_length=1, max_length=255)

class TradeOverrideResponse(BaseModel):
    proposal_id: int
    status: str
    original_quantity: float
    new_quantity: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason: str
    overridden_by: str
    timestamp: datetime
    xdi_after_override: Optional[str] = None   # Day 10: recalculated XDI explanation

    class Config:
        from_attributes = True


# ── Execute schemas (Day 8) ───────────────────────────────────────────────────
class TradeExecuteRequest(BaseModel):
    proposal_id: int = Field(..., description="ID of an existing PENDING trade proposal")

class TradeExecuteResponse(BaseModel):
    proposal_id: int
    order_id: str
    symbol: str
    action: str
    quantity: float
    status: str          # "executed" | "failed" | "guardrail_blocked"
    fill_status: str     # "filled" | "partially_filled" | "pending" | "error"
    filled_qty: float
    avg_fill_price: Optional[float]
    mock_mode: bool
    message: str