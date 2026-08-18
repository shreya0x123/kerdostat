import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.websocket import manager

logger = logging.getLogger("kerdostat-ws-router")
router = APIRouter(tags=["WebSocket Streaming"])

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_json({"event": "connected", "msg": "Kerdostat stream connected"})
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
