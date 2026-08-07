"""
Kerdostat Demo Server
======================
Minimal Flask server exposing the Signal Engine + XDI Engine as a JSON API
so the evaluator dashboard can fetch and display results.

Routes:
    GET  /health             — liveness check
    POST /analyze            — CSV or Alpaca source (original)
    POST /analyze-yahoo      — Yahoo Finance source (no API keys needed)
    POST /trade-action       — Simulated paper trade mock response

Run:
    ./venv/bin/python scripts/demo_server.py
Then open the dashboard at http://localhost:5173 (npm run dev in dashboard/)
"""

from __future__ import annotations
import os, sys, json, logging, traceback
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from flask import Flask, request, jsonify, Response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder=None)
SAMPLE_CSV    = os.path.join(ROOT, "data", "sample_ohlcv.csv")
DASHBOARD_HTML = os.path.join(ROOT, "dashboard", "index.html")


# ─────────────────────────────────────────────────────────────────────────────
# CORS — allow any origin (evaluator demo, local file, Vite dev, etc.)
# ─────────────────────────────────────────────────────────────────────────────
@app.after_request
def add_cors(r):
    r.headers["Access-Control-Allow-Origin"]  = "*"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard — serves the self-contained React HTML (no Node/npm needed)
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    with open(DASHBOARD_HTML, "r", encoding="utf-8") as f:
        return Response(f.read(), mimetype="text/html")


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok", "ts": datetime.now(timezone.utc).isoformat()})


# ─────────────────────────────────────────────────────────────────────────────
# Original /analyze — CSV or Alpaca
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/analyze", methods=["POST", "OPTIONS"])
def analyze():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    from ml.pipeline import run_analysis

    body     = request.get_json(silent=True) or {}
    source   = body.get("source", "csv")
    symbol   = body.get("symbol", "AAPL")
    interval = body.get("interval", "1day")
    filepath = body.get("filepath", SAMPLE_CSV)
    start    = body.get("start", "2020-01-01")
    end      = body.get("end",   "2025-01-01")

    logger.info("Analyze — source=%s symbol=%s interval=%s", source, symbol, interval)

    try:
        result = run_analysis(
            source=source,
            filepath=filepath if source == "csv" else None,
            symbol=symbol    if source != "csv" else None,
            start=start, end=end, candle_interval=interval,
        )
        return jsonify({"ok": True, "result": json.loads(json.dumps(result, default=str))})
    except Exception as exc:
        logger.error("Error: %s", exc)
        return jsonify({"ok": False, "error": str(exc), "trace": traceback.format_exc()}), 500


# ─────────────────────────────────────────────────────────────────────────────
# /analyze-yahoo — Yahoo Finance, zero API keys required
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/analyze-yahoo", methods=["POST", "OPTIONS"])
def analyze_yahoo():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    body     = request.get_json(silent=True) or {}
    symbol   = body.get("symbol", "AAPL").upper().strip()
    interval = body.get("interval", "1day")

    logger.info("Analyze-Yahoo — symbol=%s interval=%s", symbol, interval)

    try:
        from engine.yahoo_loader import fetch_ohlcv
        from ml.indicators.technical_indicators import compute_all_indicators
        from ml.signals.signal_engine import SignalEngine
        from ml.xdi.xdi_engine import XDIEngine
        from ml.decision.hybrid_decision_engine import HybridDecisionEngine
        from ml.pipeline import (
            _disabled_ml_placeholder,
            _candle_horizon_label,
            _compute_combined_confidence,
        )

        # Fetch last 3 months of daily candles (enough for all indicators)
        df = fetch_ohlcv(symbol=symbol, period="3mo")

        if df is None or df.empty:
            return jsonify({"ok": False, "error": f"No data returned for symbol '{symbol}'."}), 400

        indicators      = compute_all_indicators(df)
        result          = SignalEngine().generate_signal(indicators)
        ml_pred         = _disabled_ml_placeholder()
        hybrid          = HybridDecisionEngine().combine(result, ml_pred)

        result["candle_interval"]    = interval
        result["ml_prediction"]      = ml_pred
        result["hybrid_decision"]    = hybrid
        result["generated_at"]       = datetime.now(timezone.utc).isoformat()
        result["data_as_of"]         = str(df.index[-1].date())
        result["prediction_horizon"] = _candle_horizon_label(interval)
        result["rule_confidence"]    = result["confidence"]
        result["ml_confidence"]      = None
        result["confidence"]         = _compute_combined_confidence(result["confidence"], ml_pred)
        result["explanation"]        = XDIEngine().generate_explanation(result)
        result["source"]             = "yahoo"
        result["symbol"]             = symbol

        payload = json.loads(json.dumps(result, default=str))
        return jsonify({"ok": True, "result": payload})

    except Exception as exc:
        logger.error("Yahoo analyze error: %s", exc)
        return jsonify({"ok": False, "error": str(exc), "trace": traceback.format_exc()}), 500


# ─────────────────────────────────────────────────────────────────────────────
# /trade-action — Simulated paper trade (no real brokerage connection)
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/trade-action", methods=["POST", "OPTIONS"])
def trade_action():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    body   = request.get_json(silent=True) or {}
    action = body.get("action", "YES")          # YES | NO | MODIFY
    symbol = body.get("symbol", "AAPL")
    signal = body.get("signal", "HOLD")
    qty    = body.get("qty", 10)
    sl     = body.get("sl", None)
    tp     = body.get("tp", None)
    price  = body.get("price", None)

    logger.info(
        "Trade-Action — action=%s symbol=%s signal=%s qty=%s sl=%s tp=%s",
        action, symbol, signal, qty, sl, tp,
    )

    ts = datetime.now(timezone.utc).isoformat()

    if action == "NO":
        return jsonify({
            "ok":      True,
            "action":  "NO",
            "message": "Trade dismissed. No position taken.",
            "ts":      ts,
        })

    if action in ("YES", "MODIFY"):
        order_id = f"PAPER-{symbol}-{int(datetime.now().timestamp())}"
        side     = "buy" if signal == "BUY" else "sell" if signal == "SELL" else "hold"

        confirmation = {
            "ok":       True,
            "action":   action,
            "order_id": order_id,
            "symbol":   symbol,
            "signal":   signal,
            "side":     side,
            "qty":      qty,
            "price":    price,
            "sl":       sl,
            "tp":       tp,
            "status":   "PAPER_FILLED",
            "message":  (
                f"Paper trade submitted: {side.upper()} {qty} × {symbol} "
                f"{'@ $' + str(price) if price else '@ market'}."
                + (f" SL: ${sl}" if sl else "")
                + (f" TP: ${tp}" if tp else "")
            ),
            "ts": ts,
        }
        return jsonify(confirmation)

    return jsonify({"ok": False, "error": f"Unknown action: {action}"}), 400


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 62)
    print("  KerdoStat — Evaluator Demo Server")
    print("  API  → http://localhost:5050")
    print("  UI   → http://localhost:5173  (npm run dev in dashboard/)")
    print("=" * 62 + "\n")
    app.run(host="0.0.0.0", port=5050, debug=False)
