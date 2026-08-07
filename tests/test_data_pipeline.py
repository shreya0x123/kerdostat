"""
Tests for Day 4 — ML Data Pipeline
====================================
Comprehensive pytest test suite covering:
    1. PipelineConfig validation
    2. DataFetcher (CSV, row count validation)
    3. DataCleaner (NaN filling, dedup, OHLC sanity)
    4. FeatureEngineer (column count, no NaN, indicator values)
    5. Normalizer (scale range, train-only fit, save/load, inverse transform)
    6. Sequencer (X/y shapes, chronological split, leakage check)
    7. DataPreprocessor (full pipeline integration)
"""

from __future__ import annotations

import os
import sys
import tempfile
import pickle

import numpy as np
import pandas as pd
import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.data_pipeline.config import PipelineConfig, DEFAULT_FEATURE_COLUMNS
from ml.data_pipeline.fetcher import DataFetcher
from ml.data_pipeline.cleaner import DataCleaner, CleaningReport
from ml.data_pipeline.feature_engineer import FeatureEngineer
from ml.data_pipeline.normalizer import Normalizer
from ml.data_pipeline.sequencer import Sequencer, DataBundle
from ml.data_pipeline.preprocessor import DataPreprocessor

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SAMPLE_CSV = os.path.join(PROJECT_ROOT, "data", "sample_ohlcv.csv")


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def base_config(tmp_path) -> PipelineConfig:
    """Minimal valid config with a temp artifact directory."""
    return PipelineConfig(
        symbol="AAPL",
        candle_interval="1day",
        sequence_length=3,   # Small: sample CSV has 61 rows; 15% val = ~9 rows → ok
        train_ratio=0.70,
        val_ratio=0.15,
        artifacts_dir=str(tmp_path),
    )


@pytest.fixture
def raw_df() -> pd.DataFrame:
    """Load the project's sample CSV as a DataFrame."""
    from data.loaders import load_csv
    return load_csv(SAMPLE_CSV)


@pytest.fixture
def feature_df(raw_df, base_config) -> pd.DataFrame:
    """Compute feature-engineered DataFrame from sample CSV."""
    cleaner = DataCleaner(base_config)
    df_clean, _ = cleaner.clean(raw_df)
    engineer = FeatureEngineer(base_config)
    return engineer.compute(df_clean)


# ===========================================================================
# 1. PipelineConfig
# ===========================================================================
class TestPipelineConfig:
    def test_default_config_is_valid(self):
        """Default config should pass validation without raising."""
        cfg = PipelineConfig()
        cfg.validate()  # Should not raise

    def test_invalid_candle_interval_raises(self):
        cfg = PipelineConfig(candle_interval="3min")
        with pytest.raises(ValueError, match="candle_interval"):
            cfg.validate()

    def test_invalid_train_ratio_raises(self):
        cfg = PipelineConfig(train_ratio=1.1)
        with pytest.raises(ValueError, match="train_ratio"):
            cfg.validate()

    def test_train_plus_val_too_high_raises(self):
        cfg = PipelineConfig(train_ratio=0.80, val_ratio=0.30)
        with pytest.raises(ValueError, match="train_ratio"):
            cfg.validate()

    def test_test_ratio_is_computed_correctly(self):
        cfg = PipelineConfig(train_ratio=0.70, val_ratio=0.15)
        assert abs(cfg.test_ratio - 0.15) < 1e-6

    def test_n_features_matches_feature_columns(self):
        cfg = PipelineConfig()
        assert cfg.n_features == len(cfg.feature_columns)

    def test_to_dict_is_json_serialisable(self):
        import json
        cfg = PipelineConfig()
        d = cfg.to_dict()
        assert isinstance(d, dict)
        # Should not raise
        json.dumps(d)

    def test_from_dict_round_trip(self):
        cfg = PipelineConfig(symbol="TSLA", sequence_length=60)
        d = cfg.to_dict()
        cfg2 = PipelineConfig.from_dict(d)
        assert cfg2.symbol == "TSLA"
        assert cfg2.sequence_length == 60

    def test_from_dict_ignores_unknown_keys(self):
        """Extra keys in the dict should not cause errors."""
        d = {"symbol": "MSFT", "unknown_key_xyz": 42}
        cfg = PipelineConfig.from_dict(d)
        assert cfg.symbol == "MSFT"


