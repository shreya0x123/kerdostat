"""
Tests for Day 5 — LSTM Prediction Model
==========================================
Comprehensive pytest test suite covering:
    1. LSTMModel — architecture initialization and compilation
    2. ModelTrainer — training, save/load, history
    3. ModelEvaluator — MAE/RMSE/MAPE, plot generation
    4. LSTMPredictor — output schema, integration with pipeline
    5. Backward compatibility — all Day 1–3 interfaces unchanged

Note: All tests use a tiny model (units=8, seq_len=5) and minimal
      epochs (2) for speed. This validates interfaces and shapes,
      not model accuracy.

TF imports are lazy (inside fixtures/tests) to prevent pytest collection
from hanging while TensorFlow initialises.
"""

import json
import os
import sys
from typing import Tuple

import numpy as np
import pandas as pd
import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Non-TF imports — safe at module level
from ml.data_pipeline.config import PipelineConfig
from ml.data_pipeline.preprocessor import DataPreprocessor
from ml.data_pipeline.normalizer import Normalizer
from ml.data_pipeline.sequencer import DataBundle
# All ml.models imports are lazy (inside fixtures/tests) to avoid TF startup
# during pytest collection. EvaluationMetrics is imported inside TestModelEvaluator.


SAMPLE_CSV = os.path.join(PROJECT_ROOT, "data", "sample_ohlcv.csv")


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def tiny_config(tmp_path_factory) -> PipelineConfig:
    """
    Minimal config for fast tests — tiny model, short sequences.

    The sample CSV has 61 rows; after 35-row indicator warm-up we have
    ~26 usable rows. With 70/20/10 split: train≈18, val≈5, test≈3.
    sequence_length=3 ensures all splits have enough rows for windowing.
    """
    tmp = tmp_path_factory.mktemp("artifacts")
    return PipelineConfig(
        symbol="AAPL",
        candle_interval="1day",
        sequence_length=3,     # 3 steps — small enough for 61-row CSV
        train_ratio=0.70,
        val_ratio=0.20,        # 20% val → ~5 rows; enough for seq_len=3
        lstm_units_1=8,
        lstm_units_2=4,
        dense_units=4,
        dropout_rate=0.0,
        epochs=2,
        batch_size=4,
        early_stopping_patience=5,
        artifacts_dir=str(tmp),
    )


@pytest.fixture(scope="module")
def bundle_and_norm(tiny_config) -> Tuple[DataBundle, Normalizer]:
    """Run the full Day 4 pipeline once and cache the result."""
    preprocessor = DataPreprocessor(tiny_config)
    return preprocessor.run_from_csv(SAMPLE_CSV, save_artifacts=True)


@pytest.fixture(scope="module")
def trained_model_and_history(tiny_config, bundle_and_norm):
    """Build and train a tiny model once for the test module."""
    from ml.models.lstm_model import LSTMModel
    from ml.models.trainer import ModelTrainer

    bundle, norm = bundle_and_norm
    lstm = LSTMModel(tiny_config)
    model = lstm.build()
    trainer = ModelTrainer(tiny_config)
    history = trainer.train(
        model,
        bundle.X_train, bundle.y_train,
        bundle.X_val,   bundle.y_val,
    )
    return model, trainer, history, norm


