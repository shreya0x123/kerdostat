# Kerdostat Algorithmic Trading Platform - Frontend

This is the institutional-grade frontend interface for the **Kerdostat Live Trading** platform. It provides real-time portfolio tracking, explainable AI (XAI) trade suggestions, dynamic risk management overlays, manual override options (execution hijack), and comprehensive audit trail analytics.

---

## Technical Stack
- **Framework**: React (v19) + Vite (v8)
- **Styling**: Tailwind CSS + Custom CSS Variables
- **Icons**: Lucide React
- **Data Visualization**: Lightweight Charts (TradingView) & Recharts
- **Form State**: React Hook Form
- **Testing**: Vitest + JSDOM + Vitest UI + V8 Coverage

---

## Getting Started

### Prerequisites
Make sure you have [Node.js](https://nodejs.org/) installed (LTS version recommended, v18+).

### 1. Installation
Navigate to the `frontend` directory and install the required dependencies:
```bash
cd frontend
npm install
```

### 2. Development Server
Start the frontend dev server locally:
```bash
npm run dev
```
By default, Vite will start the app at `http://localhost:5173`.

> [!NOTE]
> Make sure the FastAPI backend is running simultaneously at `http://localhost:8000` to feed live data via REST endpoints and WebSockets.

### 3. Production Build
To build the application for deployment:
```bash
npm run build
```
This generates a static production bundle under the `/dist` directory.

---

## Running the Test Suite

We use **Vitest** for component, integration, and E2E simulation tests.

### Run All Tests
To run all tests once:
```bash
npm test
```
This executes the 13 test suites (40 test cases) in single-run mode.

### Active Test Suites (TC-07 to TC-12)
- **TC-07**: WebSocket reconnect backoff loops ([WebSocketReconnect.test.jsx](src/components/__tests__/WebSocketReconnect.test.jsx))
- **TC-08**: Drawdown guardrails breach warning banners ([TradingTerminal.test.jsx](src/components/__tests__/TradingTerminal.test.jsx))
- **TC-09**: Autopilot vs. Copilot badge and toggle synchronization ([AutopilotToggle.test.jsx](src/components/__tests__/AutopilotToggle.test.jsx))
- **TC-10**: Hijack form validation constraints and SL safety checks ([HijackPanel.test.jsx](src/components/__tests__/HijackPanel.test.jsx))
- **TC-11**: Audit log multi-sig selections and CSV exports ([AuditLog.test.jsx](src/components/__tests__/AuditLog.test.jsx))
- **TC-12**: Price chart interval ranges queries ([PriceChart.test.jsx](src/components/__tests__/PriceChart.test.jsx))

### Generate Coverage Report
To execute tests and output the component test coverage summary:
```bash
npx vitest run --coverage
```
Our target component coverage is **>80%** (currently at ~82.6% for lines and ~81.6% for statements under the `src/components` directory).

### Generate HTML Coverage Report
To compile the interactive visual HTML coverage report:
```bash
npx vitest run --coverage --reporter=html --reporter=default
```
The output will be saved in `frontend/coverage/index.html`. You can open this file in any web browser to drill down into coverage metrics by file and component line.
