import asyncio
import random
import json
import websockets

class MonitorService:
    def __init__(self):
        self._is_running = False
        self._task = None

    async def _run_monitoring(self):
        uri = "ws://127.0.0.1:8000/ws"
        try:
            async with websockets.connect(uri) as websocket:
                print("Monitor service connected to WebSocket server.")
                # Identify itself as a data source
                await websocket.send(json.dumps({"type": "data_source"}))
                self._is_running = True
                while self._is_running:
                    # In the future, this will be replaced with real data from hardware
                    data_point = {
                        "timestamp": asyncio.get_event_loop().time(),
                        "value": random.uniform(-0.5, 1.5)
                    }
                    await websocket.send(json.dumps(data_point))
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"Failed to connect or run monitoring: {e}")
        finally:
            print("Monitoring stopped.")

    def start(self):
        if not self._is_running:
            print("Starting monitoring service...")
            self._task = asyncio.create_task(self._run_monitoring())
        else:
            print("Monitoring service is already running.")

    def stop(self):
        if self._is_running and self._task:
            print("Stopping monitoring service...")
            self._is_running = False
            self._task.cancel()
            self._task = None
        else:
            print("Monitoring service is not running.")

async def main():
    service = MonitorService()
    service.start()
    try:
        # Keep the service running until interrupted
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        service.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMonitoring service shut down.")
