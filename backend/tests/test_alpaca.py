import pytest
import os
from unittest.mock import patch, MagicMock
from app.core.alpaca_executor import AlpacaExecutor

def test_alpaca_executor_mock_mode():
    # Force Mock mode via env var
    with patch.dict(os.environ, {"MOCK_ALPACA": "true"}):
        executor = AlpacaExecutor()
        assert executor.mock_mode is True
        
        # Submit order
        order = executor.submit_order(symbol="AAPL", qty=10, side="buy", order_type="market")
        assert order.id is not None
        assert order.symbol == "AAPL"
        assert order.qty == "10"
        assert order.side == "buy"
        assert order.status == "new"
        
        # Poll status
        polled_order = executor.get_order_status(order.id)
        assert polled_order.id == order.id
        assert polled_order.status == "filled"
        assert polled_order.filled_qty == "10"
        assert polled_order.filled_avg_price == "100.00"

def test_alpaca_executor_mock_limit_order():
    with patch.dict(os.environ, {"MOCK_ALPACA": "true"}):
        executor = AlpacaExecutor()
        
        # Submit limit order
        order = executor.submit_order(symbol="TSLA", qty=5, side="sell", order_type="limit", price=185.50)
        assert order.type == "limit"
        assert order.limit_price == "185.50"
        
        polled_order = executor.get_order_status(order.id)
        assert polled_order.status == "filled"
        assert polled_order.filled_avg_price == "185.50"

def test_alpaca_executor_validation_errors():
    with patch.dict(os.environ, {"MOCK_ALPACA": "true"}):
        executor = AlpacaExecutor()
        
        # Invalid side
        with pytest.raises(ValueError, match="Side must be 'buy' or 'sell'"):
            executor.submit_order("AAPL", 10, "hold")
            
        # Invalid order type
        with pytest.raises(ValueError, match="Order type must be 'market' or 'limit'"):
            executor.submit_order("AAPL", 10, "buy", "stop")
            
        # Missing limit price
        with pytest.raises(ValueError, match="Price must be provided for limit orders"):
            executor.submit_order("AAPL", 10, "buy", "limit")

def test_alpaca_executor_live_initialization_error():
    # Live mode should raise error if credentials are empty
    with patch.dict(os.environ, {"MOCK_ALPACA": "false", "ALPACA_API_KEY": "", "ALPACA_SECRET_KEY": ""}):
        with pytest.raises(ValueError, match="ALPACA_API_KEY and ALPACA_SECRET_KEY must be provided"):
            AlpacaExecutor()

@patch("alpaca_trade_api.REST")
def test_alpaca_executor_live_mode_order(mock_rest):
    # Mock the REST client instance
    mock_client_instance = MagicMock()
    mock_rest.return_value = mock_client_instance
    
    # Mock submit_order and get_order return values
    mock_order_response = MagicMock(id="live-order-123", status="new")
    mock_client_instance.submit_order.return_value = mock_order_response
    
    mock_filled_response = MagicMock(id="live-order-123", status="filled")
    mock_client_instance.get_order.return_value = mock_filled_response
    
    with patch.dict(os.environ, {
        "MOCK_ALPACA": "false",
        "ALPACA_API_KEY": "test-key",
        "ALPACA_SECRET_KEY": "test-secret"
    }):
        executor = AlpacaExecutor()
        assert executor.mock_mode is False
        
        # Submit live order
        order = executor.submit_order(symbol="NVDA", qty=15, side="buy")
        assert order.id == "live-order-123"
        assert order.status == "new"
        mock_client_instance.submit_order.assert_called_once_with(
            symbol="NVDA",
            qty=15,
            side="buy",
            type="market",
            time_in_force="gtc",
            limit_price=None
        )
        
        # Get live order status
        status = executor.get_order_status("live-order-123")
        assert status.status == "filled"
        mock_client_instance.get_order.assert_called_once_with("live-order-123")
