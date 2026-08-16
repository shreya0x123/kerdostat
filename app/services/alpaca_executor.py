"""
app/services/alpaca_executor.py
================================
AlpacaExecutor — single-responsibility wrapper for paper-trading order
submission, status polling, and fill retrieval.

Modes
-----
REAL   : calls Alpaca paper-trading REST API (requires credentials).
MOCK   : returns deterministic fake responses — no network, no credentials.
         Enabled by setting ALPACA_MOCK_MODE=true in environment.

Design
------
* Only paper-trading.  Live-trading URLs are never used.
* Credentials come exclusively from environment variables.
* AlpacaExecutor is independent of FastAPI — importable by any service.
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ── Mock order store (in-memory for local dev) ────────────────────────────────
_MOCK_ORDERS: dict[str, dict] = {}


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: str          # "buy" | "sell"
    qty: float
    status: str        # "accepted" | "filled" | "rejected" | "error"
    mock: bool = False
    submitted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    error_message: Optional[str] = None


@dataclass
class FillStatus:
    order_id: str
    status: str        # "filled" | "partially_filled" | "pending" | "rejected"
    filled_qty: float
    avg_fill_price: Optional[float]
    mock: bool = False


# ── AlpacaExecutor ────────────────────────────────────────────────────────────

class AlpacaExecutor:
    """
    Paper-trading order executor.

    Instantiate once per request (or share as a singleton).
    All broker calls are paper-trading only.
    """

    PAPER_BASE_URL = "https://paper-api.alpaca.markets"

    def __init__(self) -> None:
        self._mock_mode: bool = os.getenv("ALPACA_MOCK_MODE", "false").lower() == "true"
        self._client = None  # lazy-initialised on first real call
        logger.info(
            "AlpacaExecutor initialised — mode=%s",
            "MOCK" if self._mock_mode else "REAL",
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_client(self):
        """Lazily initialise the Alpaca REST client (real mode only)."""
        if self._client is not None:
            return self._client

        api_key    = os.getenv("ALPACA_API_KEY", "")
        secret_key = os.getenv("ALPACA_SECRET_KEY", "")
        base_url   = os.getenv("ALPACA_BASE_URL", self.PAPER_BASE_URL)

        if not api_key or not secret_key:
            raise EnvironmentError(
                "Alpaca credentials missing. "
                "Set ALPACA_API_KEY and ALPACA_SECRET_KEY, "
                "or enable ALPACA_MOCK_MODE=true for local development."
            )

        import alpaca_trade_api as tradeapi  # lazy — not imported in mock mode
        self._client = tradeapi.REST(
            key_id=api_key,
            secret_key=secret_key,
            base_url=base_url,
            api_version="v2",
        )
        logger.info("Alpaca REST client connected (base_url=%s)", base_url)
        return self._client

    def _mock_submit(self, symbol: str, qty: float, side: str) -> OrderResult:
        """Create a fake order and store it in the mock store."""
        order_id = str(uuid.uuid4())
        mock_order = {
            "order_id": order_id,
            "symbol": symbol.upper(),
            "qty": qty,
            "side": side,
            "status": "filled",      # mock always fills immediately
            "filled_qty": qty,
            "avg_fill_price": 150.00,  # deterministic placeholder
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
        _MOCK_ORDERS[order_id] = mock_order
        logger.info("[MOCK] Order created — id=%s %s %s qty=%s", order_id, side.upper(), symbol, qty)
        return OrderResult(
            order_id=order_id,
            symbol=symbol.upper(),
            side=side,
            qty=qty,
            status="accepted",
            mock=True,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def is_mock(self) -> bool:
        return self._mock_mode

    def submit_buy(self, symbol: str, qty: float) -> OrderResult:
        """
        Submit a paper BUY market order.

        Args:
            symbol: Ticker symbol (e.g. "AAPL").
            qty:    Number of shares (fractional shares supported).

        Returns:
            OrderResult dataclass with order_id and initial status.
        """
        return self._submit(symbol, qty, "buy")

    def submit_sell(self, symbol: str, qty: float) -> OrderResult:
        """
        Submit a paper SELL market order.

        Args:
            symbol: Ticker symbol (e.g. "AAPL").
            qty:    Number of shares.

        Returns:
            OrderResult dataclass with order_id and initial status.
        """
        return self._submit(symbol, qty, "sell")

    def _submit(self, symbol: str, qty: float, side: str) -> OrderResult:
        """Internal dispatcher for BUY / SELL."""
        if qty <= 0:
            raise ValueError(f"qty must be positive, got {qty}")

        if self._mock_mode:
            return self._mock_submit(symbol, qty, side)

        try:
            client = self._get_client()
            order = client.submit_order(
                symbol=symbol.upper(),
                qty=qty,
                side=side,
                type="market",
                time_in_force="day",
            )
            logger.info(
                "Order submitted — id=%s %s %s qty=%s status=%s",
                order.id, side.upper(), symbol, qty, order.status,
            )
            return OrderResult(
                order_id=order.id,
                symbol=symbol.upper(),
                side=side,
                qty=qty,
                status=order.status,
                mock=False,
            )
        except Exception as exc:
            logger.error("Order submission failed: %s", exc)
            return OrderResult(
                order_id="",
                symbol=symbol.upper(),
                side=side,
                qty=qty,
                status="error",
                mock=False,
                error_message=str(exc),
            )

    def poll_order_status(self, order_id: str) -> str:
        """
        Poll the current status of an order.

        Returns:
            Status string: "filled" | "partially_filled" | "new" |
                           "accepted" | "rejected" | "canceled" | "unknown"
        """
        if self._mock_mode:
            order = _MOCK_ORDERS.get(order_id)
            if order is None:
                return "unknown"
            status = order["status"]
            logger.info("[MOCK] poll_order_status id=%s → %s", order_id, status)
            return status

        try:
            client = self._get_client()
            order = client.get_order(order_id)
            logger.info("poll_order_status id=%s → %s", order_id, order.status)
            return order.status
        except Exception as exc:
            logger.error("poll_order_status failed for id=%s: %s", order_id, exc)
            return "unknown"

    def get_fill_status(self, order_id: str) -> FillStatus:
        """
        Retrieve fill information for an order.

        Returns:
            FillStatus with filled_qty and avg_fill_price.
        """
        if self._mock_mode:
            order = _MOCK_ORDERS.get(order_id)
            if order is None:
                return FillStatus(
                    order_id=order_id,
                    status="unknown",
                    filled_qty=0.0,
                    avg_fill_price=None,
                    mock=True,
                )
            logger.info("[MOCK] get_fill_status id=%s", order_id)
            return FillStatus(
                order_id=order_id,
                status=order["status"],
                filled_qty=order["filled_qty"],
                avg_fill_price=order["avg_fill_price"],
                mock=True,
            )

        try:
            client = self._get_client()
            order = client.get_order(order_id)
            filled_qty = float(order.filled_qty or 0)
            avg_price  = float(order.filled_avg_price) if order.filled_avg_price else None
            logger.info(
                "get_fill_status id=%s filled=%s avg_price=%s",
                order_id, filled_qty, avg_price,
            )
            return FillStatus(
                order_id=order_id,
                status=order.status,
                filled_qty=filled_qty,
                avg_fill_price=avg_price,
                mock=False,
            )
        except Exception as exc:
            logger.error("get_fill_status failed for id=%s: %s", order_id, exc)
            return FillStatus(
                order_id=order_id,
                status="error",
                filled_qty=0.0,
                avg_fill_price=None,
                mock=False,
            )


# ── Module-level singleton (shared by FastAPI routers) ────────────────────────
alpaca_executor = AlpacaExecutor()
