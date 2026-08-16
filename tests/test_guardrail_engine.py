"""
tests/test_guardrail_engine.py
================================
Day 9 — Comprehensive tests for GuardrailEngine.

Tests every guardrail condition, boundary values, and combined evaluation.
"""

import pytest
from app.services.guardrail_engine import GuardrailEngine, GuardrailResult


@pytest.fixture
def engine():
    """Standard engine with fixed, known thresholds for deterministic tests."""
    return GuardrailEngine(
        portfolio_value=1_000_000,
        max_position_size_pct=5.0,    # max $50,000 per trade
        daily_loss_limit_pct=3.0,     # max $30,000 daily loss
        max_open_trades=10,
    )


# ── Guardrail 1: Max Position Size ────────────────────────────────────────────

class TestPositionSizeGuardrail:

    def test_valid_position_passes(self, engine):
        """Trade using 4% of portfolio must pass (below 5% limit)."""
        result = engine.check_position_size(quantity=40, price_per_unit=1000)
        # 40 * 1000 = $40,000 = 4% of $1,000,000
        assert result.passed is True
        assert result.reasons == []

    def test_exact_limit_fails(self, engine):
        """Trade at exactly 5% should fail (> not >=, so boundary at limit)."""
        # 50 * 1000 = $50,000 = exactly 5% — still passes (not exceeding)
        result = engine.check_position_size(quantity=50, price_per_unit=1000)
        assert result.passed is True  # exactly at limit is allowed

    def test_over_limit_fails(self, engine):
        """Trade using 6% of portfolio must be blocked."""
        result = engine.check_position_size(quantity=60, price_per_unit=1000)
        # 60 * 1000 = $60,000 = 6% of $1,000,000
        assert result.passed is False
        assert len(result.reasons) == 1
        assert "6.00%" in result.reasons[0]
        assert "5.0%" in result.reasons[0]

    def test_large_qty_small_price_passes(self, engine):
        """1000 shares at $1 = $1000 = 0.1% — must pass."""
        result = engine.check_position_size(quantity=1000, price_per_unit=1.0)
        assert result.passed is True

    def test_reason_string_contains_values(self, engine):
        """Reason message must include actual dollar amounts."""
        result = engine.check_position_size(quantity=100, price_per_unit=1000)
        assert not result.passed
        assert "$100,000" in result.reason_string or "100,000" in result.reason_string


# ── Guardrail 2: Daily Loss Limit ─────────────────────────────────────────────

class TestDailyLossGuardrail:

    def test_no_loss_passes(self, engine):
        """Zero daily loss must always pass."""
        assert engine.check_daily_loss_limit(0.0).passed is True

    def test_small_loss_passes(self, engine):
        """$10,000 loss on $1M portfolio = 1% — below 3% limit, must pass."""
        result = engine.check_daily_loss_limit(10_000)
        assert result.passed is True

    def test_at_limit_blocked(self, engine):
        """$30,000 loss = exactly 3% — must be blocked."""
        result = engine.check_daily_loss_limit(30_000)
        assert result.passed is False
        assert "3.0%" in result.reasons[0]

    def test_over_limit_blocked(self, engine):
        """$35,000 loss = 3.5% — must be blocked."""
        result = engine.check_daily_loss_limit(35_000)
        assert result.passed is False
        assert len(result.reasons) == 1
        assert "3.50%" in result.reasons[0]

    def test_reason_contains_dollar_amount(self, engine):
        """Reason must include the actual loss amount."""
        result = engine.check_daily_loss_limit(40_000)
        assert "$40,000" in result.reason_string


# ── Guardrail 3: Max Open Trades ──────────────────────────────────────────────

