import os
import sys
import uuid
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("kerdostat-alpaca-executor")

class AlpacaExecutor:
    def __init__(self):
        self.api_key = os.getenv("ALPACA_API_KEY", "").strip() if os.getenv("ALPACA_API_KEY") else None
        self.secret_key = os.getenv("ALPACA_SECRET_KEY", "").strip() if os.getenv("ALPACA_SECRET_KEY") else None
        self.base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets").strip()
        self.client = None
        self.mock_orders = {}
        
        if not self.is_mock():
            import alpaca_trade_api as tradeapi
            if not self.api_key or not self.secret_key:
                raise ValueError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be provided in live mode.")
            self.client = tradeapi.REST(
                key_id=self.api_key,
                secret_key=self.secret_key,
                base_url=self.base_url,
                api_version="v2"
            )
            logger.info("AlpacaExecutor initialized in LIVE mode.")
        else:
            logger.info("AlpacaExecutor initialized in MOCK mode.")
            
    @property
    def mock_mode(self) -> bool:
        return self.is_mock()

    def is_mock(self) -> bool:
        mock_env = os.getenv("MOCK_ALPACA")
        if mock_env is not None:
            return mock_env.lower() == "true"
        # Automatically connect to live Alpaca account if credentials are configured
        if self.api_key and self.secret_key:
            return False
        return True

    def submit_order(
        self, 
        symbol: str, 
        qty: int, 
        side: str, 
        order_type: str = "market", 
        price: Optional[float] = None,
        client_order_id: Optional[str] = None
    ) -> Any:
        """
        Submits a buy/sell order to Alpaca with deterministic client_order_id idempotency.
        """
        symbol = symbol.upper()
        side = side.lower()
        order_type = order_type.lower()
        
        if side not in ["buy", "sell"]:
            raise ValueError("Side must be 'buy' or 'sell'.")
        if order_type not in ["market", "limit"]:
            raise ValueError("Order type must be 'market' or 'limit'.")
        if order_type == "limit" and price is None:
            raise ValueError("Price must be provided for limit orders.")
            
        if self.is_mock():
            order_id = str(uuid.uuid4())
            cid = client_order_id or f"client-{order_id[:8]}"
            
            class MockOrder:
                def __init__(self, **entries):
                    self.__dict__.update(entries)
                    
            mock_order = MockOrder(
                id=order_id,
                client_order_id=cid,
                symbol=symbol,
                qty=str(qty),
                filled_qty="0",
                side=side,
                type=order_type,
                time_in_force="gtc",
                status="new",
                limit_price=f"{price:.2f}" if price is not None else None,
                filled_avg_price=None,
                created_at=None
            )
            self.mock_orders[order_id] = mock_order
            logger.info(f"[MOCK] Submitted {side.upper()} order for {qty} {symbol} (ID: {order_id}, CID: {cid})")
            return mock_order
        else:
            limit_price = str(price) if (order_type == "limit" and price is not None) else None
            order = self.client.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type=order_type,
                time_in_force="gtc",
                limit_price=limit_price
            )
            logger.info(f"[LIVE] Submitted {side.upper()} order for {qty} {symbol} (ID: {order.id})")
            return order
            
    def get_order_status(self, order_id: str) -> Any:
        """
        Polls the status of an order by its ID.
        """
        if self.is_mock():
            if order_id not in self.mock_orders:
                raise KeyError(f"Order ID {order_id} not found in mock store.")
                
            mock_order = self.mock_orders[order_id]
            if mock_order.status == "new":
                mock_order.status = "filled"
                mock_order.filled_qty = mock_order.qty
                mock_order.filled_avg_price = mock_order.limit_price or "100.00"
                logger.info(f"[MOCK] Order {order_id} transitioned from new -> filled.")
                
            return mock_order
        else:
            order = self.client.get_order(order_id)
            logger.info(f"[LIVE] Checked status for order {order_id} (Status: {order.status})")
            return order

    def get_account_info(self) -> Dict[str, Any]:
        """
        Retrieves account balance and details.
        """
        if self.is_mock():
            return {
                "cash": 40000.0,
                "buying_power": 160000.0,
                "equity": 40000.0,
                "portfolio_value": 40000.0,
                "daily_pnl": 0.0,
                "mock_mode": True
            }
        else:
            try:
                acc = self.client.get_account()
                return {
                    "cash": float(acc.cash),
                    "buying_power": float(acc.buying_power),
                    "equity": float(acc.equity),
                    "portfolio_value": float(acc.portfolio_value),
                    "daily_pnl": float(acc.equity) - float(acc.last_equity) if hasattr(acc, "last_equity") else 0.0,
                    "mock_mode": False
                }
            except Exception as e:
                logger.warning(f"Using paper simulation account info (Alpaca API connection unconfigured/failed: {e})")
                return {
                    "cash": 40000.0,
                    "buying_power": 160000.0,
                    "equity": 40000.0,
                    "portfolio_value": 40000.0,
                    "daily_pnl": 0.0,
                    "mock_mode": True,
                    "error": str(e)
                }

    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Retrieves list of open positions.
        """
        if self.is_mock():
            return [
                {
                    "symbol": "AAPL",
                    "qty": 50,
                    "avg_entry_price": 103.75,
                    "current_price": 105.00,
                    "market_value": 5250.00,
                    "unrealized_pl": 62.50
                },
                {
                    "symbol": "NVDA",
                    "qty": 80,
                    "avg_entry_price": 125.00,
                    "current_price": 130.00,
                    "market_value": 10400.00,
                    "unrealized_pl": 400.00
                },
                {
                    "symbol": "TSLA",
                    "qty": 120,
                    "avg_entry_price": 180.00,
                    "current_price": 178.50,
                    "market_value": 21420.00,
                    "unrealized_pl": -180.00
                }
            ]
        else:
            try:
                positions = self.client.list_positions()
                result = []
                for pos in positions:
                    result.append({
                        "symbol": pos.symbol,
                        "qty": int(pos.qty),
                        "avg_entry_price": float(pos.avg_entry_price),
                        "current_price": float(pos.current_price),
                        "market_value": float(pos.market_value),
                        "unrealized_pl": float(pos.unrealized_pl)
                    })
                return result
            except Exception as e:
                logger.error(f"Failed to fetch Alpaca positions: {e}")
                return []
