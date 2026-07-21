import os
import uuid
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger("kerdostat-fyers-executor")

class FyersExecutor:
    def __init__(self):
        # Load environment variables
        self.client_id = os.getenv("FYERS_CLIENT_ID")
        self.access_token = os.getenv("FYERS_ACCESS_TOKEN")
        self.base_url = os.getenv("FYERS_BASE_URL", "https://api-t1.fyers.in/api/v3")
        
        # Check mock flag (default to True if not explicitly false)
        self.mock_mode = os.getenv("MOCK_FYERS", "true").lower() == "true"
        
        self.mock_orders = {}
        
        if not self.mock_mode:
            if not self.client_id or not self.access_token:
                raise ValueError("FYERS_CLIENT_ID and FYERS_ACCESS_TOKEN must be provided in live mode.")
            logger.info("FyersExecutor initialized in LIVE mode.")
        else:
            logger.info("FyersExecutor initialized in MOCK mode.")
            
    def _format_symbol(self, symbol: str) -> str:
        """
        Formats generic tickers to Fyers symbol syntax.
        E.g. RELIANCE.NS -> NSE:RELIANCE-EQ
        """
        sym = symbol.upper()
        if sym.endswith(".NS"):
            return f"NSE:{sym[:-3]}-EQ"
        if sym.endswith(".BO"):
            return f"BSE:{sym[:-3]}-EQ"
        if ":" in sym:
            return sym
        return f"NSE:{sym}-EQ"
            
    def submit_order(
        self, 
        symbol: str, 
        qty: int, 
        side: str, 
        order_type: str = "market", 
        price: Optional[float] = None
    ) -> Any:
        """
        Submits a buy/sell order to Fyers.
        side: "buy" or "sell"
        order_type: "market" or "limit"
        """
        symbol = self._format_symbol(symbol)
        side_val = 1 if side.lower() == "buy" else -1
        type_val = 1 if order_type.lower() == "limit" else 2
        
        if side.lower() not in ["buy", "sell"]:
            raise ValueError("Side must be 'buy' or 'sell'.")
        if order_type.lower() not in ["market", "limit"]:
            raise ValueError("Order type must be 'market' or 'limit'.")
        if order_type.lower() == "limit" and price is None:
            raise ValueError("Price must be provided for limit orders.")
            
        if self.mock_mode:
            order_id = str(uuid.uuid4())
            # Create a mock order entity
            class MockOrder:
                def __init__(self, **entries):
                    self.__dict__.update(entries)
                    
            mock_order = MockOrder(
                id=order_id,
                symbol=symbol,
                qty=str(qty),
                filled_qty="0",
                side=side.lower(),
                type=order_type.lower(),
                status="new",
                limit_price=f"{price:.2f}" if price is not None else None,
                filled_avg_price=None
            )
            self.mock_orders[order_id] = mock_order
            logger.info(f"[MOCK] Submitted Fyers {side.upper()} order for {qty} {symbol} (ID: {order_id})")
            return mock_order
        else:
            # Live Fyers v3 API order dispatch
            url = f"{self.base_url}/orders/sync-order"
            headers = {
                "Authorization": f"{self.client_id}:{self.access_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "symbol": symbol,
                "qty": qty,
                "side": side_val,
                "type": type_val,
                "limitPrice": float(price) if price is not None else 0.0,
                "stopPrice": 0.0,
                "validity": "DAY",
                "disclosedQty": 0,
                "offlineOrder": "False",
                "productType": "INTRADAY"
            }
            
            r = requests.post(url, json=payload, headers=headers, timeout=10)
            if r.status_code != 200:
                raise RuntimeError(f"Fyers API returned status {r.status_code}: {r.text}")
                
            resp_data = r.json()
            if resp_data.get("s") != "ok":
                raise RuntimeError(f"Fyers execution failed: {resp_data.get('message', 'Unknown error')}")
                
            order_id = resp_data.get("id")
            
            class LiveOrder:
                def __init__(self, id, symbol, qty, side, type, limit_price):
                    self.id = id
                    self.symbol = symbol
                    self.qty = str(qty)
                    self.filled_qty = "0"
                    self.side = side
                    self.type = type
                    self.status = "new"
                    self.limit_price = str(limit_price) if limit_price is not None else None
                    self.filled_avg_price = None
                    
            logger.info(f"[LIVE] Submitted Fyers {side.upper()} order for {qty} {symbol} (ID: {order_id})")
            return LiveOrder(order_id, symbol, qty, side.lower(), order_type.lower(), price)
            
    def get_order_status(self, order_id: str) -> Any:
        """
        Polls the status of a Fyers order by its ID.
        """
        if self.mock_mode:
            if order_id not in self.mock_orders:
                raise KeyError(f"Order ID {order_id} not found in mock store.")
                
            mock_order = self.mock_orders[order_id]
            if mock_order.status == "new":
                mock_order.status = "filled"
                mock_order.filled_qty = mock_order.qty
                mock_order.filled_avg_price = mock_order.limit_price or "2500.00"
                logger.info(f"[MOCK] Fyers Order {order_id} transitioned from new -> filled.")
                
            return mock_order
        else:
            # Live Fyers v3 order query
            url = f"{self.base_url}/orders"
            headers = {
                "Authorization": f"{self.client_id}:{self.access_token}",
                "Content-Type": "application/json"
            }
            params = {"id": order_id}
            r = requests.get(url, params=params, headers=headers, timeout=10)
            if r.status_code != 200:
                raise RuntimeError(f"Failed to query Fyers order status: {r.text}")
                
            resp_data = r.json()
            if resp_data.get("s") != "ok" or not resp_data.get("data"):
                raise RuntimeError(f"Failed to fetch Fyers status: {resp_data.get('message', 'Unknown error')}")
                
            order_data = resp_data["data"][0]
            
            # Map Fyers numerical statuses to standard status names
            # Status: 1 (Cancelled), 2 (Filled), 3 (Rejected), 4 (Transit), 5 (Partially Filled), 6 (New)
            status_map = {1: "cancelled", 2: "filled", 3: "rejected", 4: "transit", 5: "partially filled", 6: "new"}
            raw_status = order_data.get("status")
            status_str = status_map.get(raw_status, "unknown")
            
            class FyersOrderDetails:
                def __init__(self, **entries):
                    self.__dict__.update(entries)
                    
            return FyersOrderDetails(
                id=order_id,
                symbol=order_data.get("symbol"),
                qty=str(order_data.get("qty")),
                filled_qty=str(order_data.get("filledQty")),
                side="buy" if order_data.get("side") == 1 else "sell",
                type="limit" if order_data.get("type") == 1 else "market",
                status=status_str,
                limit_price=str(order_data.get("price")),
                filled_avg_price=str(order_data.get("tradedPrice"))
            )
