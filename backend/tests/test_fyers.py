import pytest
import os
from unittest.mock import patch, MagicMock
from app.core.fyers_executor import FyersExecutor

def test_fyers_executor_mock_mode():
    # Force Mock mode via env var
    with patch.dict(os.environ, {"MOCK_FYERS": "true"}):
        executor = FyersExecutor()
        assert executor.mock_mode is True
        
        # Submit order (symbol formatting RELIANCE.NS -> NSE:RELIANCE-EQ)
        order = executor.submit_order(symbol="RELIANCE.NS", qty=10, side="buy", order_type="market")
        assert order.id is not None
        assert order.symbol == "NSE:RELIANCE-EQ"
        assert order.qty == "10"
        assert order.side == "buy"
        assert order.status == "new"
        
        # Poll status
        polled_order = executor.get_order_status(order.id)
        assert polled_order.id == order.id
        assert polled_order.status == "filled"
        assert polled_order.filled_qty == "10"
        assert polled_order.filled_avg_price == "2500.00"

def test_fyers_symbol_formatting():
    with patch.dict(os.environ, {"MOCK_FYERS": "true"}):
        executor = FyersExecutor()
        assert executor._format_symbol("RELIANCE.NS") == "NSE:RELIANCE-EQ"
        assert executor._format_symbol("TCS.BO") == "BSE:TCS-EQ"
        assert executor._format_symbol("NSE:INFY-EQ") == "NSE:INFY-EQ"
        assert executor._format_symbol("SBIN") == "NSE:SBIN-EQ"

def test_fyers_executor_mock_limit_order():
    with patch.dict(os.environ, {"MOCK_FYERS": "true"}):
        executor = FyersExecutor()
        
        # Submit limit order
        order = executor.submit_order(symbol="TCS.BO", qty=5, side="sell", order_type="limit", price=3200.50)
        assert order.type == "limit"
        assert order.limit_price == "3200.50"
        
        polled_order = executor.get_order_status(order.id)
        assert polled_order.status == "filled"
        assert polled_order.filled_avg_price == "3200.50"

def test_fyers_executor_validation_errors():
    with patch.dict(os.environ, {"MOCK_FYERS": "true"}):
        executor = FyersExecutor()
        
        # Invalid side
        with pytest.raises(ValueError, match="Side must be 'buy' or 'sell'"):
            executor.submit_order("RELIANCE.NS", 10, "hold")
            
        # Invalid order type
        with pytest.raises(ValueError, match="Order type must be 'market' or 'limit'"):
            executor.submit_order("RELIANCE.NS", 10, "buy", "stop")
            
        # Missing limit price
        with pytest.raises(ValueError, match="Price must be provided for limit orders"):
            executor.submit_order("RELIANCE.NS", 10, "buy", "limit")

def test_fyers_executor_live_initialization_error():
    # Live mode should raise error if credentials are empty
    with patch.dict(os.environ, {"MOCK_FYERS": "false", "FYERS_CLIENT_ID": "", "FYERS_ACCESS_TOKEN": ""}):
        with pytest.raises(ValueError, match="FYERS_CLIENT_ID and FYERS_ACCESS_TOKEN must be provided in live mode"):
            FyersExecutor()

@patch("requests.post")
def test_fyers_executor_live_mode_order(mock_post):
    # Mock order response from Fyers HTTP POST sync-order
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "s": "ok",
        "message": "Order placed successfully",
        "id": "fyers-order-12345"
    }
    mock_post.return_value = mock_response
    
    with patch.dict(os.environ, {
        "MOCK_FYERS": "false",
        "FYERS_CLIENT_ID": "test-client-id",
        "FYERS_ACCESS_TOKEN": "test-access-token"
    }):
        executor = FyersExecutor()
        assert executor.mock_mode is False
        
        # Submit live order
        order = executor.submit_order(symbol="RELIANCE.NS", qty=15, side="buy")
        assert order.id == "fyers-order-12345"
        assert order.status == "new"
        
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["symbol"] == "NSE:RELIANCE-EQ"
        assert kwargs["json"]["qty"] == 15
        assert kwargs["json"]["side"] == 1
        assert kwargs["json"]["type"] == 2 # market

@patch("requests.get")
def test_fyers_executor_live_mode_get_status(mock_get):
    # Mock status check response from Fyers HTTP GET orders
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "s": "ok",
        "data": [{
            "symbol": "NSE:RELIANCE-EQ",
            "qty": 15,
            "filledQty": 15,
            "side": 1,
            "type": 2,
            "status": 2, # filled
            "price": 0.0,
            "tradedPrice": 2450.25
        }]
    }
    mock_get.return_value = mock_response
    
    with patch.dict(os.environ, {
        "MOCK_FYERS": "false",
        "FYERS_CLIENT_ID": "test-client-id",
        "FYERS_ACCESS_TOKEN": "test-access-token"
    }):
        executor = FyersExecutor()
        status = executor.get_order_status("fyers-order-12345")
        assert status.status == "filled"
        assert status.filled_qty == "15"
        assert status.filled_avg_price == "2450.25"
        
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert kwargs["params"] == {"id": "fyers-order-12345"}