# ===========================================================================
# 2. DataFetcher
# ===========================================================================
class TestDataFetcher:
    def test_fetch_csv_returns_dataframe(self, base_config):
        fetcher = DataFetcher(base_config)
        df, meta = fetcher.fetch_csv(SAMPLE_CSV)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_fetch_csv_returns_metadata(self, base_config):
        fetcher = DataFetcher(base_config)
        _, meta = fetcher.fetch_csv(SAMPLE_CSV)
        required_keys = {"source", "rows", "columns", "date_start", "date_end", "fetched_at"}
        assert required_keys.issubset(meta.keys())

    def test_fetch_csv_file_not_found_raises(self, base_config):
        fetcher = DataFetcher(base_config)
        with pytest.raises(FileNotFoundError):
            fetcher.fetch_csv("/nonexistent/path/data.csv")

    def test_fetch_csv_too_few_rows_raises(self, base_config, tmp_path):
        """A CSV with insufficient rows should raise ValueError."""
        # Write a tiny CSV with only 5 rows
        small_csv = tmp_path / "small.csv"
        small_csv.write_text(
            "Date,Open,High,Low,Close,Volume\n"
            + "\n".join(
                f"2025-01-{i+1:02d},100,101,99,100,1000"
                for i in range(5)
            )
        )
        fetcher = DataFetcher(base_config)
        with pytest.raises(ValueError, match="Insufficient data"):
            fetcher.fetch_csv(str(small_csv))

    def test_fetch_csv_metadata_source_is_csv(self, base_config):
        fetcher = DataFetcher(base_config)
        _, meta = fetcher.fetch_csv(SAMPLE_CSV)
        assert meta["source"].startswith("csv")


# ===========================================================================
# 3. DataCleaner
# ===========================================================================
class TestDataCleaner:
    def test_clean_returns_dataframe_and_report(self, raw_df, base_config):
        cleaner = DataCleaner(base_config)
        df_clean, report = cleaner.clean(raw_df)
        assert isinstance(df_clean, pd.DataFrame)
        assert isinstance(report, CleaningReport)

    def test_clean_removes_duplicate_timestamps(self, raw_df, base_config):
        # Duplicate the first row
        dup_df = pd.concat([raw_df, raw_df.iloc[[0]]])
        cleaner = DataCleaner(base_config)
        df_clean, report = cleaner.clean(dup_df)
        assert report.duplicates_removed >= 1
        assert not df_clean.index.duplicated().any()

    def test_clean_forward_fills_short_nan_gaps(self, raw_df, base_config):
        df = raw_df.copy()
        # Introduce a single NaN in Close at row 10
        df.iloc[10, df.columns.get_loc("Close")] = np.nan
        cleaner = DataCleaner(base_config)
        df_clean, report = cleaner.clean(df)
        assert df_clean.isnull().sum().sum() == 0

    def test_clean_sorts_chronologically(self, raw_df, base_config):
        shuffled = raw_df.sample(frac=1, random_state=42)
        cleaner = DataCleaner(base_config)
        df_clean, _ = cleaner.clean(shuffled)
        assert df_clean.index.is_monotonic_increasing

    def test_clean_missing_required_column_raises(self, base_config):
        bad_df = pd.DataFrame({"Close": [100, 101], "Open": [99, 100]})
        cleaner = DataCleaner(base_config)
        with pytest.raises(ValueError, match="missing required"):
            cleaner.clean(bad_df)

    def test_clean_fixes_high_less_than_low(self, raw_df, base_config):
        df = raw_df.copy()
        # Swap High and Low for one row to create a violation
        df.iloc[5, df.columns.get_loc("High")] = 100.0
        df.iloc[5, df.columns.get_loc("Low")]  = 200.0
        cleaner = DataCleaner(base_config)
        df_clean, report = cleaner.clean(df)
        assert (df_clean["High"] >= df_clean["Low"]).all()
        assert report.ohlc_violations_fixed >= 1

    def test_clean_no_nan_in_output(self, raw_df, base_config):
        cleaner = DataCleaner(base_config)
        df_clean, _ = cleaner.clean(raw_df)
        assert df_clean.isnull().sum().sum() == 0