# ===========================================================================
# 1. LSTMModel — Architecture
# ===========================================================================
class TestLSTMModel:
    def test_build_returns_keras_model(self, tiny_config):
        from tensorflow import keras
        from ml.models.lstm_model import LSTMModel
        lstm = LSTMModel(tiny_config)
        model = lstm.build()
        assert isinstance(model, keras.Model)

    def test_model_input_shape(self, tiny_config):
        from ml.models.lstm_model import LSTMModel
        lstm = LSTMModel(tiny_config)
        model = lstm.build()
        expected = (None, tiny_config.sequence_length, tiny_config.n_features)
        assert model.input_shape == expected

    def test_model_output_shape(self, tiny_config):
        from ml.models.lstm_model import LSTMModel
        lstm = LSTMModel(tiny_config)
        model = lstm.build()
        assert model.output_shape == (None, 1)

    def test_model_has_trainable_params(self, tiny_config):
        from ml.models.lstm_model import LSTMModel
        lstm = LSTMModel(tiny_config)
        model = lstm.build()
        assert model.count_params() > 0

    def test_model_is_compiled(self, tiny_config):
        from ml.models.lstm_model import LSTMModel
        lstm = LSTMModel(tiny_config)
        model = lstm.build()
        assert model.optimizer is not None

    def test_architecture_summary_is_string(self, tiny_config):
        from ml.models.lstm_model import LSTMModel
        lstm = LSTMModel(tiny_config)
        summary = lstm.architecture_summary()
        assert isinstance(summary, str)
        assert "LSTM" in summary

    def test_forward_pass_output_shape(self, tiny_config):
        from ml.models.lstm_model import LSTMModel
        lstm = LSTMModel(tiny_config)
        model = lstm.build()
        X = np.random.rand(4, tiny_config.sequence_length, tiny_config.n_features).astype(np.float32)
        preds = model.predict(X, verbose=0)
        assert preds.shape == (4, 1)

    def test_model_property_raises_before_build(self, tiny_config):
        from ml.models.lstm_model import LSTMModel
        lstm = LSTMModel(tiny_config)
        with pytest.raises(RuntimeError, match="not been built"):
            _ = lstm.model


# ===========================================================================
# 2. ModelTrainer
# ===========================================================================
class TestModelTrainer:
    def test_train_returns_history_dict(self, trained_model_and_history):
        _, _, history, _ = trained_model_and_history
        assert isinstance(history, dict)
        assert "loss" in history
        assert "val_loss" in history

    def test_history_has_expected_epochs(self, trained_model_and_history):
        _, _, history, _ = trained_model_and_history
        assert len(history["loss"]) >= 1

    def test_training_loss_is_finite(self, trained_model_and_history):
        _, _, history, _ = trained_model_and_history
        for loss in history["loss"]:
            assert np.isfinite(loss), f"Non-finite training loss: {loss}"

    def test_save_model_creates_file(self, trained_model_and_history, tmp_path):
        model, trainer, _, _ = trained_model_and_history
        path = str(tmp_path / "test_model.keras")
        saved = trainer.save_model(model, path=path)
        assert os.path.exists(saved)

    def test_load_model_returns_compiled_model(self, trained_model_and_history, tmp_path):
        from tensorflow import keras
        from ml.models.trainer import ModelTrainer
        model, trainer, _, _ = trained_model_and_history
        path = str(tmp_path / "load_test.keras")
        trainer.save_model(model, path=path)
        loaded = ModelTrainer.load_model(path)
        assert isinstance(loaded, keras.Model)

    def test_load_nonexistent_model_raises(self):
        from ml.models.trainer import ModelTrainer
        with pytest.raises(FileNotFoundError):
            ModelTrainer.load_model("/nonexistent/model.keras")

    def test_save_history_creates_json(self, trained_model_and_history, tmp_path):
        _, trainer, history, _ = trained_model_and_history
        path = str(tmp_path / "history.json")
        saved = trainer.save_history(history, path=path)
        assert os.path.exists(saved)
        with open(saved) as f:
            data = json.load(f)
        assert "loss" in data
        assert "val_loss" in data


