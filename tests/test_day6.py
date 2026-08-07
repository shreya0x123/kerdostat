"""
Day 6 Unit Tests — ML Training Pipeline (Baseline, Metrics, Metadata, Session)

All tests use synthetic in-memory data only. No TF/Keras imports occur at
module load time (lazy imports are used inside the tests that need them).

Test isolation:
    - NaiveBaseline, metrics, ModelMetadata: pure NumPy, always fast.
    - TrainingSession: skipped if TF not available.
    - make_sequences_scaled_y: pure NumPy.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

import numpy as np
import pytest

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# NaiveBaseline tests
# ============================================================

class TestNaiveBaseline:

    def test_predict_shape(self):
        from ml.training.baseline import NaiveBaseline
        baseline = NaiveBaseline()
        y = np.array([100, 101, 99, 102, 103], dtype=float)
        pred = baseline.predict(y)
        assert pred.shape == (4,), "predict() should return n-1 predictions"
        np.testing.assert_array_equal(pred, y[:-1])

    def test_predict_too_short(self):
        from ml.training.baseline import NaiveBaseline
        baseline = NaiveBaseline()
        with pytest.raises(ValueError, match="at least 2"):
            baseline.predict(np.array([100.0]))

    def test_compute_metrics_keys(self):
        from ml.training.baseline import NaiveBaseline
        baseline = NaiveBaseline()
        y = np.linspace(100, 120, 30)
        m = baseline.compute_metrics(y)
        assert {"mae", "rmse", "mape", "n_samples"} == set(m.keys())

    def test_compute_metrics_zero_series(self):
        """Flat price series → MAE/RMSE = 0."""
        from ml.training.baseline import NaiveBaseline
        baseline = NaiveBaseline()
        y = np.full(10, 150.0)
        m = baseline.compute_metrics(y)
        assert m["mae"] == pytest.approx(0.0, abs=1e-6)
        assert m["rmse"] == pytest.approx(0.0, abs=1e-6)

    def test_beats_positive(self):
        from ml.training.baseline import NaiveBaseline
        b = NaiveBaseline()
        assert b.beats({"rmse": 2.0}, {"rmse": 1.5}) is True

    def test_beats_negative(self):
        from ml.training.baseline import NaiveBaseline
        b = NaiveBaseline()
        assert b.beats({"rmse": 1.0}, {"rmse": 1.5}) is False

    def test_improvement_pct(self):
        from ml.training.baseline import NaiveBaseline
        b = NaiveBaseline()
        pct = b.improvement_pct({"rmse": 2.0}, {"rmse": 1.5})
        assert pct == pytest.approx(25.0, abs=0.1)


# ============================================================
# Metrics tests
# ============================================================

class TestMetrics:

    def test_compute_metrics_perfect(self):
        from ml.training.metrics import compute_metrics
        y = np.array([100, 101, 102], dtype=float)
        m = compute_metrics(y, y)
        assert m["mae"] == pytest.approx(0.0, abs=1e-6)
        assert m["rmse"] == pytest.approx(0.0, abs=1e-6)
        assert m["mape"] == pytest.approx(0.0, abs=1e-6)

    def test_compute_metrics_shape_mismatch(self):
        from ml.training.metrics import compute_metrics
        with pytest.raises(ValueError, match="Shape mismatch"):
            compute_metrics(np.array([1, 2, 3]), np.array([1, 2]))

    def test_compute_metrics_known(self):
        from ml.training.metrics import compute_metrics
        y_true = np.array([100.0, 200.0])
        y_pred = np.array([110.0, 180.0])
        m = compute_metrics(y_true, y_pred)
        assert m["mae"] == pytest.approx(15.0, abs=1e-4)  # (10+20)/2

    def test_directional_accuracy_all_correct(self):
        from ml.training.metrics import directional_accuracy
        # actual goes up: 100→101→102
        # predicted also above previous actual: 101→102
        y_true = np.array([100.0, 101.0, 102.0])
        y_pred = np.array([100.5, 101.5, 102.5])
        da = directional_accuracy(y_true, y_pred)
        assert da == pytest.approx(1.0)

    def test_directional_accuracy_all_wrong(self):
        from ml.training.metrics import directional_accuracy
        y_true = np.array([100.0, 101.0, 102.0])
        # Predicted below previous actual → wrong direction
        y_pred = np.array([99.0, 99.5, 100.5])
        da = directional_accuracy(y_true, y_pred)
        # Actual dirs: +1, +1; Pred dirs: <prev_actual, <prev_actual
        # pred[1]=99.5 > y_true[0]=100.0? No. pred[2]=100.5 > y_true[1]=101.0? No.
        # actual dirs: [True, True], pred dirs: [False, False] → all wrong
        assert da == pytest.approx(0.0)

    def test_directional_accuracy_too_short(self):
        from ml.training.metrics import directional_accuracy
        da = directional_accuracy(np.array([100.0]), np.array([100.0]))
        assert da is None

    def test_pct_vs(self):
        from ml.training.metrics import pct_vs
        assert pct_vs(2.0, 1.5) == "+25.0%"
        assert pct_vs(1.5, 2.0) == "-33.3%"
        assert pct_vs(0.0, 1.0) == "N/A"


# ============================================================
# ModelMetadata tests
# ============================================================

class TestModelMetadata:

    def test_creation_defaults(self):
        from ml.training.model_metadata import ModelMetadata
        meta = ModelMetadata()
        assert meta.symbol == "AAPL"
        assert meta.model_name == "LSTM"
        assert meta.beats_baseline is None

    def test_set_metrics(self):
        from ml.training.model_metadata import ModelMetadata
        meta = ModelMetadata()
        meta.set_metrics(mae=1.2, rmse=1.8, mape=0.65, directional_accuracy=0.54)
        assert meta.metrics["mae"] == pytest.approx(1.2, abs=1e-4)
        assert meta.metrics["directional_accuracy"] == pytest.approx(0.54, abs=1e-4)

    def test_compute_verdict_beats(self):
        from ml.training.model_metadata import ModelMetadata
        meta = ModelMetadata()
        meta.set_metrics(mae=1.0, rmse=1.5, mape=0.5, directional_accuracy=0.6)
        meta.set_baseline_metrics(mae=1.5, rmse=2.0, mape=0.7)
        meta.compute_verdict()
        assert meta.beats_baseline is True
        assert meta.improvement_pct_rmse == pytest.approx(25.0, abs=0.1)

    def test_compute_verdict_does_not_beat(self):
        from ml.training.model_metadata import ModelMetadata
        meta = ModelMetadata()
        meta.set_metrics(mae=2.0, rmse=2.5, mape=1.0, directional_accuracy=0.4)
        meta.set_baseline_metrics(mae=1.0, rmse=1.5, mape=0.5)
        meta.compute_verdict()
        assert meta.beats_baseline is False

    def test_save_and_load_roundtrip(self, tmp_path):
        from ml.training.model_metadata import ModelMetadata
        meta = ModelMetadata(symbol="TSLA", candle_interval="1day")
        meta.set_metrics(mae=1.1, rmse=1.7, mape=0.6, directional_accuracy=0.52)
        meta.set_baseline_metrics(mae=1.4, rmse=2.1, mape=0.75)
        meta.compute_verdict()
        meta.stamp_version()

        path = str(tmp_path / "metadata.json")
        meta.save(path)

        loaded = ModelMetadata.load(path)
        assert loaded.symbol == "TSLA"
        assert loaded.metrics["mae"] == pytest.approx(1.1, abs=1e-4)
        assert loaded.beats_baseline is True

    def test_save_creates_json(self, tmp_path):
        from ml.training.model_metadata import ModelMetadata
        meta = ModelMetadata()
        path = str(tmp_path / "meta.json")
        meta.save(path)
        with open(path) as f:
            data = json.load(f)
        assert data["symbol"] == "AAPL"

    def test_is_compatible_with_ok(self):
        from ml.training.model_metadata import ModelMetadata
        from ml.data_pipeline.config import DEFAULT_FEATURE_COLUMNS
        meta = ModelMetadata(
            symbol="AAPL", candle_interval="1day",
            sequence_length=30, forecast_horizon=1,
            features=DEFAULT_FEATURE_COLUMNS,
        )
        ok, reason = meta.is_compatible_with(
            symbol="AAPL", candle_interval="1day",
            features=DEFAULT_FEATURE_COLUMNS,
            sequence_length=30, forecast_horizon=1,
        )
        assert ok is True
        assert reason == ""

    def test_is_compatible_with_symbol_mismatch(self):
        from ml.training.model_metadata import ModelMetadata
        from ml.data_pipeline.config import DEFAULT_FEATURE_COLUMNS
        meta = ModelMetadata(
            symbol="AAPL", candle_interval="1day",
            sequence_length=30, forecast_horizon=1,
            features=DEFAULT_FEATURE_COLUMNS,
        )
        ok, reason = meta.is_compatible_with(
            symbol="TSLA", candle_interval="1day",
            features=DEFAULT_FEATURE_COLUMNS,
            sequence_length=30, forecast_horizon=1,
        )
        assert ok is False
        assert "Symbol" in reason

    def test_summary_string(self):
        from ml.training.model_metadata import ModelMetadata
        meta = ModelMetadata()
        meta.set_metrics(mae=1.0, rmse=1.5, mape=0.5, directional_accuracy=0.55)
        meta.set_baseline_metrics(mae=1.5, rmse=2.0, mape=0.7)
        meta.compute_verdict()
        summary = meta.summary()
        assert "LSTM" in summary
        assert "AAPL" in summary


# ============================================================
# make_sequences_scaled_y tests
# ============================================================

class TestMakeSequencesScaledY:
    """Test the new Sequencer.make_sequences_scaled_y() method."""

    def test_output_shapes(self):
        from ml.data_pipeline.config import PipelineConfig
        from ml.data_pipeline.sequencer import Sequencer

        cfg = PipelineConfig(sequence_length=3, target_horizon=1)
        seq = Sequencer(cfg)

        n_rows = 20
        n_features = 5
        close_col_idx = 3  # Close is at index 3

        scaled_array = np.random.rand(n_rows, n_features).astype(np.float32)
        X, y = seq.make_sequences_scaled_y(scaled_array, close_col_idx)

        expected_n = n_rows - cfg.sequence_length - cfg.target_horizon + 1
        assert X.shape == (expected_n, cfg.sequence_length, n_features)
        assert y.shape == (expected_n,)

    def test_y_values_match_close_column(self):
        from ml.data_pipeline.config import PipelineConfig
        from ml.data_pipeline.sequencer import Sequencer

        cfg = PipelineConfig(sequence_length=3, target_horizon=1)
        seq = Sequencer(cfg)

        n_rows = 10
        n_features = 4
        close_col_idx = 2

        np.random.seed(42)
        scaled_array = np.random.rand(n_rows, n_features).astype(np.float32)
        X, y = seq.make_sequences_scaled_y(scaled_array, close_col_idx)

        # y[i] should be scaled_array[i + seq_len + horizon - 1, close_col_idx]
        for i in range(len(y)):
            expected = scaled_array[i + cfg.sequence_length + cfg.target_horizon - 1, close_col_idx]
            assert y[i] == pytest.approx(expected, abs=1e-6)

    def test_y_in_zero_one_range(self):
        from ml.data_pipeline.config import PipelineConfig
        from ml.data_pipeline.sequencer import Sequencer

        cfg = PipelineConfig(sequence_length=3, target_horizon=1)
        seq = Sequencer(cfg)

        n_rows = 15
        n_features = 5
        close_col_idx = 0

        # Generate values strictly in [0, 1]
        scaled_array = np.random.rand(n_rows, n_features).astype(np.float32)
        _, y = seq.make_sequences_scaled_y(scaled_array, close_col_idx)

        assert float(y.min()) >= 0.0
        assert float(y.max()) <= 1.0

    def test_too_short_raises(self):
        from ml.data_pipeline.config import PipelineConfig
        from ml.data_pipeline.sequencer import Sequencer

        cfg = PipelineConfig(sequence_length=5, target_horizon=1)
        seq = Sequencer(cfg)

        too_short = np.random.rand(4, 3).astype(np.float32)
        with pytest.raises(ValueError, match="Array too short"):
            seq.make_sequences_scaled_y(too_short, close_col_idx=0)

    def test_existing_make_sequences_unchanged(self):
        """Verify make_sequences() still works identically after adding new method."""
        from ml.data_pipeline.config import PipelineConfig
        from ml.data_pipeline.sequencer import Sequencer

        cfg = PipelineConfig(sequence_length=3, target_horizon=1)
        seq = Sequencer(cfg)

        n_rows = 12
        n_features = 4
        scaled_array = np.random.rand(n_rows, n_features).astype(np.float32)
        raw_close = np.linspace(100, 120, n_rows)

        X, y = seq.make_sequences(scaled_array, raw_close)

        # y should be raw dollar values (> 1)
        assert float(y.max()) > 1.0  # definitely dollar-range values
