import asyncio
import random
import json
import websockets
import math
import time

class MonitorService:
    def __init__(self):
        self._is_running = False
        self._task = None

    async def _run_monitoring(self):
        uri = "ws://127.0.0.1:8000/api/v1/ws" # 修正WebSocket路径
        try:
            async with websockets.connect(uri) as websocket:
                print("Monitor service connected to WebSocket server.")
                # Identify itself as a data source
                await websocket.send(json.dumps({"type": "data_source"}))
                self._is_running = True
                while self._is_running:
                    # 模拟更真实的心电波形数据
                    current_time = time.time()
                    # 基于时间产生周期性波形
                    t = current_time % 1.0  # 模拟1秒的心跳周期
                    
                    # 模拟类似PQRST波形的心电图
                    if 0 <= t < 0.2:  # P波
                        value = 0.3 * math.sin(t * 10 * math.pi)
                    elif 0.2 <= t < 0.4:  # PR段
                        value = 0.1 * math.sin(t * 5 * math.pi)
                    elif 0.4 <= t < 0.45:  # QRS波群-Q波
                        value = -0.5 * math.sin(t * 20 * math.pi)
                    elif 0.45 <= t < 0.5:  # QRS波群-R波
                        value = 1.5 * math.sin((t - 0.45) * 40 * math.pi)
                    elif 0.5 <= t < 0.55:  # QRS波群-S波
                        value = -0.7 * math.sin(t * 25 * math.pi)
                    elif 0.55 <= t < 0.7:  # ST段
                        value = 0.2 * math.sin(t * 5 * math.pi)
                    elif 0.7 <= t < 0.8:  # T波
                        value = 0.4 * math.sin((t - 0.7) * 15 * math.pi)
                    else:  # U波和TP间期
                        value = 0.1 * math.sin(t * 3 * math.pi)
                        
                    # 增加一些随机噪声
                    value += random.uniform(-0.05, 0.05)
                    
                    data_point = {
                        "timestamp": current_time,
                        "value": value
                    }
                    await websocket.send(json.dumps(data_point))
                    # 增加到100Hz的采样率
                    await asyncio.sleep(0.01)
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