# ===========================================================================
# 4. FeatureEngineer
# ===========================================================================
class TestFeatureEngineer:
    def test_output_has_all_feature_columns(self, raw_df, base_config):
        cleaner = DataCleaner(base_config)
        df_clean, _ = cleaner.clean(raw_df)
        engineer = FeatureEngineer(base_config)
        df_feat = engineer.compute(df_clean)
        assert set(base_config.feature_columns).issubset(set(df_feat.columns))

    def test_output_has_no_nan(self, raw_df, base_config):
        cleaner = DataCleaner(base_config)
        df_clean, _ = cleaner.clean(raw_df)
        engineer = FeatureEngineer(base_config)
        df_feat = engineer.compute(df_clean)
        assert df_feat.isnull().sum().sum() == 0

    def test_output_row_count_is_reduced_by_warmup(self, raw_df, base_config):
        cleaner = DataCleaner(base_config)
        df_clean, _ = cleaner.clean(raw_df)
        engineer = FeatureEngineer(base_config)
        df_feat = engineer.compute(df_clean)
        # Should have fewer rows than input due to indicator warm-up NaN drop
        assert len(df_feat) < len(df_clean)

    def test_rsi_column_in_valid_range(self, raw_df, base_config):
        cleaner = DataCleaner(base_config)
        df_clean, _ = cleaner.clean(raw_df)
        engineer = FeatureEngineer(base_config)
        df_feat = engineer.compute(df_clean)
        assert (df_feat["RSI"] >= 0).all()
        assert (df_feat["RSI"] <= 100).all()

    def test_bb_width_is_positive(self, feature_df):
        assert (feature_df["BB_Width"] >= 0).all()

    def test_ema_20_is_smoother_than_close(self, feature_df):
        """EMA rolling changes should be less volatile than raw Close changes."""
        # Compare first-difference volatility, not levels — EMA is a smoother
        ema_diff_std   = feature_df["EMA_20"].diff().std()
        close_diff_std = feature_df["Close"].diff().std()
        assert ema_diff_std <= close_diff_std * 1.5, (
            f"EMA diff std ({ema_diff_std:.4f}) unexpectedly high vs "
            f"Close diff std ({close_diff_std:.4f})"
        )


# ===========================================================================
# 5. Normalizer
# ===========================================================================
class TestNormalizer:
    def test_fit_transform_scales_to_0_1(self, feature_df, base_config):
        norm = Normalizer(base_config)
        seq = Sequencer(base_config)
        split = seq.split_dataframe(feature_df)
        scaled = norm.fit_transform(split.train)
        assert scaled.min() >= -1e-7   # Allow tiny floating point tolerance
        assert scaled.max() <= 1.0 + 1e-7

    def test_transform_without_fit_raises(self, feature_df, base_config):
        norm = Normalizer(base_config)
        with pytest.raises(RuntimeError, match="not been fitted"):
            norm.transform(feature_df)

    def test_double_fit_raises(self, feature_df, base_config):
        norm = Normalizer(base_config)
        seq = Sequencer(base_config)
        split = seq.split_dataframe(feature_df)
        norm.fit_transform(split.train)
        with pytest.raises(RuntimeError, match="already fitted"):
            norm.fit_transform(split.val)

    def test_inverse_transform_close_is_accurate(self, feature_df, base_config):
        norm = Normalizer(base_config)
        seq = Sequencer(base_config)
        split = seq.split_dataframe(feature_df)
        scaled_train = norm.fit_transform(split.train)

        # Get the Close column index
        close_idx = list(feature_df.columns).index("Close")
        scaled_close = scaled_train[:, close_idx]

        # Inverse transform
        recovered = norm.inverse_transform_close(scaled_close)
        original = split.train["Close"].values

        np.testing.assert_allclose(recovered, original, rtol=1e-4)

    def test_save_and_load(self, feature_df, base_config, tmp_path):
        norm = Normalizer(base_config)
        seq = Sequencer(base_config)
        split = seq.split_dataframe(feature_df)
        norm.fit_transform(split.train)

        path = str(tmp_path / "scaler.pkl")
        norm.save(path)
        assert os.path.exists(path)

        loaded = Normalizer.load(path, config=base_config)
        assert loaded.is_fitted
        # Should transform without error
        result = loaded.transform(split.val)
        assert result.shape[1] == base_config.n_features


