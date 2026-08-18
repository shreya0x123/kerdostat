# Kerdostat — Full-Stack Hybrid Copilot-to-Autopilot Trading Platform

This repository contains the **Kerdostat Trading Platform**, an automated and human-in-the-loop (HITL) algorithmic trading system supporting US markets (via Alpaca) and Indian markets (via Fyers). It utilizes a rules-based XAI Justification engine, coordinates live updates across nodes using Redis Pub/Sub WebSockets, and is served through an Nginx proxy.

---

## Features & Highlights

* **Copilot Mode (HITL — Human-in-the-Loop)**: Allows traders to review, approve, override, or reject trade proposals manually.
* **Autopilot Mode (HOTL — Human-on-the-Loop)**: System auto-evaluates guardrails and executes trade signals automatically when conditions match.
* **XAI Justification Engine**: Compiles indicator confluences (RSI, Bollinger Bands, EMA, MACD) and outputs human-readable trade reasoning.
* **Interrupt & Resume Control**: Enables traders to pause active automated execution flows during high volatility or manual intervention.
* **Full Monorepo Architecture**: Integrated React + Vite frontend, FastAPI backend, Alembic database migrations, Redis message broker, and Nginx reverse proxy.

---

## Architecture

- **Frontend**: React and Vite interface with interactive charts, indicator overlays, guided tour, and API sandbox. Served statically via Nginx on port 80.
- **Backend**: FastAPI server running asynchronous execution queues and routing orders dynamically to Alpaca/Fyers. Exposes port 8000.
- **Redis**: Channels signal updates and order dispatches across backend nodes via Pub/Sub. Exposes port 6379.
- **Nginx**: Serves built frontend assets at `/`, proxies `/api/*` to FastAPI, and proxies `/ws` for WebSockets.

---

## Project Structure

```text
kerdostat/
├── backend/
│   ├── alembic/                  # Database migrations
│   ├── app/                      # FastAPI core, routers, models, schemas & services
│   ├── engine/                   # Yahoo loader & ML engine scripts
│   ├── scripts/                  # Verification & utility scripts
│   ├── tests/                    # Backend test suite (pytest)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/                      # React frontend source (components, hooks, pages, store)
│   ├── Dockerfile
│   └── package.json
├── docker/
│   └── nginx/                    # Nginx reverse proxy configuration
├── docs/                         # System guides, API docs, presentation & setup guides
├── postman/                      # Postman collections
├── docker-compose.yml
└── README.md
```

---

## Local Development (Direct Run)

### 1. Backend Setup
1. Navigate to `backend`:
   ```bash
   cd backend
   ```
2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run database migrations:
   ```bash
   alembic upgrade head
   ```
5. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### 2. Frontend Setup
1. Navigate to `frontend`:
   ```bash
   cd ../frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run Vite development server:
   ```bash
   npm run dev
   ```

---

## Local Production Execution (Docker Compose)

Launch the entire stack (Nginx proxy, FastAPI Backend, Redis message broker):
```bash
docker compose up --build -d
```

### Services Access
- **Application Dashboard**: `http://localhost/`
- **Backend API Docs**: `http://localhost:8000/docs` (Swagger UI)

---

## Running Test Suites

- **Backend Tests**:
  ```bash
  cd backend
  pytest
  ```

- **Frontend Tests**:
  ```bash
  cd frontend
  npm run test
  ```
