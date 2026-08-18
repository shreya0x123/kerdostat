# KERDOSTAT — API USER GUIDE

**Version:** 1.0.0  
**Base URL:** `http://localhost:8000`  
**Authentication:** Bearer JWT Token (`Authorization: Bearer <token>`)

---

## Table of Contents
1. [Authentication (`/auth`)](#1-authentication-auth)
2. [User Management (`/user`)](#2-user-management-user)
3. [Signal Engine (`/signal`)](#3-signal-engine-signal)
4. [Trade Lifecycle (`/trade`)](#4-trade-lifecycle-trade)
5. [Guardrails (`/guardrails`)](#5-guardrails-guardrails)
6. [Audit Trail (`/audit`)](#6-audit-trail-audit)
7. [Market Data (`/market`)](#7-market-data-market)
8. [System & Health (`/health`, `/version`)](#8-system--health-health-version)

---

## 1. Authentication (`/auth`)

### `POST /auth/register`
Registers a new trader account.

**Request Body:**
```json
{
  "username": "trader1",
  "email": "trader1@kerdostat.com",
  "password": "SecurePassword123"
}
```

**Response (`200 OK`):**
```json
{
  "id": 1,
  "username": "trader1",
  "email": "trader1@kerdostat.com",
  "role": "trader",
  "mode": "COPILOT",
  "created_at": "2026-07-22T10:45:00Z"
}
```

### `POST /auth/login`
Authenticates a user and returns a JWT access token.

**Request (Form Data):**
- `username`: `trader1`
- `password`: `SecurePassword123`

**Response (`200 OK`):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## 2. User Management (`/user`)

### `GET /user/me`
Fetches current authenticated user profile.

**Headers:** `Authorization: Bearer <token>`

**Response (`200 OK`):**
```json
{
  "id": 1,
  "username": "trader1",
  "email": "trader1@kerdostat.com",
  "role": "trader",
  "mode": "COPILOT",
  "created_at": "2026-07-22T10:45:00Z"
}
```

### `PATCH /user/mode`
Toggles user trading operational mode between `COPILOT` (HITL) and `AUTOPILOT` (HOTL).

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "mode": "AUTOPILOT"
}
```

**Response (`200 OK`):**
```json
{
  "id": 1,
  "username": "trader1",
  "email": "trader1@kerdostat.com",
  "role": "trader",
  "mode": "AUTOPILOT",
  "created_at": "2026-07-22T10:45:00Z"
}
```

---

## 3. Signal Engine (`/signal`)

### `POST /signal/generate`
Scans technical indicators (RSI, MACD, EMA, ATR) for a symbol and generates XAI justification. If user mode is `AUTOPILOT`, automatically evaluates guardrails and executes trades.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "symbol": "AAPL",
  "period": "6mo"
}
```

**Response (`200 OK`):**
```json
{
  "symbol": "AAPL",
  "signal_found": true,
  "direction": "BUY",
  "date": "2026-07-21",
  "price_inr": 12525.00,
  "rsi": 32.40,
  "macd_line": 0.4520,
  "macd_signal": 0.2100,
  "risk_score": 3.5,
  "ema_20_inr": 12400.00,
  "ema_50_inr": 12100.00,
  "atr_14_inr": 210.50,
  "xdi_justification": "A BUY signal has been identified for AAPL on 2026-07-21 at $150.00. RSI-14 is 32.40, placing it in oversold territory...",
  "proposal_id": 14
}
```

---

## 4. Trade Lifecycle (`/trade`)

### Trade Status Flow
```text
PENDING → APPROVED → EXECUTED  
        → REJECTED  
        → OVERRIDDEN  
        → INTERRUPTED → RESUMED → EXECUTED  
```

### `POST /trade/propose`
Manually submits a trade proposal.

**Request Body:**
```json
{
  "symbol": "NVDA",
  "action": "BUY",
  "quantity": 10.0,
  "risk_score": 4.0,
  "indicator_summary": "RSI=31.5 oversold, MACD crossover"
}
```

### `GET /trade/proposals`
Returns paginated trade proposals. Optional status filter (`?status=PENDING`).

### `POST /trade/{id}/override`
Modifies quantity, stop loss, or take profit with guardrail validation.

**Request Body:**
```json
{
  "quantity": 15.0,
  "stop_loss": 140.0,
  "take_profit": 180.0,
  "reason": "Trader manual risk adjustment"
}
```

### `POST /trade/{id}/interrupt`
Pauses active or pending trade execution flows in Autopilot mode.

**Response (`200 OK`):**
```json
{
  "id": 14,
  "symbol": "AAPL",
  "action": "BUY",
  "quantity": 5.0,
  "risk_score": 3.5,
  "status": "INTERRUPTED",
  "created_at": "2026-07-22T10:50:00Z"
}
```

### `POST /trade/{id}/resume`
Resumes an interrupted trade proposal, re-validating guardrails before execution.

**Response (`200 OK`):**
```json
{
  "id": 14,
  "symbol": "AAPL",
  "action": "BUY",
  "quantity": 5.0,
  "risk_score": 3.5,
  "status": "RESUMED",
  "created_at": "2026-07-22T10:50:00Z"
}
```

### `POST /trade/execute/{id}`
Submits order to broker after guardrail checks.

**Response (`200 OK`):**
```json
{
  "proposal_id": 14,
  "status": "EXECUTED",
  "alpaca_order_id": "sim-order-14",
  "symbol": "AAPL",
  "action": "BUY",
  "quantity": 5.0,
  "executed_by": "trader1"
}
```

---

## 5. Guardrails (`/guardrails`)

### `GET /guardrails/config`
Returns active portfolio guardrail thresholds.

**Response (`200 OK`):**
```json
{
  "max_position_size_pct": 5.0,
  "daily_loss_limit_pct": 10.0,
  "max_open_trades": 5,
  "max_risk_score": 7.0
}
```

---

## 6. Audit Trail (`/audit`)

### `GET /audit/log`
Retrieves paginated audit log entries with filters by date, symbol, and action type.

---

## 7. Market Data (`/market`)

### `GET /market/ohlcv/{symbol}`
Returns cached OHLCV market data (TTL 60s).

---

## 8. System & Health (`/health`, `/version`)

### `GET /health`
Returns system status.

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```
