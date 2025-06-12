"""
ECG信号处理模块
提供多种滤波算法用于消除ECG信号的噪声
"""
import numpy as np
from collections import deque
import logging

logger = logging.getLogger(__name__)

class ECGFilter:
    """ECG信号滤波器类"""
    
    def __init__(self, filter_type="combined", window_size=5, fix_polarity=True):
        """
        初始化滤波器
        
        Args:
            filter_type: 滤波器类型，可选值：'ma'(移动平均), 'median'(中值滤波), 'combined'(组合滤波)
            window_size: 滤波窗口大小
            fix_polarity: 是否自动修正波峰极性，确保QRS波向上
        """
        self.filter_type = filter_type
        self.window_size = window_size
        self.fix_polarity = fix_polarity
        
        # 为每个导联创建数据缓冲区和极性检测
        self.lead_buffers = {}
        self.lead_polarities = {}  # 存储每个导联的极性信息
        self.polarity_detection_window = 100  # 使用100个样本点确定极性
        self.polarity_samples = {}
        
        # 支持的导联列表
        self.lead_names = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']
        self.limb_leads = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF']  # 仅这6个导联进行极性检测
        
        # 为每个导联初始化缓冲区和极性
        for lead in self.lead_names:
            self.lead_buffers[lead] = deque(maxlen=window_size)
            self.lead_polarities[lead] = 1.0  # 默认极性为正
            self.polarity_samples[lead] = []
            
        logger.info(f"已初始化ECG滤波器: 类型={filter_type}, 窗口大小={window_size}, 极性修正={fix_polarity}")
            
    def apply(self, ecg_data):
        """
        应用滤波器到ECG数据
        
        Args:
            ecg_data: 包含所有导联数据的字典
            
        Returns:
            处理后的ECG数据
        """
        if not isinstance(ecg_data, dict):
            logger.warning(f"ECG数据格式错误: {type(ecg_data)}")
            return ecg_data
            
        filtered_data = {}
        
        # 处理每个导联的数据
        for lead, value in ecg_data.items():
            if lead not in self.lead_buffers:
                filtered_data[lead] = value
                continue
            
            # 收集样本用于极性检测
            if self.fix_polarity and len(self.polarity_samples[lead]) < self.polarity_detection_window and lead in self.limb_leads:
                self.polarity_samples[lead].append(value)
                # 如果收集够了足够的样本，确定极性
                if len(self.polarity_samples[lead]) == self.polarity_detection_window:
                    self._determine_polarity(lead)
            
            # 应用极性修正（仅对肚体导联）
            corrected_value = value
            if self.fix_polarity and self.lead_polarities[lead] == -1.0 and lead in self.limb_leads:
                corrected_value = -value  # 反转信号
                
            # 将当前值添加到缓冲区
            self.lead_buffers[lead].append(corrected_value)
            
            # 根据选择的滤波方法进行处理
            if self.filter_type == "ma":
                filtered_data[lead] = self._moving_average(self.lead_buffers[lead])
            elif self.filter_type == "median":
                filtered_data[lead] = self._median_filter(self.lead_buffers[lead])
            elif self.filter_type == "combined":
                # 先应用中值滤波去除尖峰噪声，再应用移动平均平滑
                median_filtered = self._median_filter(self.lead_buffers[lead])
                filtered_data[lead] = self._moving_average([median_filtered] if isinstance(median_filtered, (int, float)) else median_filtered)
            else:
                filtered_data[lead] = corrected_value
                
        return filtered_data
    
    def _moving_average(self, data):
        """
        应用移动平均滤波
        
        Args:
            data: 输入数据序列
        
        Returns:
            滤波后的当前值
        """
        if len(data) == 0:
            return 0
            
        return sum(data) / len(data)
    
    def _median_filter(self, data):
        """
        应用中值滤波
        
        Args:
            data: 输入数据序列
            
        Returns:
            滤波后的当前值
        """
        if len(data) == 0:
            return 0
            
        return np.median(list(data))
    
    def _determine_polarity(self, lead):
        """
        确定导联信号的极性
        
        通过分析信号特征判断QRS波峰是否向上
        如果QRS波峰应该向上但实际向下，则翻转信号
        """
        samples = self.polarity_samples[lead]
        if not samples:
            return
            
        # QRS波峰通常是信号中振幅最大的部分
        # 我们通过比较正向峰值和负向峰值的大小来确定极性
        max_peak = max(samples)
        min_peak = min(samples)
        
        # 计算正负峰值的绝对值比率
        if abs(min_peak) > abs(max_peak) * 1.2:  # 如果负向峰值明显大于正向峰值
            # 信号极性需要反转
            self.lead_polarities[lead] = -1.0
            logger.info(f"导联 {lead} 检测到反向极性，已进行极性修正")
        else:
            self.lead_polarities[lead] = 1.0
            
    def reset(self):
        """重置所有缓冲区和极性检测"""
        for lead in self.lead_names:
            self.lead_buffers[lead].clear()
            self.polarity_samples[lead] = []
            self.lead_polarities[lead] = 1.0
            
        logger.info("已重置所有ECG滤波器缓冲区和极性检测")

class ButterworthFilter:
    """
    巴特沃斯滤波器实现 - 用于更高级的ECG信号滤波
    需要scipy库支持
    """
    
    def __init__(self, lowcut=0.5, highcut=40, fs=250, order=2):
        """
        初始化巴特沃斯滤波器
        
        Args:
            lowcut: 低频截止频率
            highcut: 高频截止频率 
            fs: 采样频率
            order: 滤波器阶数
        """
        try:
            from scipy import signal
            self.signal = signal
            
            nyq = 0.5 * fs
            low = lowcut / nyq
            high = highcut / nyq
            
            # 创建带通滤波器系数
            self.b, self.a = signal.butter(order, [low, high], btype='band')
            
            # 为每个导联初始化状态
            self.lead_states = {lead: None for lead in ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']}
            
            logger.info(f"已初始化巴特沃斯滤波器: 低截={lowcut}Hz, 高截={highcut}Hz, 采样率={fs}Hz, 阶数={order}")
            self.initialized = True
            
        except ImportError:
            logger.warning("无法导入scipy库，巴特沃斯滤波器不可用")
            self.initialized = False
    
    def apply(self, ecg_data):
        """
        应用巴特沃斯滤波器到ECG数据
        
        Args:
            ecg_data: 包含所有导联数据的字典
            
        Returns:
            处理后的ECG数据
        """
        if not self.initialized:
            return ecg_data
            
        filtered_data = {}
        
        for lead, value in ecg_data.items():
            if lead not in self.lead_states:
                filtered_data[lead] = value
                continue
                
            # 应用滤波器并更新状态
            filtered_value, self.lead_states[lead] = self.signal.lfilter(
                self.b, self.a, [value], zi=self.lead_states[lead] if self.lead_states[lead] is not None else self.signal.lfilter_zi(self.b, self.a)
            )
            
            filtered_data[lead] = filtered_value[0]
            
        return filtered_data
        
    def reset(self):
        """重置滤波器状态"""
        if not self.initialized:
            return
            
        for lead in self.lead_states:
            self.lead_states[lead] = None
            
        logger.info("已重置巴特沃斯滤波器状态")
