# KERDOSTAT — 3-MINUTE EVALUATOR DEMO SCRIPT

**Presenter:** Dharshini G (Backend Lead)  
**System:** Kerdostat Hybrid Copilot-to-Autopilot Trading Framework  

---

## ⏱️ Demo Flow (3 Minutes Max)

### Step 1: Authentication & Default Mode Verification (30 Seconds)
1. Open Postman or Swagger UI (`http://localhost:8000/docs`).
2. Call `POST /auth/login` with test credentials:
   - **Username**: `postmanuser2`
   - **Password**: `test123`
3. Show the JWT Access Token response.
4. Call `GET /user/me` using the bearer token.
5. Point out to evaluators:  
   > *"The user starts in **Copilot mode (HITL)** by default, requiring explicit human authorization for all trade executions."*

---

### Step 2: Signal Generation & Explainable AI (XAI) (45 Seconds)
1. Call `POST /signal/generate` with symbol `AAPL`.
2. **Highlight RSI and MACD signals from response** *(note: values vary based on market data)*.
3. Highlight the **XDI Justification string**:  
   > *"Notice how Kerdostat generates natural language explanations (XAI) detailing why a BUY signal was identified rather than acting as a black box."*
4. Show that Proposal `#1` was saved with status `PENDING`.

---

### Step 3: Autopilot Mode Activation & Guardrail Check (45 Seconds)
1. Call `PATCH /user/mode` with body `{"mode": "AUTOPILOT"}`.
2. Show profile updated to `mode: "AUTOPILOT"`.
3. Call `POST /signal/generate` with symbol `NVDA`.
4. Point out the automated response and explicit Autopilot proof:  
   > *"In **Autopilot mode (HOTL)**, the system immediately invokes the Autopilot service. Note that execution only happens after rigorous guardrail validation (risk checks for portfolio concentration and risk score thresholds pass)."*
5. **Show status directly changing from PENDING → EXECUTED without manual approval.**

---

### Step 4: Intervention Hijack (Interrupt → Resume → Override) (45 Seconds)
1. Submit a trade proposal via `POST /trade/propose` for `TSLA`.
2. Call `POST /trade/{id}/interrupt`. Point out status changed to `INTERRUPTED`:  
   > *"If market volatility surges, the trader can hit **Interrupt** to pause active or pending trade execution flows mid-flight."*
3. Call `POST /trade/{id}/resume`. Show status updated to `RESUMED`:  
   > *"The user intervenes, reviews parameters, and resumes execution."*
4. *(Optional)* Call `POST /trade/{id}/override` to adjust Stop-Loss and Take-Profit values if parameter adjustments are requested before execution.
5. Call `POST /trade/execute/{id}` to submit order after review.

---

### Step 5: Audit Trail Inspection (15 Seconds)
1. Call `GET /audit/log`.
2. Show timestamped log entries for `LOGIN`, `SIGNAL_GEN`, `AUTO_EXECUTED`, `INTERRUPT`, `RESUME`, `OVERRIDE`, and `EXECUTED`.
3. Conclude:  
   > *"Every single system action, override, and guardrail breach is fully audited for compliance and risk tracking."*
4. Final Closing Statement:  
   > *"This demonstrates how Kerdostat combines automation with human control, ensuring both efficiency and risk-aware decision making."*