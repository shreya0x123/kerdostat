"""
Kerdostat ML Data Pipeline — Package Init
==========================================
Day 4: Machine Learning data preparation pipeline.

Modules:
    config          — PipelineConfig dataclass (all tunable parameters)
    fetcher         — Historical OHLCV data acquisition (wraps Day 1 loaders)
    cleaner         — Data validation, deduplication, NaN handling
    feature_engineer — Column-level technical indicator computation
    normalizer      — MinMaxScaler fit/transform, save/load
    sequencer       — Sliding-window sequences, targets, train/val/test split
    preprocessor    — Pipeline orchestrator → DataBundle
"""
