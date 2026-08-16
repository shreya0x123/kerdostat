"""
app/services/guardrail_engine.py
==================================
GuardrailEngine — Day 9

Centralised, reusable guardrail evaluation engine.
Both Copilot (manual execute) and Autopilot paths delegate to this class.

Guardrails enforced
-------------------
1. max_position_size_pct  — trade value must not exceed N% of portfolio.
2. daily_loss_limit_pct   — total realised loss today must not exceed N%.
3. max_open_trades        — number of PENDING/EXECUTED proposals must not exceed N.

Configuration
-------------
Loaded from environment variables at construction time with safe defaults.
Can also be passed explicitly for testing or admin override.

Usage
-----
    from app.services.guardrail_engine import GuardrailEngine

    engine = GuardrailEngine()
    result = engine.evaluate(proposal, db)
    if not result.passed:
        # block execution
        print(result.reasons)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class GuardrailResult:
    passed: bool
    reasons: List[str] = field(default_factory=list)

    @property
    def reason_string(self) -> str:
        return " | ".join(self.reasons) if self.reasons else ""


# ── GuardrailEngine ───────────────────────────────────────────────────────────

class GuardrailEngine:
    """
    Evaluates all guardrails for a proposed trade before execution.

    If ANY guardrail fails:
      - passed = False
      - reasons list contains a clear human-readable explanation
      - Alpaca is NOT called
    """

    def __init__(
        self,
        portfolio_value: Optional[float] = None,
        max_position_size_pct: Optional[float] = None,
        daily_loss_limit_pct: Optional[float] = None,
        max_open_trades: Optional[int] = None,
    ) -> None:
        """
        Args:
            portfolio_value        : Total portfolio value in dollars. Defaults to env PORTFOLIO_VALUE (1_000_000).
            max_position_size_pct  : Max % of portfolio per trade. Defaults to env MAX_POSITION_SIZE_PCT (5.0).
            daily_loss_limit_pct   : Max daily loss % before all trades blocked. Defaults to env DAILY_LOSS_LIMIT_PCT (3.0).
            max_open_trades        : Max concurrent PENDING+EXECUTED proposals. Defaults to env MAX_OPEN_TRADES (10).
        """
        self.portfolio_value = portfolio_value or float(
            os.getenv("PORTFOLIO_VALUE", "1000000")
        )
        self.max_position_size_pct = max_position_size_pct or float(
            os.getenv("MAX_POSITION_SIZE_PCT", "5.0")
        )
        self.daily_loss_limit_pct = daily_loss_limit_pct or float(
            os.getenv("DAILY_LOSS_LIMIT_PCT", "3.0")
        )
        self.max_open_trades = max_open_trades or int(
            os.getenv("MAX_OPEN_TRADES", "10")
        )

    # ── Individual guardrail checks ───────────────────────────────────────────

    def check_position_size(
        self,
        quantity: float,
        price_per_unit: float,
    ) -> GuardrailResult:
        """
        Guardrail 1: Maximum position size.
        Trade value must not exceed max_position_size_pct% of portfolio.
        """
        trade_value = quantity * price_per_unit
        trade_pct   = (trade_value / self.portfolio_value) * 100

        if trade_pct > self.max_position_size_pct:
            reason = (
                f"Position size {trade_pct:.2f}% exceeds the maximum allowed "
                f"{self.max_position_size_pct:.1f}% per trade "
                f"(trade_value=${trade_value:,.0f}, portfolio=${self.portfolio_value:,.0f})."
            )
            logger.warning("Guardrail [position_size] FAILED: %s", reason)
            return GuardrailResult(passed=False, reasons=[reason])

        logger.debug("Guardrail [position_size] passed: %.2f%%", trade_pct)
        return GuardrailResult(passed=True)

    def check_daily_loss_limit(self, current_daily_loss: float) -> GuardrailResult:
        """
        Guardrail 2: Daily loss limit.
        If today's total realised loss exceeds daily_loss_limit_pct% of portfolio,
        block all further executions.

        Args:
            current_daily_loss: Total dollar loss today (positive = loss).
        """
        loss_pct = (current_daily_loss / self.portfolio_value) * 100

        if loss_pct >= self.daily_loss_limit_pct:
            reason = (
                f"Daily loss limit reached: ${current_daily_loss:,.0f} "
                f"({loss_pct:.2f}%) exceeds the {self.daily_loss_limit_pct:.1f}% "
                f"daily limit. No further executions allowed today."
            )
            logger.warning("Guardrail [daily_loss] FAILED: %s", reason)
            return GuardrailResult(passed=False, reasons=[reason])

        logger.debug("Guardrail [daily_loss] passed: %.2f%% of limit used", loss_pct)
        return GuardrailResult(passed=True)

    def check_max_open_trades(self, open_trade_count: int) -> GuardrailResult:
        """
        Guardrail 3: Maximum number of open trades.
        If open PENDING+EXECUTED proposals >= max_open_trades, block new execution.

        Args:
            open_trade_count: Current count of PENDING + EXECUTED proposals.
        """
        if open_trade_count >= self.max_open_trades:
            reason = (
                f"Maximum open trades reached: {open_trade_count} open trades "
                f"(limit={self.max_open_trades}). Close or reject existing proposals first."
            )
            logger.warning("Guardrail [max_open_trades] FAILED: %s", reason)
            return GuardrailResult(passed=False, reasons=[reason])

        logger.debug("Guardrail [max_open_trades] passed: %d open", open_trade_count)
        return GuardrailResult(passed=True)

    # ── Full evaluation ───────────────────────────────────────────────────────

    def evaluate(
        self,
        quantity: float,
        price_per_unit: float,
        current_daily_loss: float,
        open_trade_count: int,
    ) -> GuardrailResult:
        """
        Run all three guardrails against the proposed trade.

        Returns a single GuardrailResult:
          - passed=True if ALL guardrails pass.
          - passed=False with combined reasons if ANY guardrail fails.

        The caller must NOT call Alpaca if passed=False.
        """
        violations: List[str] = []

        r1 = self.check_position_size(quantity, price_per_unit)
        if not r1.passed:
            violations.extend(r1.reasons)

        r2 = self.check_daily_loss_limit(current_daily_loss)
        if not r2.passed:
            violations.extend(r2.reasons)

        r3 = self.check_max_open_trades(open_trade_count)
        if not r3.passed:
            violations.extend(r3.reasons)

        if violations:
            logger.warning(
                "GuardrailEngine: %d violation(s) — execution blocked.", len(violations)
            )
            return GuardrailResult(passed=False, reasons=violations)

        logger.info("GuardrailEngine: all guardrails passed — execution permitted.")
        return GuardrailResult(passed=True)

    # ── DB-aware convenience method ───────────────────────────────────────────

    def evaluate_from_db(
        self,
        quantity: float,
        price_per_unit: float,
        db,
        current_daily_loss: float = 0.0,
    ) -> GuardrailResult:
        """
        Convenience wrapper that counts open trades from the database.

        Args:
            quantity         : Proposed trade quantity.
            price_per_unit   : Estimated price per unit (use risk_score*100 as proxy when price unknown).
            db               : SQLAlchemy Session.
            current_daily_loss: Today's realised loss in dollars (defaults to 0 if not tracked).
        """
        from app.models.models import TradeProposal
        open_count = db.query(TradeProposal).filter(
            TradeProposal.status.in_(["PENDING", "EXECUTED"])
        ).count()

        return self.evaluate(quantity, price_per_unit, current_daily_loss, open_count)


# ── Module-level singleton ────────────────────────────────────────────────────
guardrail_engine = GuardrailEngine()