# ===========================================================================
# 6. Sequencer
# ===========================================================================
class TestSequencer:
    def test_split_respects_ratios(self, feature_df, base_config):
        seq = Sequencer(base_config)
        split = seq.split_dataframe(feature_df)
        n = len(feature_df)
        expected_train = int(n * base_config.train_ratio)
        assert len(split.train) == expected_train

    def test_split_preserves_chronological_order(self, feature_df, base_config):
        seq = Sequencer(base_config)
        split = seq.split_dataframe(feature_df)
        # All train timestamps must be before val timestamps
        assert split.train.index.max() <= split.val.index.min()
        assert split.val.index.max() <= split.test.index.min()

    def test_make_sequences_x_shape(self, feature_df, base_config):
        seq = Sequencer(base_config)
        split = seq.split_dataframe(feature_df)
        norm = Normalizer(base_config)
        scaled = norm.fit_transform(split.train)
        raw_close = split.train["Close"].values.astype(np.float32)

        X, y = seq.make_sequences(scaled, raw_close)
        seq_len = base_config.sequence_length
        n_features = base_config.n_features
        assert X.ndim == 3
        assert X.shape[1] == seq_len
        assert X.shape[2] == n_features

    def test_make_sequences_y_is_raw_price(self, feature_df, base_config):
        """y values should be in real dollar price range, not [0, 1]."""
        seq = Sequencer(base_config)
        split = seq.split_dataframe(feature_df)
        norm = Normalizer(base_config)
        scaled = norm.fit_transform(split.train)
        raw_close = split.train["Close"].values.astype(np.float32)

        _, y = seq.make_sequences(scaled, raw_close)
        # Real prices are > 1 for stocks; scaled values would be in [0, 1]
        assert y.max() > 1.0, "y targets appear to be scaled, not raw prices"

    def test_no_data_leakage_between_splits(self, feature_df, base_config):
        """Test timestamps in training split must all precede val/test."""
        seq = Sequencer(base_config)
        split = seq.split_dataframe(feature_df)
        train_dates = set(split.train.index)
        val_dates   = set(split.val.index)
        test_dates  = set(split.test.index)
        # No overlap
        assert train_dates.isdisjoint(val_dates)
        assert train_dates.isdisjoint(test_dates)
        assert val_dates.isdisjoint(test_dates)

    def test_too_short_array_raises(self, base_config):
        seq = Sequencer(base_config)
        # Use 2 rows — always < seq_len(3) + horizon(1) = 4
        too_short = np.zeros((2, base_config.n_features), dtype=np.float32)
        raw_close = np.zeros(2, dtype=np.float32)
        with pytest.raises(ValueError, match="Array too short"):
            seq.make_sequences(too_short, raw_close)


# ===========================================================================
# 7. DataPreprocessor (full integration)
# ===========================================================================
class TestDataPreprocessor:
    def test_run_from_csv_returns_bundle_and_normalizer(self, base_config):
        preprocessor = DataPreprocessor(base_config)
        bundle, norm = preprocessor.run_from_csv(SAMPLE_CSV, save_artifacts=False)
        assert isinstance(bundle, DataBundle)
        assert isinstance(norm, Normalizer)

    def test_bundle_x_shapes_are_3d(self, base_config):
        preprocessor = DataPreprocessor(base_config)
        bundle, _ = preprocessor.run_from_csv(SAMPLE_CSV, save_artifacts=False)
        assert bundle.X_train.ndim == 3
        assert bundle.X_val.ndim == 3
        assert bundle.X_test.ndim == 3

    def test_bundle_y_shapes_are_1d(self, base_config):
        preprocessor = DataPreprocessor(base_config)
        bundle, _ = preprocessor.run_from_csv(SAMPLE_CSV, save_artifacts=False)
        assert bundle.y_train.ndim == 1
        assert bundle.y_val.ndim == 1
        assert bundle.y_test.ndim == 1

    def test_bundle_metadata_has_required_keys(self, base_config):
        preprocessor = DataPreprocessor(base_config)
        bundle, _ = preprocessor.run_from_csv(SAMPLE_CSV, save_artifacts=False)
        required = {"sequence_length", "n_features", "feature_columns", "train_size"}
        assert required.issubset(bundle.metadata.keys())

    def test_save_artifacts_creates_files(self, base_config, tmp_path):
        base_config.artifacts_dir = str(tmp_path)
        preprocessor = DataPreprocessor(base_config)
        bundle, norm = preprocessor.run_from_csv(SAMPLE_CSV, save_artifacts=True)

        # Scaler should exist
        assert os.path.exists(base_config.scaler_path)
        # Metadata JSON should exist
        assert os.path.exists(base_config.metadata_path)

    def test_invalid_config_raises_on_init(self):
        with pytest.raises(ValueError):
            DataPreprocessor(PipelineConfig(candle_interval="invalid"))

    def test_bundle_input_shape_matches_config(self, base_config):
        preprocessor = DataPreprocessor(base_config)
        bundle, _ = preprocessor.run_from_csv(SAMPLE_CSV, save_artifacts=False)
        seq_len, n_feat = bundle.input_shape
        assert seq_len == base_config.sequence_length
        assert n_feat == base_config.n_features
