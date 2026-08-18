import os
import json
import asyncio
import logging
from typing import List, Dict, Any
from fastapi import WebSocket

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

logger = logging.getLogger("kerdostat-websocket")

class ConnectionManager:
    """
    Manages active WebSocket connections with optional Redis Pub/Sub support.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.redis_url = os.getenv("REDIS_URL")
        self.redis_client = None
        self.pubsub = None
        self.listener_task = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected_clients.append(connection)
        
        for client in disconnected_clients:
            self.disconnect(client)

    async def init_redis(self):
        self.redis_url = os.getenv("REDIS_URL")
        if not self.redis_url:
            logger.info("REDIS_URL not set. Running in local WebSocket mode.")
            return

        if aioredis is None:
            logger.warning("redis package not available. Running in local WebSocket mode.")
            return

        try:
            self.redis_client = aioredis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info(f"Successfully connected to Redis at {self.redis_url}")
            
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe("kerdostat-channel")
            logger.info("Subscribed to Redis channel 'kerdostat-channel'")
            
            self.listener_task = asyncio.create_task(self._redis_listener())
        except Exception as e:
            logger.error(f"Failed to initialize Redis Pub/Sub: {e}. Falling back to local mode.")
            self.redis_client = None

    async def _redis_listener(self):
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        logger.info(f"Received message from Redis Pub/Sub: {data.get('event')}")
                        await self.broadcast(data)
                    except Exception as e:
                        logger.error(f"Error processing Redis Pub/Sub message: {e}")
        except asyncio.CancelledError:
            logger.info("Redis listener task cancelled.")
        except Exception as e:
            logger.error(f"Redis listener encountered error: {e}")

    async def publish(self, message: Dict[str, Any]):
        if self.redis_client:
            try:
                await self.redis_client.publish("kerdostat-channel", json.dumps(message))
                logger.info(f"Published message to Redis Pub/Sub: {message.get('event')}")
                return
            except Exception as e:
                logger.error(f"Failed to publish to Redis: {e}. Falling back to local broadcast.")
        
        await self.broadcast(message)

    async def close(self):
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
        if self.pubsub:
            await self.pubsub.unsubscribe("kerdostat-channel")
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()

manager = ConnectionManager()
