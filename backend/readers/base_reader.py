"""
Base reader and parser for different data sources and formats
"""
import asyncio
import json
from abc import ABC, abstractmethod
import logging
import time

logger = logging.getLogger(__name__)

class DataReader(ABC):
    """Abstract base class for all data source readers"""
    
    def __init__(self, connection_info, data_format, websocket_manager=None):
        """
        Initialize the data reader
        
        Args:
            connection_info: Dictionary with connection parameters
            data_format: String identifier of data format (rawdata, justfloat, firewater)
            websocket_manager: WebSocket manager reference for broadcasting data
        """
        self.connection_info = connection_info
        self.data_format = data_format
        self.websocket_manager = websocket_manager
        self.is_running = False
        self.task = None
        # 批量发送控制
        self.batch_buffer = []
        self.batch_size = 10  # 每批10个样本
        self.batch_interval = 0.04  # 最长40ms (~25fps)
        self._last_batch_time = time.time()
    
    @abstractmethod
    async def connect(self):
        """Connect to the data source"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Disconnect from the data source"""
        pass
    
    @abstractmethod
    async def read_data(self):
        """Read data from the source and parse according to format"""
        pass
    
    async def start(self):
        """Start the reader task"""
        if self.is_running:
            logger.info("Reader is already running")
            return
        
        await self.connect()
        self.is_running = True
        self.task = asyncio.create_task(self.read_loop())
        logger.info(f"Started {self.__class__.__name__} with format {self.data_format}")
    
    async def stop(self):
        """Stop the reader task"""
        if not self.is_running:
            logger.info("Reader is not running")
            return
            
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
        
        await self.disconnect()
        logger.info(f"Stopped {self.__class__.__name__}")
    
    async def read_loop(self):
        """Main reading loop"""
        try:
            logger.info(f"{self.__class__.__name__} read_loop started")
            while self.is_running:
                data = await self.read_data()
                if data and self.websocket_manager:
                    # 聚合到批量缓冲
                    self.batch_buffer.append(data)
                    now = time.time()
                    if len(self.batch_buffer) >= self.batch_size or now - self._last_batch_time >= self.batch_interval:
                        payload = {"batch": self._process_batch(self.batch_buffer)}
                        await self.websocket_manager.broadcast_data(payload)
                        logger.debug(f"批量广播 {len(self.batch_buffer)} 条数据")
                        self.batch_buffer = []
                        self._last_batch_time = now
                else:
                    # 记录没有数据或websocket_manager为空的情况
                    if not data:
                        logger.debug("没有读取到数据")
                    if not self.websocket_manager:
                        logger.warning("WebSocket管理器未设置，无法广播数据")
                # Small delay to prevent CPU overload
                await asyncio.sleep(0.001)
        except Exception as e:
            logger.error(f"Error in read loop: {e}")
            self.is_running = False

    # --- 新增: 批量后处理钩子，可在子类中覆盖 ---
    def _process_batch(self, batch):
        """Hook for subclasses to process a batch of raw samples before broadcasting.
        Default implementation直接返回原始batch。
        Args:
            batch: list of sample dicts
        Returns:
            list processed_batch
        """
        return batch
