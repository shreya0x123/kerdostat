# Kerdostat Full-Stack Trading Platform

This repository contains the Kerdostat Trading Platform, an automated and human-in-the-loop (HITL) algorithmic trading dashboard supporting US markets (via Alpaca) and Indian markets (via Fyers). It utilizes a rules-based XAI Justification engine and coordinates live updates across nodes using Redis Pub/Sub WebSockets, served through an Nginx proxy.

## Architecture

- **Frontend**: React and Vite interface with charts, technical indicators overlays, and interactive API Docs sandbox. Served statically via Nginx on port 80.
- **Backend**: FastAPI server running asynchronous execution queues and routing orders dynamically to Alpaca/Fyers. Exposes port 8000.
- **Redis**: Channels signal updates and order dispatches across backend nodes via Pub/Sub. Exposes port 6379.
- **Nginx**: Serves built frontend assets at `/`, proxies `/api/*` to FastAPI, and proxies `/ws` for WebSockets.

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
4. Run the FastAPI development server:
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

The full stack can be built and orchestrated using Docker Compose. Ensure Docker Desktop is running on your machine.

### 1. Build and Run Stack
Launch the services (Nginx proxy, FastAPI Backend, Redis message broker) in detached mode:
```bash
docker compose up --build -d
```

### 2. Services Access
- **Application Dashboard**: Access `http://localhost/` (Nginx gateway on port 80).
- **Backend API Docs**: Access `http://localhost:8000/docs` (Swagger UI).

### 3. Tear Down Stack
Stop and remove all running containers and networks:
```bash
docker compose down
```

---

## Technical Specifications

### XAI Justification Engine
The XAI engine compiles confluences of technical indicator thresholds (RSI, Bollinger Bands, EMA, MACD signal) and translates them to human-readable text justification:
- **BUY**: Triggered when RSI is oversold (< 30) or price crosses above EMA with positive MACD histogram.
- **SELL**: Triggered when RSI is overbought (> 70) or price crosses below EMA with negative MACD histogram.
- **HOLD**: Triggered during neutral conditions or when risk confluences (e.g. bullish trend but overbought RSI) suggest entering is unsafe.

### Redis Pub/Sub WebSocket Routing
When running in Docker Compose with a defined `REDIS_URL=redis://redis:6379`, the Connection Manager automatically subscribes to the channel `kerdostat-channel`. Signals computed or updates executed are published to the channel, and local listener tasks broadcast them to all WebSocket client sessions. If Redis is unavailable or offline, the system gracefully falls back to local broadcasting.

### Reverse Proxy Routes
- **Vite Client App**: `http://localhost/` -> serves Built Assets.
- **FastAPI Endpoint**: `http://localhost/api/*` -> `http://backend:8000/*`
- **FastAPI WebSockets**: `ws://localhost/ws` -> `ws://backend:8000/ws`