# ===========================================================================
# 3. ModelEvaluator
# ===========================================================================
class TestModelEvaluator:
    def test_evaluate_returns_metrics(self, tiny_config, trained_model_and_history, bundle_and_norm):
        from ml.models.evaluator import ModelEvaluator, EvaluationMetrics
        model, _, _, norm = trained_model_and_history
        bundle, _ = bundle_and_norm
        evaluator = ModelEvaluator(tiny_config, norm)
        metrics = evaluator.evaluate(model, bundle.X_test, bundle.y_test)
        assert isinstance(metrics, EvaluationMetrics)


    def test_mae_is_positive(self, tiny_config, trained_model_and_history, bundle_and_norm):
        from ml.models.evaluator import ModelEvaluator
        model, _, _, norm = trained_model_and_history
        bundle, _ = bundle_and_norm
        evaluator = ModelEvaluator(tiny_config, norm)
        metrics = evaluator.evaluate(model, bundle.X_test, bundle.y_test)
        assert metrics.mae >= 0

    def test_rmse_is_positive(self, tiny_config, trained_model_and_history, bundle_and_norm):
        from ml.models.evaluator import ModelEvaluator
        model, _, _, norm = trained_model_and_history
        bundle, _ = bundle_and_norm
        evaluator = ModelEvaluator(tiny_config, norm)
        metrics = evaluator.evaluate(model, bundle.X_test, bundle.y_test)
        assert metrics.rmse >= 0

    def test_mape_is_finite(self, tiny_config, trained_model_and_history, bundle_and_norm):
        from ml.models.evaluator import ModelEvaluator
        model, _, _, norm = trained_model_and_history
        bundle, _ = bundle_and_norm
        evaluator = ModelEvaluator(tiny_config, norm)
        metrics = evaluator.evaluate(model, bundle.X_test, bundle.y_test)
        assert np.isfinite(metrics.mape)
        assert metrics.mape >= 0

    def test_predictions_length_matches_test_set(self, tiny_config, trained_model_and_history, bundle_and_norm):
        from ml.models.evaluator import ModelEvaluator
        model, _, _, norm = trained_model_and_history
        bundle, _ = bundle_and_norm
        evaluator = ModelEvaluator(tiny_config, norm)
        metrics = evaluator.evaluate(model, bundle.X_test, bundle.y_test)
        assert len(metrics.predictions) == len(bundle.y_test)

    def test_to_dict_is_json_serialisable(self, tiny_config, trained_model_and_history, bundle_and_norm):
        from ml.models.evaluator import ModelEvaluator
        model, _, _, norm = trained_model_and_history
        bundle, _ = bundle_and_norm
        evaluator = ModelEvaluator(tiny_config, norm)
        metrics = evaluator.evaluate(model, bundle.X_test, bundle.y_test)
        json.dumps(metrics.to_dict())   # Should not raise

    def test_plot_creates_file(self, tiny_config, trained_model_and_history, bundle_and_norm, tmp_path):
        from ml.models.evaluator import ModelEvaluator
        model, _, _, norm = trained_model_and_history
        bundle, _ = bundle_and_norm
        evaluator = ModelEvaluator(tiny_config, norm)
        metrics = evaluator.evaluate(model, bundle.X_test, bundle.y_test)
        plot_path = str(tmp_path / "test_plot.png")
        saved = evaluator.plot(
            np.array(metrics.actuals),
            np.array(metrics.predictions),
            save_path=plot_path,
            show=False,
        )
        assert os.path.exists(saved)

    def test_mae_calculation(self):
        from ml.models.evaluator import ModelEvaluator
        y_true = np.array([100.0, 200.0, 300.0])
        y_pred = np.array([110.0, 190.0, 310.0])
        assert abs(ModelEvaluator._mae(y_true, y_pred) - 10.0) < 1e-6

    def test_rmse_calculation(self):
        from ml.models.evaluator import ModelEvaluator
        y_true = np.array([100.0, 200.0])
        y_pred = np.array([110.0, 190.0])
        assert abs(ModelEvaluator._rmse(y_true, y_pred) - 10.0) < 1e-6

    def test_mape_calculation(self):
        from ml.models.evaluator import ModelEvaluator
        y_true = np.array([100.0, 200.0])
        y_pred = np.array([110.0, 220.0])
        assert abs(ModelEvaluator._mape(y_true, y_pred) - 10.0) < 1e-6


