import asyncio
import logging
import json
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from websocket_manager import websocket_manager

logger = logging.getLogger(__name__)
router = APIRouter()

print("--- Initializing websocket_router in websocket.py ---")

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print("--- WebSocket connection attempt received at /ws endpoint ---")
    await websocket.accept()
    
    try:
        # 等待身份识别消息
        first_message = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
        message_data = json.loads(first_message)
        
        if message_data.get("type") == "data_source":
            # 这是一个数据源连接
            if websocket_manager.data_source:
                logger.warning("A data source is already connected. Rejecting new connection.")
                await websocket.close(code=1008, reason="Data source already exists")
                return
                
            # 设置数据源
            websocket_manager.set_data_source(websocket)
            
            # 处理来自数据源的消息
            try:
                # 限制帧率相关变量
                last_broadcast_time = time.time()
                target_interval = 1.0 / 250  # 限制帧率为250fps，匹配ECG常用采样率
                data_buffer = None
                
                while True:
                    # 持续接收数据
                    data = await websocket.receive_text()
                    data_json = json.loads(data)
                    
                    # 将样本加入批量缓冲
                    if data_buffer is None:
                        data_buffer = []
                    data_buffer.append(data_json)
                    
                    # 检查是否到达发送间隔
                    current_time = time.time()
                    if current_time - last_broadcast_time >= target_interval:
                        # 达到间隔时批量推送并清空缓冲
                        if data_buffer:
                            await websocket_manager.broadcast_data({"batch": data_buffer})
                            logger.debug(f"批量发送{len(data_buffer)}点，间隔: {current_time - last_broadcast_time:.4f}秒")
                            data_buffer = []
                            last_broadcast_time = current_time
                    else:
                        # 不发送数据，等待下一次循环
                        await asyncio.sleep(0.001)  # 小的延迟，避免 CPU 超负载
            except WebSocketDisconnect:
                websocket_manager.clear_data_source()
        else:
            # 这是客户端连接
            await websocket_manager.connect_client(websocket)
            
            # 等待客户端断开连接
            try:
                await websocket.receive_text()  # 这只是等待消息以检测断开连接
            except WebSocketDisconnect:
                await websocket_manager.disconnect_client(websocket)
    
    except asyncio.TimeoutError:
        # 如果没有收到身份消息，假定这是客户端
        logger.info("No identification message received, treating as a client connection")
        await websocket_manager.connect_client(websocket)
        
        # 等待客户端断开连接
        try:
            await websocket.receive_text()
        except WebSocketDisconnect:
            await websocket_manager.disconnect_client(websocket)
    
    except WebSocketDisconnect:
        # 连接过程中断开
        if websocket_manager.is_data_source(websocket):
            websocket_manager.clear_data_source()
        else:
            await websocket_manager.disconnect_client(websocket)
    
    except Exception as e:
        # 其他异常处理
        logger.error(f"Error in websocket handler: {e}")
        try:
            await websocket.close(code=1011, reason="Server error")
        except:
            pass
