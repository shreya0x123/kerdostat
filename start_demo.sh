#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  KerdoStat — Evaluator Demo Launcher  (no Node/npm required)
#
#  Usage (from the KerdoStat root folder):
#      bash start_demo.sh
#
#  Opens:  http://localhost:5050
# ═══════════════════════════════════════════════════════════════════
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/venv/bin/python"
PIP="$ROOT/venv/bin/pip"

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'
YELLOW='\033[1;33m'; BOLD='\033[1m'; RESET='\033[0m'

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${CYAN}║        KERDOSTAT  —  Evaluator Demo              ║${RESET}"
echo -e "${BOLD}${CYAN}║   Signal Engine (M1) + XDI Engine (M2)           ║${RESET}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════╝${RESET}"
echo ""

# ── 1. Verify Python venv ────────────────────────────────────────────
if [ ! -f "$VENV" ]; then
  echo -e "${RED}✗ venv not found at $VENV${RESET}"
  echo "  Create it with:  python3 -m venv venv && venv/bin/pip install -r requirements.txt"
  exit 1
fi
echo -e "${GREEN}✔ Python venv found${RESET}"

# ── 2. Ensure required Python packages ───────────────────────────────
echo -e "${CYAN}→ Checking Python dependencies…${RESET}"
"$VENV" -c "import yfinance, rich, flask" 2>/dev/null || {
  echo -e "${YELLOW}  Installing missing packages (yfinance rich flask)…${RESET}"
  "$PIP" install yfinance rich flask --quiet
}
echo -e "${GREEN}✔ Python dependencies ready${RESET}"

# ── 3. Kill anything already on port 5050 ────────────────────────────
lsof -ti:5050 | xargs kill -9 2>/dev/null || true
sleep 0.5

# ── 4. Start Flask (serves dashboard + API) ──────────────────────────
echo -e "${CYAN}→ Starting server on http://localhost:5050 …${RESET}"
"$VENV" "$ROOT/scripts/demo_server.py" &
FLASK_PID=$!
sleep 2

# ── 5. Health check ──────────────────────────────────────────────────
if curl -s http://localhost:5050/health > /dev/null 2>&1; then
  echo -e "${GREEN}✔ Server is up (PID $FLASK_PID)${RESET}"
else
  echo -e "${YELLOW}  Server starting… open http://localhost:5050 in a few seconds${RESET}"
fi

echo ""
echo -e "${BOLD}${GREEN}══════════════════════════════════════════════════${RESET}"
echo -e "${BOLD}${GREEN}  ✔ Demo Ready — open your browser:${RESET}"
echo -e "${BOLD}${GREEN}       http://localhost:5050${RESET}"
echo -e "${BOLD}${GREEN}══════════════════════════════════════════════════${RESET}"
echo ""
echo -e "${CYAN}  5-Step Demo:${RESET}"
echo -e "  1 · Pick TSLA (or any symbol) from the chip bar"
echo -e "  2 · Click ⚡ Run Analysis — Module 1 fetches + calculates"
echo -e "  3 · Point to XDI Explanation panel — Module 2 justification"
echo -e "  4 · Show Horizon badge (e.g. next 5–10 trading days)"
echo -e "  5 · Click Yes / No / Modify — Human-in-the-Loop handoff"
echo ""
echo -e "${YELLOW}  Press Ctrl+C to stop the server.${RESET}"
echo ""

# ── 6. Open browser ──────────────────────────────────────────────────
open http://localhost:5050 2>/dev/null || true

# ── 7. Wait for Ctrl+C ───────────────────────────────────────────────
trap "echo ''; echo -e '${YELLOW}Shutting down…${RESET}'; kill $FLASK_PID 2>/dev/null; exit 0" INT TERM
wait