# ===========================================================================
# 4. LSTMPredictor — Output Schema & Integration
# ===========================================================================
class TestLSTMPredictor:
    @pytest.fixture
    def predictor(self, tiny_config, trained_model_and_history, bundle_and_norm, tmp_path):
        from ml.models.predictor import LSTMPredictor
        model, trainer, _, _ = trained_model_and_history
        _, norm = bundle_and_norm
        model_path = str(tmp_path / "pred_model.keras")
        scaler_path = str(tmp_path / "pred_scaler.pkl")
        trainer.save_model(model, path=model_path)
        norm.save(scaler_path)
        return LSTMPredictor.load(
            model_path=model_path,
            scaler_path=scaler_path,
            config=tiny_config,
        )

    def _load_sample_df(self):
        from data.loaders import load_csv
        return load_csv(SAMPLE_CSV)

    def test_predictor_loads_without_error(self, predictor):
        assert predictor is not None

    def test_predict_returns_dict(self, predictor):
        df = self._load_sample_df()
        result = predictor.predict(df)
        assert isinstance(result, dict)

    def test_predict_schema_has_all_required_keys(self, predictor):
        df = self._load_sample_df()
        result = predictor.predict(df)
        required_keys = {
            "enabled", "prediction_type", "model",
            "predicted_price", "expected_change_percent",
            "prediction_confidence", "forecast_features",
        }
        assert required_keys.issubset(set(result.keys()))

    def test_predict_enabled_is_true(self, predictor):
        df = self._load_sample_df()
        assert predictor.predict(df)["enabled"] is True

    def test_predict_model_is_lstm(self, predictor):
        df = self._load_sample_df()
        assert predictor.predict(df)["model"] == "LSTM"

    def test_predict_type_is_price_forecast(self, predictor):
        df = self._load_sample_df()
        assert predictor.predict(df)["prediction_type"] == "price_forecast"

    def test_predicted_price_is_positive(self, predictor):
        df = self._load_sample_df()
        assert predictor.predict(df)["predicted_price"] > 0

    def test_confidence_is_in_valid_range(self, predictor):
        df = self._load_sample_df()
        conf = predictor.predict(df)["prediction_confidence"]
        assert 0.0 <= conf <= 1.0

    def test_forecast_features_is_list(self, predictor):
        df = self._load_sample_df()
        features = predictor.predict(df)["forecast_features"]
        assert isinstance(features, list)
        assert len(features) > 0

    def test_predict_insufficient_data_raises(self, predictor):
        too_short = pd.DataFrame({
            "Open": [100.0] * 3,
            "High": [101.0] * 3,
            "Low":  [99.0] * 3,
            "Close": [100.0] * 3,
            "Volume": [1000] * 3,
        }, index=pd.date_range("2025-01-01", periods=3))
        with pytest.raises((ValueError, Exception)):
            predictor.predict(too_short)


