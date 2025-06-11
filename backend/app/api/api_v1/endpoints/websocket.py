from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import asyncio
from typing import List

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.clients: List[WebSocket] = []
        self.data_source: WebSocket | None = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

    def disconnect(self, websocket: WebSocket):
        if websocket in self.clients:
            self.clients.remove(websocket)
            print(f"Client disconnected. Total clients: {len(self.clients)}")
        if self.data_source == websocket:
            self.data_source = None
            print("Data source disconnected.")

    async def broadcast_to_clients(self, message: str):
        if self.clients:
            tasks = [client.send_text(message) for client in self.clients]
            await asyncio.gather(*tasks, return_exceptions=True)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Wait for an identification message for a short period.
        first_message = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
        message_data = json.loads(first_message)

        if message_data.get("type") == "data_source":
            # This is the data source connection
            if manager.data_source is not None:
                print("A data source is already connected. Rejecting new connection.")
                await websocket.close(code=1008, reason="Data source already connected")
                return

            manager.data_source = websocket
            print("Data source connected.")
            try:
                # Loop to receive data from the source and broadcast it
                while True:
                    data = await websocket.receive_text()
                    await manager.broadcast_to_clients(data)
            finally:
                manager.disconnect(websocket)
        else:
            # Message received, but not a valid data_source identifier
            await websocket.close(code=1002, reason="Invalid identification message")

    except asyncio.TimeoutError:
        # No message received within timeout, so it's a client.
        manager.clients.append(websocket)
        print(f"Client connected. Total clients: {len(manager.clients)}")
        try:
            # Keep the connection open to receive broadcasts. The loop will exit on disconnect.
            while True:
                await websocket.receive_text() # This just waits for a message to detect disconnect
        finally:
            manager.disconnect(websocket)

    except (json.JSONDecodeError, WebSocketDisconnect):
        # Disconnect if the first message isn't valid JSON or if a disconnect occurs.
        manager.disconnect(websocket)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        manager.disconnect(websocket)

