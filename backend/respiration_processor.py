# respiration_processor.py

import numpy as np
import scipy.signal as sig
import neurokit2 as nk

class RespirationProcessor:
    """呼吸波形数据处理类"""
    
    def __init__(self, sampling_rate=100):
        """初始化呼吸波形数据处理类
        
        Args:
            sampling_rate: 采样率 (Hz)
        """
        self.sampling_rate = sampling_rate
    
    def preprocess(self, signal):
        """对呼吸波形数据进行预处理
        
        Args:
            signal: 原始呼吸波形数据
            
        Returns:
            ndarray: 预处理后的呼吸波形数据
        """
        # 将列表转换为NumPy数组
        if isinstance(signal, list):
            signal = np.array(signal)
            
        # 去除趋势
        signal = sig.detrend(signal)
        
        # 滤波 0.05-0.8 Hz (呼吸信号频率范围)
        filtered = nk.signal_filter(
            signal, 
            lowcut=0.05, 
            highcut=0.8, 
            sampling_rate=self.sampling_rate, 
            order=3
        )
        
        return filtered
    
    def find_peaks(self, signal):
        """查找呼吸波形数据的呼吸峰值
        
        Args:
            signal: 预处理后的呼吸波形数据
            
        Returns:
            tuple: (peaks_indices, peaks_info)
        """
        # 使用neurokit2进行呼吸峰值检测
        try:
            peaks, info = nk.rsp_peaks(signal, sampling_rate=self.sampling_rate)
            return peaks, info
        except Exception as e:
            print(f"Error in finding respiration peaks: {e}")
            # 使用scipy进行呼吸峰值检测
            peaks, _ = sig.find_peaks(signal, height=0, distance=self.sampling_rate/2)
            return peaks, {"RSP_Peaks": peaks}
    
    def calculate_rate(self, signal=None, peaks=None):
        """计算呼吸率
        
        Args:
            signal: 预处理后的呼吸波形数据
            peaks: 已检测到的呼吸峰值索引
            
        Returns:
            float: 呼吸率 (呼吸次数/分钟)
        """
        if peaks is None and signal is not None:
            peaks, _ = self.find_peaks(signal)
        
        if peaks is not None and len(peaks) > 1:
            # 计算相邻呼吸峰值之间的间隔时间
            intervals = np.diff(peaks) / self.sampling_rate  # 转换为秒
            # 计算呼吸率 (呼吸次数/分钟)
            rate = 60 / np.mean(intervals)  
            return rate
        return None
    
    def analyze_variability(self, signal=None, peaks=None):
        """分析呼吸波形数据的呼吸变异度
        
        Args:
            signal: 预处理后的呼吸波形数据
            peaks: 已检测到的呼吸峰值索引
            
        Returns:
            dict: 呼吸变异度分析结果
        """
        if peaks is None and signal is not None:
            peaks, _ = self.find_peaks(signal)
        
        if peaks is not None and len(peaks) > 2:
            # 计算相邻呼吸峰值之间的间隔时间
            intervals = np.diff(peaks) / self.sampling_rate  # 转换为秒
            
            # 计算呼吸率 (呼吸次数/分钟)
            mean_interval = np.mean(intervals)
            std_interval = np.std(intervals)
            cv = (std_interval / mean_interval) * 100  # 变异系数
            
            # 计算呼吸变异度 (RMSSD)
            rmssd = np.sqrt(np.mean(np.square(np.diff(intervals))))  # RMSSD
            
            return {
                "mean_interval": mean_interval,
                "std_interval": std_interval,
                "CV": cv,
                "RMSSD": rmssd,
                "rate": 60 / mean_interval
            }
        return None
    
    def detect_apnea(self, signal, threshold_seconds=10):
        """u7b80u5355u7684u547cu5438u6682u505cu68c0u6d4b
        
        Args:
            signal: 预处理后的呼吸波形数据
            threshold_seconds: 检测呼吸暂停的阈值时间 (秒)
            
        Returns:
            list: 检测到的呼吸暂停事件列表
        """
        peaks, _ = self.find_peaks(signal)
        
        apnea_events = []
        if len(peaks) > 1:
            # 计算相邻呼吸峰值之间的间隔时间
            intervals = np.diff(peaks) / self.sampling_rate
            
            # 检测呼吸暂停事件
            for i, interval in enumerate(intervals):
                if interval > threshold_seconds:
                    start_idx = peaks[i]
                    end_idx = peaks[i + 1]
                    duration = interval
                    apnea_events.append({
                        "start_index": start_idx,
                        "end_index": end_idx,
                        "duration": duration,
                        "start_time": start_idx / self.sampling_rate,
                        "end_time": end_idx / self.sampling_rate
                    })
        
        return apnea_events
    
    def get_respiration_features(self, signal):
        """获取呼吸波形数据的特征
        
        Args:
            signal: 预处理后的呼吸波形数据
            
        Returns:
            dict: 呼吸波形数据的特征
        """
        # 预处理呼吸波形数据
        clean_signal = self.preprocess(signal)
        
        # 检测呼吸峰值
        peaks, peaks_info = self.find_peaks(clean_signal)
        
        # 分析呼吸变异度
        variability = self.analyze_variability(peaks=peaks)
        
        # 检测呼吸暂停事件
        apnea_events = self.detect_apnea(clean_signal)
        
        # 计算呼吸率
        rate = variability["rate"] if variability else None
        
        # 计算呼吸变异度
        try:
            freqs, psd = sig.welch(clean_signal, fs=self.sampling_rate, nperseg=len(clean_signal)//4)
            dominant_freq = freqs[np.argmax(psd)]
            power_low = np.trapz(psd[(freqs >= 0.05) & (freqs <= 0.15)])
            power_high = np.trapz(psd[(freqs >= 0.15) & (freqs <= 0.4)])
        except Exception as e:
            print(f"Error in frequency domain analysis: {e}")
            dominant_freq = None
            power_low = None
            power_high = None
        
        return {
            "preprocessed_signal": clean_signal,
            "peaks": peaks,
            "peaks_info": peaks_info,
            "respiration_rate": rate,
            "variability": variability,
            "apnea_events": apnea_events,
            "dominant_frequency": dominant_freq,
            "power_low_freq": power_low,
            "power_high_freq": power_high
        }
