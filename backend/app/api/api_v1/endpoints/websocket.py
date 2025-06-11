from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

import random
import json

# ... (rest of the ConnectionManager class)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Start a background task to broadcast data
        async def data_sender():
            while True:
                await asyncio.sleep(0.1) # Broadcast every 100ms
                data_point = {
                    "timestamp": asyncio.get_event_loop().time(),
                    "value": random.uniform(-0.5, 1.5) # Simulate ECG signal
                }
                await manager.broadcast(json.dumps(data_point))
        
        sender_task = asyncio.create_task(data_sender())

        while True:
            # Keep the connection alive by waiting for messages (or just sleeping)
            # This part can be used to receive commands from the client in the future
            await websocket.receive_text() # This will block until a message is received

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        if 'sender_task' in locals() and not sender_task.done():
            sender_task.cancel()

