"""
tests/conftest.py
==================
Shared pytest fixtures for kerdostat-signal-engine test suite.

Key fixture: ensure SQLite tables are created before every test session.
This replaces the FastAPI lifespan() event that only fires in real uvicorn runs.
"""
import os
import pytest

# ── Force test environment before any app import ──────────────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite:///./kerdostat_test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-kerdostat-2025")
os.environ.setdefault("ALPACA_MOCK_MODE", "true")
os.environ.setdefault("LOG_LEVEL", "WARNING")


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all SQLite tables once before the entire test session."""
    from app.core.database import engine, Base
    from app.models import models  # import models so Base has all tables registered
    Base.metadata.create_all(bind=engine)
    yield
    # Optionally drop tables after session (leave for inspection):
    # Base.metadata.drop_all(bind=engine)
