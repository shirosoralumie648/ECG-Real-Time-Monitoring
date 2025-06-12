"""
WebSocket连接和数据管理器
"""
import logging
import json
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    管理WebSocket连接和数据传输
    """
    def __init__(self):
        # 存储活跃的客户端WebSocket连接
        self.active_clients: Set[WebSocket] = set()
        # 存储数据源WebSocket
        self.data_source: WebSocket = None
        # 当前活跃的读取器
        self.active_reader = None
        
    async def connect_client(self, websocket: WebSocket):
        """
        连接一个客户端WebSocket
        """
        self.active_clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.active_clients)}")
        
    async def disconnect_client(self, websocket: WebSocket):
        """
        断开一个客户端WebSocket连接
        """
        if websocket in self.active_clients:
            self.active_clients.remove(websocket)
            logger.info(f"Client disconnected. Total clients: {len(self.active_clients)}")
            
    def set_data_source(self, websocket: WebSocket):
        """
        设置一个WebSocket为数据源
        """
        self.data_source = websocket
        logger.info("Data source connected.")
        
    def clear_data_source(self):
        """
        清除数据源WebSocket
        """
        if self.data_source:
            self.data_source = None
            logger.info("Data source disconnected.")
            
    def is_data_source(self, websocket: WebSocket):
        """
        检查某个WebSocket是否为数据源
        """
        return self.data_source == websocket
        
    async def broadcast_data(self, data: dict):
        """
        向所有活跃的客户端广播数据
        """
        if not self.active_clients:
            logger.debug("没有活跃客户端，无需广播数据")
            return
            
        logger.debug(f"准备广播数据给 {len(self.active_clients)} 个客户端")
        logger.debug(f"数据内容: {str(data)[:200]}..." if len(str(data)) > 200 else str(data))
            
        disconnected_clients = set()
        message = json.dumps(data)
        
        for client in self.active_clients:
            try:
                await client.send_text(message)
                logger.debug(f"已发送数据到客户端 {id(client)}")
            except Exception as e:
                logger.error(f"发送数据到客户端时出错: {e}")
                disconnected_clients.add(client)
                
        # 移除断开连接的客户端
        for client in disconnected_clients:
            self.active_clients.remove(client)
            logger.info(f"已移除断开连接的客户端，剩余 {len(self.active_clients)} 个客户端")
            
    def set_active_reader(self, reader):
        """
        设置当前活跃的数据读取器
        """
        self.active_reader = reader
        
    def get_active_reader(self):
        """
        获取当前活跃的数据读取器
        """
        return self.active_reader
        
    async def stop_active_reader(self):
        """
        停止当前活跃的数据读取器
        """
        if self.active_reader:
            await self.active_reader.stop()
            self.active_reader = None
            logger.info("Active reader stopped.")
            
# 全局实例
websocket_manager = WebSocketManager()
