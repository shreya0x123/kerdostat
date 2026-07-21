import pytest
import os
import json
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.main import ConnectionManager

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.anyio
async def test_connection_manager_local_mode():
    # Test local mode when REDIS_URL is not set
    with patch.dict(os.environ, {"REDIS_URL": ""}):
        manager = ConnectionManager()
        # Initialize
        await manager.init_redis()
        assert manager.redis_client is None
        assert manager.pubsub is None
        
        # Mock a websocket connection
        mock_ws = AsyncMock()
        await manager.connect(mock_ws)
        assert mock_ws in manager.active_connections
        
        # Local publish calls broadcast directly
        message = {"event": "test"}
        await manager.publish(message)
        mock_ws.send_json.assert_called_once_with(message)
        
        # Disconnect
        manager.disconnect(mock_ws)
        assert mock_ws not in manager.active_connections

@pytest.mark.anyio
@patch("redis.asyncio.from_url")
async def test_connection_manager_redis_mode(mock_from_url):
    # Test redis mode when REDIS_URL is set
    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock()
    mock_redis.publish = AsyncMock()
    mock_redis.close = AsyncMock()
    
    mock_pubsub = AsyncMock()
    mock_redis.pubsub.return_value = mock_pubsub
    mock_from_url.return_value = mock_redis
    
    with patch.dict(os.environ, {"REDIS_URL": "redis://localhost:6379"}):
        manager = ConnectionManager()
        await manager.init_redis()
        
        assert manager.redis_client == mock_redis
        assert manager.pubsub == mock_pubsub
        
        # Verify publish writes to redis channel
        message = {"event": "test-redis"}
        await manager.publish(message)
        mock_redis.publish.assert_called_once_with("kerdostat-channel", json.dumps(message))
        
        # Cleanup
        await manager.close()
        mock_pubsub.unsubscribe.assert_called_once_with("kerdostat-channel")
