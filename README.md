# Kerdostat — Hybrid Copilot-to-Autopilot Trading Framework

**Owner:** Dharshini G (Backend + Auth + FastAPI)  
**Repository:** [https://github.com/shreya0x123/kerdostat](https://github.com/shreya0x123/kerdostat)  
**Branch:** `signal-engine`  
**Version:** v1.0.0

---

## Overview

Kerdostat is a **Hybrid Copilot-to-Autopilot Algorithmic Trading Framework** that implements:
* **Copilot (HITL — Human-in-the-Loop)**: User approves, overrides, or rejects trade proposals manually.
* **Autopilot (HOTL — Human-on-the-Loop)**: System auto-evaluates guardrails and auto-executes trade signals.
* **Signal Engine**: Calculates technical indicators (RSI, MACD, EMA, ATR) and generates Explainable AI (XAI) justifications.
* **Interrupt & Resume Control**: Enables traders to pause active automated execution flows during high volatility or manual intervention.
* **Audit Trail**: Full historical logging of every action, override, guardrail breach, and execution.

---

## Trade Status Flow

```text
PENDING → APPROVED → EXECUTED  
        → REJECTED  
        → OVERRIDDEN  
        → INTERRUPTED → RESUMED → EXECUTED  
```

---

## Project Structure

```text
kerdostat/
├── alembic/                      # Database migrations
│   └── versions/                 # Revision scripts (including e5f6g7h8i9j0_add_mode_to_users.py)
├── app/
│   ├── main.py                   # FastAPI app initialization, middleware, rate limiting
│   ├── core/
│   │   ├── auth.py               # JWT authentication & password hashing
│   │   ├── config.py             # Settings configuration
│   │   └── database.py           # PostgreSQL SQLAlchemy engine & session factory
│   ├── models/
│   │   └── models.py             # SQLAlchemy models (User, TradeProposal, AuditLog)
│   ├── schemas/
│   │   └── schemas.py            # Pydantic OWASP-compliant request/response validation schemas
│   ├── services/
│   │   ├── signal_engine.py      # Technical indicator calculation, SSL resilience, mock OHLCV fallback
│   │   ├── autopilot.py          # Autopilot HOTL evaluation service & guardrail engine
│   │   └── broker.py             # Alpaca paper trading SDK wrapper
│   └── routers/
│       ├── auth.py               # /auth/register, /auth/login
│       ├── user.py               # /user/me, /user/mode (PATCH)
│       ├── signal.py             # /signal/generate
│       ├── trade.py              # /trade/propose, /proposals, /interrupt, /resume, /execute
│       ├── override.py           # /trade/{id}/override
│       ├── guardrails.py         # /guardrails/config
│       ├── audit.py              # /audit/log
│       ├── market.py             # /market/ohlcv/{symbol}
│       └── websocket.py          # /ws/ohlcv/{symbol}
├── postman/
│   └── kerdostat.postman_collection.json # Exported Postman collection
├── tests/
│   ├── test_auth.py
│   ├── test_trade.py
│   ├── test_smoke.py
│   └── test_autopilot_interrupt.py # Unit & integration test suite
├── API_USER_GUIDE.md             # API documentation with request/response samples
├── CHANGELOG.md                  # Release history
├── requirements.txt
└── pytest.ini
```

---

## Local Setup Instructions

```bash
# 1. Activate environment
cd D:\Kerdostat
venv\Scripts\activate
cd kerdostat

# 2. Start Redis via WSL (optional for WS caching)
wsl
redis-server --daemonize yes
exit

# 3. Apply Alembic migrations
alembic upgrade head

# 4. Start backend server
uvicorn app.main:app --reload
```

---

## Interactive API Documentation

Once the server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## Running Test Suite

Run full automated Pytest test suite:

```bash
pytest tests/ -v
```

All test suites cover:
- Authentication & JWT token generation
- User mode toggle (`COPILOT` vs `AUTOPILOT`)
- Signal generation & SSL resilience fallback
- Proposal creation, override, interrupt, and resume
- Guardrail breach blocking
- Audit log persistence
