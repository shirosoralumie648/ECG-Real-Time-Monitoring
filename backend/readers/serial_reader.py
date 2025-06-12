"""
Serial port data reader with support for different data formats
"""
import asyncio
import json
import serial
import struct
import logging
import time
from .base_reader import DataReader

logger = logging.getLogger(__name__)

# 导入信号处理模块
try:
    from ..signal_processing.filters import ECGFilter, ButterworthFilter
    SIGNAL_PROCESSING_AVAILABLE = True
    logger.info("成功加载信号处理模块")
except ImportError:
    SIGNAL_PROCESSING_AVAILABLE = False
    logger.warning("无法导入信号处理模块，将使用原始信号")

class SerialReader(DataReader):
    """Reader for serial port data sources"""
    
    def __init__(self, connection_info, data_format, websocket_manager=None):
        super().__init__(connection_info, data_format, websocket_manager)
        self.port = connection_info.get("port")
        self.baudrate = connection_info.get("baudrate", 115200)  # 默认波特率115200
        self.serial = None
        self.buffer = bytearray()
        
        # 定义justfloat格式的帧尾
        self.JUSTFLOAT_TAIL = bytes([0x00, 0x00, 0x80, 0x7f])
        
        # 导联数量 (justfloat格式传输的导联数)
        self.CHANNEL_COUNT = 8  # I, II, V1, V2, V3, V4, V5, V6
        
        # 导联名称映射
        self.LEAD_NAMES = ['I', 'II', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']
        
        # 过滤器配置：默认启用组合滤波，可通过 connection_info 指定
        filter_type = connection_info.get("filter_type", "combined").lower()
        window_size = connection_info.get("filter_window", 5)
        self.enable_filtering = filter_type != "none"
        
        # 初始化信号处理模块
        self.signal_filter = None
        
        # 如果信号处理模块可用，创建滤波器
        if SIGNAL_PROCESSING_AVAILABLE and self.enable_filtering:
            try:
                self.signal_filter = ECGFilter(filter_type=filter_type, window_size=window_size)
                logger.info(f"已初始化信号处理器: 类型={filter_type}, 窗口大小={window_size}")
            except Exception as e:
                logger.error(f"信号处理器初始化失败: {e}")
                self.signal_filter = None
        
    async def connect(self):
        """Connect to the serial port"""
        try:
            # 使用PySerial打开串口
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1
            )
            logger.info(f"Connected to serial port {self.port} at {self.baudrate} baud")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to serial port {self.port}: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the serial port"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            logger.info(f"Disconnected from serial port {self.port}")
            
        # 重置信号处理器
        if self.signal_filter:
            try:
                self.signal_filter.reset()
                logger.info("已重置信号处理器")
            except Exception as e:
                logger.error(f"重置信号处理器失败: {e}")
    
    def _calculate_derived_leads(self, leads_data):
        """计算衍生导联
        
        基于直接测量的8导联 (I, II, V1-V6) 计算其他4个导联:
        - III = II - I
        - aVR = -(I + II)/2
        - aVL = I - II/2
        - aVF = II - I/2
        """
        i = leads_data[0]  # Lead I
        ii = leads_data[1]  # Lead II
        
        # 计算衍生导联
        iii = ii - i
        avr = -(i + ii) / 2
        avl = i - ii / 2
        avf = ii - i / 2
        
        # 创建缓冲区数据字典
        leads_dict = {
            'I': leads_data[0],
            'II': leads_data[1],
            'III': iii,
            'aVR': avr,
            'aVL': avl, 
            'aVF': avf,
            'V1': leads_data[2],
            'V2': leads_data[3],
            'V3': leads_data[4],
            'V4': leads_data[5],
            'V5': leads_data[6],
            'V6': leads_data[7]
        }
        
        # 如果有信号处理模块，对数据进行滤波
        if self.signal_filter and self.enable_filtering:
            try:
                # 应用滤波器
                filtered_leads = self.signal_filter.apply(leads_dict)
                logger.debug("已应用信号降噪处理")
                return filtered_leads
            except Exception as e:
                logger.error(f"信号处理失败: {e}")
                return leads_dict
        else:
            return leads_dict
    
    async def read_data(self):
        """读取并解析串口数据，采用异步非阻塞实现提高效率"""
        if not self.serial or not self.serial.is_open:
            logger.error("串口未打开")
            await asyncio.sleep(0.1)  # 等待一段时间再重试
            return None
            
        # 使用异步方式读取可用数据
        try:
            # 首先检查是否有数据可读
            if self.serial.in_waiting > 0:
                # 一次性读取所有可用数据
                chunk_size = min(self.serial.in_waiting, 4096)  # 限制每次最大读取量防止缓冲区过载
                data = self.serial.read(chunk_size)
                if data:
                    self.buffer.extend(data)
                    # 数据调试
                    logger.debug(f"收到串口数据: {len(data)} 字节, 缓冲区大小: {len(self.buffer)} 字节")
            else:
                # 如果没有数据可用，短暂等待后返回
                await asyncio.sleep(0.001)
                return None
        except Exception as e:
            logger.error(f"串口读取错误: {str(e)}")
            await asyncio.sleep(0.1)  # 错误后短暂等待
            return None
        
        # 根据配置的数据格式选择解析方法
        try:
            if self.data_format == "justfloat":
                return self._parse_justfloat()
            elif self.data_format == "rawdata":
                return self._parse_rawdata()
            elif self.data_format == "firewater":
                return self._parse_firewater()
            else:
                logger.error(f"不支持的数据格式: {self.data_format}")
                return None
        except Exception as e:
            logger.error(f"数据解析错误 ({self.data_format}): {str(e)}")
            return None
    
    def _parse_justfloat(self):
        """解析justfloat格式数据
        
        格式: N个float值(4字节每个) + 帧尾(0x00, 0x00, 0x80, 0x7f)
        采用多帧检测和处理方式提高效率
        """
        # 如果缓冲区太小，等待更多数据
        min_frame_size = self.CHANNEL_COUNT * 4 + len(self.JUSTFLOAT_TAIL)  # 最小帧大小
        if len(self.buffer) < min_frame_size:
            return None
        
        # 检查是否包含帧尾
        tail_pos = self.buffer.find(self.JUSTFLOAT_TAIL)
        
        # 如果找不到帧尾或缓冲区过大需要清理
        if tail_pos < 0:
            # 更智能的缓冲区管理
            max_buffer_size = 32768  # 增加缓冲区大小限制
            keep_size = 16384       # 保留这么多最近的数据
            
            if len(self.buffer) > max_buffer_size:
                # 保留最后的keep_size字节数据
                self.buffer = self.buffer[-keep_size:]
                logger.info(f"缓冲区调整: 保留最新的 {keep_size} 字节数据")
            return None
        
        # 确保帧尾之前有足够数据
        if tail_pos < self.CHANNEL_COUNT * 4:
            # 可能是帧不完整，清除数据直到这个位置
            self.buffer = self.buffer[tail_pos + len(self.JUSTFLOAT_TAIL):]
            logger.debug(f"数据帧不完整，已清除")
            return None
            
        # 计算帧起始位置
        frame_start = tail_pos - self.CHANNEL_COUNT * 4
        
        # 提取帧数据
        frame_data = bytes(self.buffer[frame_start:tail_pos])  # 转换为bytes对象提高解析效率
        
        # 修改清除策略，只删除到本帧结束位置
        self.buffer = self.buffer[tail_pos + len(self.JUSTFLOAT_TAIL):]
        
        # 批量解析float值，对整个帧的数据进行一次性解析
        try:
            # 使用struct.unpack一次解析所有数据点
            format_str = f'<{self.CHANNEL_COUNT}f'  # 例如8个float: '<8f'
            leads_data = list(struct.unpack(format_str, frame_data))
            
            # 计算所月12个导联并应用信号处理
            all_leads = self._calculate_derived_leads(leads_data)
            
            # 构建返回的数据结构
            result = {
                "timestamp": time.time(),
                "leads": all_leads
            }
            
            # 添加日志记录原始解析的浮点数
            logger.debug(f"Raw parsed values from serial: I={leads_data[0]}, II={leads_data[1]}, "
                         f"V1={leads_data[2]}, V2={leads_data[3]}, V3={leads_data[4]}, "
                         f"V4={leads_data[5]}, V5={leads_data[6]}, V6={leads_data[7]}")
            
            return result
        except Exception as e:
            logger.error(f"浮点解析错误: {str(e)}")
            return None
    
    def _parse_rawdata(self):
        """解析rawdata格式数据
        目前未实现
        """
        logger.warning("rawdata format parsing not implemented yet")
        return None
        
    def _parse_firewater(self):
        """解析firewater格式数据
        目前未实现
        """
        logger.warning("firewater format parsing not implemented yet")
        return None

    # 覆盖基类钩子: 对批量样本做滤波/平滑后再抽帧
    def _process_batch(self, batch):
        if not batch:
            return batch

        # 1. 可选滤波
        if self.signal_filter and self.enable_filtering:
            processed = []
            for sample in batch:
                leads_filtered = self.signal_filter.apply(sample["leads"])
                sample_processed = {**sample, "leads": leads_filtered}
                processed.append(sample_processed)
        else:
            processed = batch

        # 禁用降采样，保留原始频率
        decimated = processed
        return decimated
