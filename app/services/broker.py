"""
kerdostat/app/services/broker.py
Alpaca SDK wrapper — single point of contact for all broker calls.
"""
import logging
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta

import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import APIError

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AccountSnapshot:
    account_number: str
    status: str
    equity: float
    cash: float
    buying_power: float
    portfolio_value: float
    currency: str
    paper_trading: bool


class BrokerService:

    def __init__(self):
        self._client: Optional[tradeapi.REST] = None

    def connect(self) -> None:
        if not settings.is_alpaca_configured():
            raise EnvironmentError(
                "Alpaca credentials missing. "
                "Set ALPACA_API_KEY and ALPACA_SECRET_KEY in your .env file."
            )
        self._client = tradeapi.REST(
            key_id=settings.ALPACA_API_KEY,
            secret_key=settings.ALPACA_SECRET_KEY,
            base_url=settings.ALPACA_BASE_URL,
            api_version="v2",
        )
        logger.info("BrokerService: Alpaca client initialised (base_url=%s)", settings.ALPACA_BASE_URL)

    def smoke_test(self) -> AccountSnapshot:
        if self._client is None:
            self.connect()
        try:
            acct = self._client.get_account()
        except APIError as exc:
            logger.error("Alpaca API error during smoke test: %s", exc)
            raise
        snapshot = AccountSnapshot(
            account_number=acct.account_number,
            status=acct.status,
            equity=float(acct.equity),
            cash=float(acct.cash),
            buying_power=float(acct.buying_power),
            portfolio_value=float(acct.portfolio_value),
            currency=acct.currency,
            paper_trading="paper" in settings.ALPACA_BASE_URL,
        )
        logger.info(
            "Smoke test PASSED — account=%s status=%s equity=%.2f",
            snapshot.account_number,
            snapshot.status,
            snapshot.equity,
        )
        return snapshot

    def get_bars(self, symbol: str, timeframe: str = "1Day", limit: int = 50):
        if self._client is None:
            self.connect()
        end = datetime.now()
        start = end - timedelta(days=30)
        bars = self._client.get_bars(
            symbol,
            timeframe,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            limit=limit
        )
        return bars.df

    @property
    def client(self) -> tradeapi.REST:
        if self._client is None:
            self.connect()
        return self._client


broker_service = BrokerService()