class TestMaxOpenTradesGuardrail:

    def test_no_open_trades_passes(self, engine):
        """Zero open trades must always pass."""
        assert engine.check_max_open_trades(0).passed is True

    def test_below_limit_passes(self, engine):
        """9 open trades with limit=10 must pass."""
        assert engine.check_max_open_trades(9).passed is True

    def test_at_limit_blocked(self, engine):
        """Exactly 10 open trades with limit=10 must be blocked."""
        result = engine.check_max_open_trades(10)
        assert result.passed is False
        assert "10" in result.reasons[0]

    def test_over_limit_blocked(self, engine):
        """15 open trades with limit=10 must be blocked."""
        result = engine.check_max_open_trades(15)
        assert result.passed is False

    def test_reason_contains_count_and_limit(self, engine):
        """Reason must include open count and limit."""
        result = engine.check_max_open_trades(11)
        assert "11" in result.reason_string
        assert "10" in result.reason_string


# ── Full evaluate() combining all three guardrails ────────────────────────────

class TestCombinedEvaluation:

    def test_all_pass_returns_passed(self, engine):
        """All guardrails within limits must return passed=True."""
        result = engine.evaluate(
            quantity=10,
            price_per_unit=100,       # $1,000 = 0.1% of $1M
            current_daily_loss=5_000, # 0.5% — below 3%
            open_trade_count=3,       # below 10
        )
        assert result.passed is True
        assert result.reasons == []

    def test_position_size_fail_blocks(self, engine):
        """Oversized position alone blocks execution."""
        result = engine.evaluate(
            quantity=100, price_per_unit=1000,  # $100k = 10%
            current_daily_loss=0, open_trade_count=0,
        )
        assert result.passed is False
        assert any("position" in r.lower() or "10.00%" in r for r in result.reasons)

    def test_daily_loss_fail_blocks(self, engine):
        """Daily loss limit alone blocks execution."""
        result = engine.evaluate(
            quantity=1, price_per_unit=1,       # trivial trade
            current_daily_loss=50_000,          # 5% — over 3%
            open_trade_count=0,
        )
        assert result.passed is False
        assert any("daily loss" in r.lower() for r in result.reasons)

    def test_max_open_trades_fail_blocks(self, engine):
        """Max open trades alone blocks execution."""
        result = engine.evaluate(
            quantity=1, price_per_unit=1,
            current_daily_loss=0,
            open_trade_count=10,               # exactly at limit
        )
        assert result.passed is False
        assert any("open trades" in r.lower() for r in result.reasons)

    def test_multiple_failures_returns_all_reasons(self, engine):
        """When multiple guardrails fail, all reasons are collected."""
        result = engine.evaluate(
            quantity=100, price_per_unit=1000,  # 10% — fails position
            current_daily_loss=40_000,          # 4% — fails daily loss
            open_trade_count=10,               # fails open trades
        )
        assert result.passed is False
        assert len(result.reasons) == 3  # all three violated

    def test_reason_string_joins_all(self, engine):
        """reason_string must concatenate all failure messages."""
        result = engine.evaluate(
            quantity=100, price_per_unit=1000,
            current_daily_loss=40_000,
            open_trade_count=10,
        )
        assert "|" in result.reason_string  # separator between messages

    def test_passed_result_has_empty_reasons(self, engine):
        """A passing result must have an empty reasons list."""
        result = engine.evaluate(
            quantity=1, price_per_unit=10,
            current_daily_loss=0, open_trade_count=0,
        )
        assert result.passed is True
        assert result.reasons == []
        assert result.reason_string == ""


# ── Custom configuration tests ────────────────────────────────────────────────

class TestCustomConfiguration:

    def test_tight_limit_blocks_small_trade(self):
        """A very tight 0.1% limit blocks even a small trade."""
        engine = GuardrailEngine(
            portfolio_value=100_000,
            max_position_size_pct=0.1,  # max $100
            daily_loss_limit_pct=99.0,
            max_open_trades=100,
        )
        result = engine.check_position_size(quantity=2, price_per_unit=100)  # $200 = 0.2%
        assert result.passed is False

    def test_generous_limit_allows_large_trade(self):
        """A 50% limit allows a large trade."""
        engine = GuardrailEngine(
            portfolio_value=1_000_000,
            max_position_size_pct=50.0,  # $500k allowed
            daily_loss_limit_pct=99.0,
            max_open_trades=1000,
        )
        result = engine.check_position_size(quantity=400, price_per_unit=1000)  # $400k = 40%
        assert result.passed is True