# ===========================================================================
# 5. Pipeline Integration
# ===========================================================================
class TestPipelineIntegration:
    def test_ml_prediction_dict_is_compatible_with_pipeline_schema(
        self, tiny_config, trained_model_and_history, bundle_and_norm, tmp_path
    ):
        from ml.models.predictor import LSTMPredictor
        from ml.models.trainer import ModelTrainer
        from data.loaders import load_csv

        model, trainer, _, _ = trained_model_and_history
        _, norm = bundle_and_norm
        model_path = str(tmp_path / "integ_model.keras")
        scaler_path = str(tmp_path / "integ_scaler.pkl")
        trainer.save_model(model, path=model_path)
        norm.save(scaler_path)

        predictor = LSTMPredictor.load(
            model_path=model_path,
            scaler_path=scaler_path,
            config=tiny_config,
        )
        df = load_csv(SAMPLE_CSV)
        ml_pred = predictor.predict(df)

        assert ml_pred["enabled"] is True
        assert isinstance(ml_pred["predicted_price"], float)
        assert isinstance(ml_pred["expected_change_percent"], float)
        assert isinstance(ml_pred["prediction_confidence"], float)
        assert isinstance(ml_pred["forecast_features"], list)

    def test_existing_pipeline_still_works_without_ml(self):
        from ml.pipeline import run_analysis
        result = run_analysis(source="csv", filepath=SAMPLE_CSV)
        assert result["signal"] in {"BUY", "SELL", "HOLD"}
        assert 0.0 <= result["confidence"] <= 1.0
        assert result["ml_prediction"]["enabled"] is False
        assert result["ml_confidence"] is None

    def test_xdi_engine_consumes_ml_prediction_when_enabled(
        self, tiny_config, trained_model_and_history, bundle_and_norm, tmp_path
    ):
        from ml.models.predictor import LSTMPredictor
        from data.loaders import load_csv
        from ml.indicators.technical_indicators import compute_all_indicators
        from ml.signals.signal_engine import SignalEngine
        from ml.pipeline import _compute_combined_confidence
        from ml.xdi.xdi_engine import XDIEngine

        model, trainer, _, _ = trained_model_and_history
        _, norm = bundle_and_norm
        model_path = str(tmp_path / "xdi_model.keras")
        scaler_path = str(tmp_path / "xdi_scaler.pkl")
        trainer.save_model(model, path=model_path)
        norm.save(scaler_path)

        predictor = LSTMPredictor.load(
            model_path=model_path,
            scaler_path=scaler_path,
            config=tiny_config,
        )
        df = load_csv(SAMPLE_CSV)
        indicators = compute_all_indicators(df)
        result = SignalEngine().generate_signal(indicators)
        ml_pred = predictor.predict(df)

        result["candle_interval"] = "1day"
        result["ml_prediction"] = ml_pred
        result["rule_confidence"] = result["confidence"]
        result["ml_confidence"] = ml_pred["prediction_confidence"]
        result["confidence"] = _compute_combined_confidence(
            result["rule_confidence"], ml_pred
        )

        explanation = XDIEngine().generate_explanation(result)
        assert "Machine Learning Forecast:" in explanation["detailed_reasoning"]
        assert "price forecast model" in explanation["detailed_reasoning"]


# ===========================================================================
# 6. Backward Compatibility — Day 1–3 unchanged
# ===========================================================================
class TestBackwardCompatibility:
    def test_technical_indicators_unchanged(self):
        from data.loaders import load_csv
        from ml.indicators.technical_indicators import compute_all_indicators
        df = load_csv(SAMPLE_CSV)
        indicators = compute_all_indicators(df)
        required = {"rsi", "ema_20", "macd_line", "macd_signal",
                    "macd_histogram", "bb_upper", "bb_middle", "bb_lower", "close"}
        assert required.issubset(indicators.keys())

    def test_signal_engine_unchanged(self):
        from ml.signals.signal_engine import SignalEngine
        result = SignalEngine().generate_signal({
            "rsi": 22.5, "ema_20": 180.0, "macd_line": 1.5,
            "macd_signal": 0.8, "macd_histogram": 0.7,
            "bb_upper": 190.0, "bb_middle": 182.0, "bb_lower": 174.0,
            "close": 172.0,
        })
        assert result["signal"] == "BUY"

    def test_xdi_engine_unchanged(self):
        from ml.xdi.xdi_engine import XDIEngine
        explanation = XDIEngine().generate_explanation({
            "signal": "HOLD",
            "confidence": 0.45,
            "indicators": {
                "rsi": 50.0, "ema_20": 180.0, "macd_line": 0.1,
                "macd_signal": 0.08, "macd_histogram": 0.02,
                "bb_upper": 188.0, "bb_middle": 182.0, "bb_lower": 176.0,
                "close": 181.0,
            },
            "rules_triggered": [],
            "candle_interval": "1day",
            "ml_prediction": {"enabled": False},
            "rule_confidence": 0.45,
            "ml_confidence": None,
        })
        assert "summary" in explanation
        assert "HOLD" in explanation["summary"]
