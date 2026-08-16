"""
tests/test_backtest.py
=======================
Day 13 — Tests for backtest service and /signal/backtest-report endpoint.
Uses mock data (no network calls needed).
"""

import os
import pytest
from app.services.backtest import run_backtest, load_backtest_report, BACKTEST_JSON


class TestBacktestService:

    def test_run_backtest_returns_dict(self):
        """run_backtest must return a dict with required top-level keys."""
        result = run_backtest(symbol="AAPL", eval_window=20, use_mock_data=True)
        assert isinstance(result, dict)
        assert "metadata" in result
        assert "buy_metrics" in result
        assert "sell_metrics" in result
        assert "summary" in result
        assert "daily_records" in result

    def test_buy_metrics_fields_present(self):
        """BUY metrics must contain precision, recall, f1_score."""
        result = run_backtest(symbol="AAPL", eval_window=20, use_mock_data=True)
        bm = result["buy_metrics"]
        for key in ["precision", "recall", "f1_score", "true_positives", "false_positives"]:
            assert key in bm, f"Missing key: {key}"

    def test_sell_metrics_fields_present(self):
        """SELL metrics must contain precision, recall, f1_score."""
        result = run_backtest(symbol="AAPL", eval_window=20, use_mock_data=True)
        sm = result["sell_metrics"]
        for key in ["precision", "recall", "f1_score", "true_positives", "false_positives"]:
            assert key in sm

    def test_precision_and_recall_in_valid_range(self):
        """Precision and recall must be between 0 and 1."""
        result = run_backtest(symbol="AAPL", eval_window=20, use_mock_data=True)
        for metric_name in ["buy_metrics", "sell_metrics"]:
            m = result[metric_name]
            assert 0.0 <= m["precision"] <= 1.0, f"{metric_name} precision out of range"
            assert 0.0 <= m["recall"] <= 1.0, f"{metric_name} recall out of range"

    def test_daily_records_not_empty(self):
        """daily_records must contain at least one entry."""
        result = run_backtest(symbol="AAPL", eval_window=20, use_mock_data=True)
        assert len(result["daily_records"]) > 0

    def test_daily_record_fields(self):
        """Each daily_record must have required fields."""
        result = run_backtest(symbol="AAPL", eval_window=10, use_mock_data=True)
        for record in result["daily_records"]:
            for field in ["date", "predicted", "actual", "fwd_return_pct"]:
                assert field in record, f"Missing field '{field}' in daily record"

    def test_predicted_values_are_valid(self):
        """Predicted values must only be BUY, SELL, or HOLD."""
        result = run_backtest(symbol="AAPL", eval_window=10, use_mock_data=True)
        valid = {"BUY", "SELL", "HOLD"}
        for record in result["daily_records"]:
            assert record["predicted"] in valid, f"Invalid predicted: {record['predicted']}"

    def test_metadata_contains_symbol_and_methodology(self):
        """Metadata must contain symbol, methodology, and indicator config."""
        result = run_backtest(symbol="AAPL", eval_window=10, use_mock_data=True)
        meta = result["metadata"]
        assert meta["symbol"] == "AAPL"
        assert "methodology" in meta
        assert "indicator_config" in meta

    def test_report_saved_to_json(self):
        """Backtest must save results to the JSON file."""
        run_backtest(symbol="AAPL", eval_window=10, use_mock_data=True)
        assert os.path.exists(BACKTEST_JSON)

    def test_load_backtest_report_returns_saved(self):
        """load_backtest_report must return the saved report after a run."""
        run_backtest(symbol="AAPL", eval_window=10, use_mock_data=True)
        report = load_backtest_report()
        assert report is not None
        assert "buy_metrics" in report

    def test_tp_fp_fn_are_non_negative(self):
        """All confusion matrix values must be non-negative integers."""
        result = run_backtest(symbol="AAPL", eval_window=10, use_mock_data=True)
        for metric in ["buy_metrics", "sell_metrics"]:
            m = result[metric]
            assert m["true_positives"] >= 0
            assert m["false_positives"] >= 0
            assert m["false_negatives"] >= 0

    def test_summary_counts_add_up(self):
        """buy + sell + hold signals should sum to total days evaluated."""
        result = run_backtest(symbol="AAPL", eval_window=10, use_mock_data=True)
        s = result["summary"]
        total = s["buy_signals_generated"] + s["sell_signals_generated"] + s["hold_signals_generated"]
        assert total == s["total_days_evaluated"]

    def test_mock_flag_reflected_in_metadata(self):
        """use_mock_data flag must be reflected in metadata.used_mock_data."""
        result = run_backtest(symbol="AAPL", eval_window=10, use_mock_data=True)
        assert result["metadata"]["used_mock_data"] is True


# ── API integration test ──────────────────────────────────────────────────────

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _get_token(username="btuser13", email="bt13@ex.com"):
    client.post("/auth/register", json={"username": username, "email": email, "password": "btpass123"})
    r = client.post("/auth/login", data={"username": username, "password": "btpass123"})
    return r.json().get("access_token", "")


class TestBacktestEndpoint:

    def test_get_backtest_report_returns_200(self):
        """GET /signal/backtest-report must return 200 with a valid report."""
        token = _get_token("btget1", "btget1@ex.com")
        r = client.get("/signal/backtest-report",
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "buy_metrics" in body
        assert "sell_metrics" in body

    def test_get_backtest_report_no_auth_returns_401(self):
        """GET /signal/backtest-report without token must return 401."""
        r = client.get("/signal/backtest-report")
        assert r.status_code == 401

    def test_post_run_backtest_returns_200(self):
        """POST /signal/backtest must run a fresh backtest and return 200."""
        token = _get_token("btpost1", "btpost1@ex.com")
        r = client.post("/signal/backtest?symbol=AAPL&use_mock_data=true",
                        headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "metadata" in body
        assert body["metadata"]["symbol"] == "AAPL"
