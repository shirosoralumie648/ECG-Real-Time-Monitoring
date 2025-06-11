# data_processing_service.py

import numpy as np
import logging
import time
import threading
from datetime import datetime
from collections import deque
from scipy import signal

# 导入必要的服务
from .data_acquisition_service import data_acquisition_service
from ..data.database_manager import database_manager

class DataProcessingService:
    """数据处理服务类，负责信号处理、滤波、特征提取"""
    
    def __init__(self):
        self.is_processing = False
        self.processing_thread = None
        self.stop_thread = False
        self.data_listeners = []
        self.buffer_size = 2000  # 缓冲区大小（样本数）
        self.processed_data = {
            'ecg': deque(maxlen=self.buffer_size),
            'filtered_ecg': deque(maxlen=self.buffer_size),
            'heart_rate': deque(maxlen=self.buffer_size),
            'rr_intervals': deque(maxlen=self.buffer_size),
            'respiration': deque(maxlen=self.buffer_size),
            'spo2': deque(maxlen=self.buffer_size),
            'temperature': deque(maxlen=self.buffer_size),
            'qrs_peaks': deque(maxlen=100),
            'timestamp': deque(maxlen=self.buffer_size)
        }
        self.logger = logging.getLogger('data_processing_service')
        
        # 滤波器参数
        self.fs = 250  # 采样率（Hz）
        self.filter_configs = {
            'ecg_bandpass': {
                'lowcut': 0.5,  # 低通截止频率（Hz）
                'highcut': 40,  # 高通截止频率（Hz）
                'order': 2      # 滤波器阶数
            },
            'respiration_lowpass': {
                'cutoff': 1.0,  # 截止频率（Hz）
                'order': 2      # 滤波器阶数
            }
        }
        
        # 注册为数据采集服务的监听器
        data_acquisition_service.register_data_listener(self._on_new_data)
    
    def start_processing(self, config=None):
        """开始数据处理
        
        Args:
            config (dict, optional): 处理配置参数
        
        Returns:
            dict: 启动结果
        """
        if self.is_processing:
            return {'success': False, 'message': '数据处理已在进行中'}
        
        try:
            # 更新配置
            if config:
                if 'buffer_size' in config:
                    new_size = config['buffer_size']
                    self.buffer_size = new_size
                    for key in self.processed_data:
                        self.processed_data[key] = deque(self.processed_data[key], maxlen=new_size)
                
                if 'sampling_rate' in config:
                    self.fs = config['sampling_rate']
                
                if 'filter_configs' in config:
                    self.filter_configs.update(config['filter_configs'])
            
            # 启动处理线程
            self.stop_thread = False
            self.is_processing = True
            self.processing_thread = threading.Thread(target=self._processing_loop)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            
            return {
                'success': True,
                'message': '数据处理已启动',
                'config': {
                    'buffer_size': self.buffer_size,
                    'sampling_rate': self.fs,
                    'filter_configs': self.filter_configs
                }
            }
        except Exception as e:
            self.logger.error(f"启动数据处理失败: {str(e)}")
            return {'success': False, 'message': f'启动数据处理失败: {str(e)}'}
    
    def stop_processing(self):
        """停止数据处理
        
        Returns:
            dict: 停止结果
        """
        if not self.is_processing:
            return {'success': False, 'message': '没有正在进行的数据处理'}
        
        try:
            # 停止处理线程
            self.stop_thread = True
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(2.0)  # 等待线程结束，最多2秒
            
            # 重置状态
            self.is_processing = False
            
            return {
                'success': True,
                'message': '数据处理已停止'
            }
        except Exception as e:
            self.logger.error(f"停止数据处理失败: {str(e)}")
            return {'success': False, 'message': f'停止数据处理失败: {str(e)}'}
    
    def get_processing_status(self):
        """获取数据处理状态
        
        Returns:
            dict: 处理状态
        """
        status = {
            'is_processing': self.is_processing,
            'buffer_size': self.buffer_size,
            'sampling_rate': self.fs,
            'buffer_usage': {k: len(v) for k, v in self.processed_data.items()}
        }
        return {'success': True, 'status': status}
    
    def get_processed_data(self, data_type=None, samples=100):
        """获取处理后的数据
        
        Args:
            data_type (str, optional): 数据类型，如果为None则返回所有类型
            samples (int, optional): 样本数量
        
        Returns:
            dict: 处理后的数据
        """
        if not self.is_processing:
            return {'success': False, 'message': '数据处理未启动'}
        
        try:
            result = {}
            
            if data_type and data_type in self.processed_data:
                # 获取指定类型的数据
                buffer = self.processed_data[data_type]
                data = list(buffer)[-samples:] if len(buffer) > 0 else []
                result[data_type] = data
            else:
                # 获取所有类型的数据
                for data_type, buffer in self.processed_data.items():
                    data = list(buffer)[-samples:] if len(buffer) > 0 else []
                    result[data_type] = data
            
            return {
                'success': True,
                'data': result,
                'timestamp': datetime.now().isoformat(),
                'samples': samples
            }
        except Exception as e:
            self.logger.error(f"获取处理数据失败: {str(e)}")
            return {'success': False, 'message': f'获取处理数据失败: {str(e)}'}
    
    def register_data_listener(self, listener):
        """注册数据监听器
        
        Args:
            listener (function): 监听器函数
        
        Returns:
            bool: 是否注册成功
        """
        if listener not in self.data_listeners:
            self.data_listeners.append(listener)
            return True
        return False
    
    def unregister_data_listener(self, listener):
        """取消注册数据监听器
        
        Args:
            listener (function): 监听器函数
        
        Returns:
            bool: 是否取消成功
        """
        if listener in self.data_listeners:
            self.data_listeners.remove(listener)
            return True
        return False
    
    def _on_new_data(self, data, timestamp):
        """处理新到达的数据
        
        Args:
            data (dict): 数据包
            timestamp (datetime): 时间戳
        """
        if not self.is_processing:
            return
        
        try:
            # 将原始数据添加到缓冲区
            self.processed_data['timestamp'].append(timestamp)
            
            # 处理ECG数据
            if 'ecg' in data:
                ecg_value = data['ecg']
                self.processed_data['ecg'].append(ecg_value)
                
                # 实时滤波（如果有足够的数据）
                if len(self.processed_data['ecg']) > 10:  # 确保有足够的数据点进行滤波
                    try:
                        # 获取最近的一段ECG数据进行滤波
                        recent_ecg = list(self.processed_data['ecg'])[-250:]  # 取最近1秒的数据
                        filtered = self._apply_bandpass_filter(recent_ecg)
                        self.processed_data['filtered_ecg'].append(filtered[-1])  # 存储最新的滤波结果
                    except Exception as e:
                        self.logger.error(f"ECG滤波失败: {str(e)}")
                        # 如果滤波失败，使用原始数据
                        self.processed_data['filtered_ecg'].append(ecg_value)
                
                # 每当积累了足够的数据，就进行QRS检测
                if len(self.processed_data['filtered_ecg']) >= 250:  # 积累1秒的数据
                    try:
                        # 取最近几秒的数据进行QRS检测
                        data_for_qrs = list(self.processed_data['filtered_ecg'])[-750:]  # 取最近3秒的数据
                        r_peaks = self._detect_qrs_peaks(data_for_qrs)
                        
                        # 将新检测到的R峰添加到缓冲区（转换索引位置）
                        if r_peaks is not None and len(r_peaks) > 0:
                            for peak in r_peaks:
                                if peak >= 500:  # 只保留最后1秒内的新峰值
                                    # 计算实际在filtered_ecg中的索引
                                    actual_index = len(self.processed_data['filtered_ecg']) - (750 - peak)
                                    if 0 <= actual_index < len(self.processed_data['filtered_ecg']):
                                        self.processed_data['qrs_peaks'].append(actual_index)
                        
                        # 计算心率和RR间期
                        if len(self.processed_data['qrs_peaks']) >= 2:
                            qrs_peaks = list(self.processed_data['qrs_peaks'])
                            qrs_timestamps = [list(self.processed_data['timestamp'])[i] if i < len(self.processed_data['timestamp']) else None for i in qrs_peaks]
                            qrs_timestamps = [ts for ts in qrs_timestamps if ts is not None]
                            
                            if len(qrs_timestamps) >= 2:
                                # 计算最近两个R峰之间的时间差（RR间期，单位：毫秒）
                                last_rr = (qrs_timestamps[-1] - qrs_timestamps[-2]).total_seconds() * 1000
                                self.processed_data['rr_intervals'].append(last_rr)
                                
                                # 计算心率（每分钟心跳次数）
                                heart_rate = 60000 / last_rr  # 60000毫秒/分钟 除以 RR间期(毫秒)
                                self.processed_data['heart_rate'].append(heart_rate)
                    except Exception as e:
                        self.logger.error(f"QRS检测失败: {str(e)}")
            
            # 处理其他生理信号
            if 'respiration' in data:
                resp_value = data['respiration']
                self.processed_data['respiration'].append(resp_value)
                # 可以添加呼吸信号的处理逻辑
            
            if 'spo2' in data:
                self.processed_data['spo2'].append(data['spo2'])
            
            if 'temperature' in data:
                self.processed_data['temperature'].append(data['temperature'])
            
            # 通知所有监听器
            processed_result = {}
            for key, buffer in self.processed_data.items():
                if len(buffer) > 0:
                    processed_result[key] = buffer[-1]  # 获取每个缓冲区的最新值
            
            for listener in self.data_listeners:
                try:
                    listener(processed_result, timestamp)
                except Exception as e:
                    self.logger.error(f"数据监听器处理失败: {str(e)}")
        except Exception as e:
            self.logger.error(f"处理新数据失败: {str(e)}")
    
    def _processing_loop(self):
        """数据处理主循环"""
        while not self.stop_thread and self.is_processing:
            try:
                # 后台处理逻辑，例如定期计算特征、执行复杂分析等
                # 大部分实时处理已在_on_new_data中完成
                
                # 这里可以添加一些定期执行的处理任务
                # 例如，每隔几秒计算心率变异性指标等
                
                time.sleep(0.1)  # 避免CPU使用过高
            except Exception as e:
                self.logger.error(f"处理循环出错: {str(e)}")
                time.sleep(1)
    
    def _apply_bandpass_filter(self, data):
        """应用带通滤波器
        
        Args:
            data (list): 需要滤波的数据列表
        
        Returns:
            list: 滤波后的数据
        """
        config = self.filter_configs['ecg_bandpass']
        nyquist = 0.5 * self.fs
        low = config['lowcut'] / nyquist
        high = config['highcut'] / nyquist
        order = config['order']
        
        b, a = signal.butter(order, [low, high], btype='band')
        y = signal.filtfilt(b, a, data)
        return y.tolist()
    
    def _apply_lowpass_filter(self, data, filter_type='respiration_lowpass'):
        """应用低通滤波器
        
        Args:
            data (list): 需要滤波的数据列表
            filter_type (str): 滤波器类型
        
        Returns:
            list: 滤波后的数据
        """
        config = self.filter_configs[filter_type]
        nyquist = 0.5 * self.fs
        cutoff = config['cutoff'] / nyquist
        order = config['order']
        
        b, a = signal.butter(order, cutoff, btype='low')
        y = signal.filtfilt(b, a, data)
        return y.tolist()
    
    def _detect_qrs_peaks(self, ecg_data):
        """检测QRS波群中的R峰
        
        Args:
            ecg_data (list): ECG数据
        
        Returns:
            list: R峰的索引列表
        """
        # Pan-Tompkins算法简化版
        try:
            # 步骤1: 对信号进行微分，突出R峰的斜率
            diff_ecg = np.diff(ecg_data)
            
            # 步骤2: 平方，使所有值为正
            squared = np.square(diff_ecg)
            
            # 步骤3: 移动平均，平滑信号
            window_size = 30  # 根据实际情况调整窗口大小
            weights = np.ones(window_size) / window_size
            convolved = np.convolve(squared, weights, mode='same')
            
            # 步骤4: 设置阈值（这里使用简单的方法设置阈值）
            threshold = 0.7 * np.max(convolved)  # 使用最大值的70%作为阈值
            
            # 步骤5: 寻找超过阈值的峰值
            peaks = []
            for i in range(1, len(convolved)-1):
                if convolved[i] > threshold and convolved[i] > convolved[i-1] and convolved[i] > convolved[i+1]:
                    peaks.append(i)
            
            # 步骤6: 进行峰值合并（如果两个峰值太近，只保留较大的一个）
            min_distance = 40  # 最小RR间隔（最高可能心率约为180bpm时的间隔）
            final_peaks = []
            i = 0
            while i < len(peaks):
                current_peak = peaks[i]
                current_value = convolved[current_peak]
                
                # 查找接下来min_distance范围内的所有峰值
                j = i + 1
                while j < len(peaks) and peaks[j] - current_peak < min_distance:
                    if convolved[peaks[j]] > current_value:
                        # 如果找到更大的峰值，更新当前峰值
                        current_peak = peaks[j]
                        current_value = convolved[current_peak]
                    j += 1
                
                final_peaks.append(current_peak)
                i = j  # 跳过已经处理过的峰值
            
            return final_peaks
        except Exception as e:
            self.logger.error(f"QRS检测算法失败: {str(e)}")
            return []
    
    def calculate_heart_rate_variability(self, window_size=120):
        """计算心率变异性指标
        
        Args:
            window_size (int): 用于计算的RR间期窗口大小
        
        Returns:
            dict: HRV指标结果
        """
        try:
            # 获取缓冲区中的RR间期数据
            rr_intervals = list(self.processed_data['rr_intervals'])
            
            # 如果数据不足，返回空结果
            if len(rr_intervals) < 5:  # 至少需要5个RR间期才能计算有意义的HRV
                return {
                    'success': False,
                    'message': 'RR间期数据不足',
                    'data': {}
                }
            
            # 取最近的window_size个RR间期（或全部，如果不足window_size个）
            rr_intervals = rr_intervals[-min(window_size, len(rr_intervals)):]
            
            # 时域指标
            mean_rr = np.mean(rr_intervals)  # 平均RR间期
            sdnn = np.std(rr_intervals)       # RR间期标准差
            
            # 计算相邻RR间期差的均方根（RMSSD）
            rmssd = np.sqrt(np.mean(np.square(np.diff(rr_intervals))))
            
            # 计算相邻RR间期差异超过50ms的比例（pNN50）
            nn50 = sum(abs(np.diff(rr_intervals)) > 50)
            pnn50 = (nn50 / (len(rr_intervals) - 1)) * 100 if len(rr_intervals) > 1 else 0
            
            hrv_data = {
                'mean_rr': float(mean_rr),
                'sdnn': float(sdnn),
                'rmssd': float(rmssd),
                'pnn50': float(pnn50),
                'nn50': int(nn50),
                'window_size': len(rr_intervals)
            }
            
            return {
                'success': True,
                'data': hrv_data,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"计算HRV失败: {str(e)}")
            return {'success': False, 'message': f'计算HRV失败: {str(e)}', 'data': {}}

# 初始化数据处理服务
data_processing_service = DataProcessingService()
