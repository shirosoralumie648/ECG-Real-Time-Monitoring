#ecg_data_processor.py

import neurokit2 as nk
import numpy as np
from scipy import interpolate
#定义ECGDataProcessor类，负责计算12导联、信号预处理等功能

class ECGDataProcessor:
    def compute_12_leads(self, leads):
        I, II, V1, V2, V3, V4, V5, V6 = leads
        III = II - I
        aVR = -(I + II) / 2
        aVL = (I - II) / 2
        aVF = (II + III) / 2
        return [I, II, III, aVR, aVL, aVF, V1, V2, V3, V4, V5, V6]
        
    def advanced_interpolate(self, times, values, method='cubic'):
        """
        改进的高级插值算法，支持线性、三次样条和Akima插值
        增强了错误处理和输入验证
        
        参数:
            times: 时间点列表
            values: 对应的数值列表
            method: 插值方法，'linear'、'cubic'或'akima'
        
        返回:
            new_times: 新的均匀分布的时间点
            new_values: 对应的插值后的数值
        """
        # 输入验证
        if times is None or values is None:
            print("插值输入为空")
            return [], []
            
        # 确保输入是列表或数组
        try:
            times = list(times)
            values = list(values)
        except Exception as e:
            print(f"无法转换输入为列表: {e}")
            return [], []
        
        # 检查输入长度
        if len(times) != len(values):
            print(f"时间和值的长度不匹配: {len(times)} vs {len(values)}")
            return times, values
            
        # 检查最小点数
        if len(times) < 4:  # 需要至少4个点进行三次样条插值
            # 如果点数不足，回退到线性插值
            return self.linear_interpolate(times, values)
            
        # 检查时间是否单调递增
        if not all(times[i] < times[i+1] for i in range(len(times)-1)):
            print("时间序列不是单调递增的")
            # 尝试排序
            try:
                sorted_indices = np.argsort(times)
                times = [times[i] for i in sorted_indices]
                values = [values[i] for i in sorted_indices]
            except Exception as e:
                print(f"无法排序时间序列: {e}")
                return self.linear_interpolate(times, values)
            
        # 检查时间间隔
        try:
            intervals = [times[i+1] - times[i] for i in range(len(times)-1)]
            if not intervals:
                return times, values
                
            # 使用中位数而不是平均值，更鲁棒
            median_interval = sorted(intervals)[len(intervals)//2]
            avg_interval = sum(intervals) / len(intervals)
            
            # 使用更安全的间隔计算
            safe_interval = max(median_interval, avg_interval / 10)
            
            # 防止时间间隔为零
            if safe_interval <= 0:
                print("时间间隔为零或负值")
                return times, values
                
            # 防止创建过多点
            max_points = min(1000, len(times) * 5)  # 限制最大点数
            
            # 创建新的均匀时间点
            num_points = min(max_points, int((times[-1] - times[0]) / safe_interval) + 1)
            num_points = max(num_points, len(times))  # 确保至少与原始点数相同
            
            # 创建新的时间点
            new_times = np.linspace(times[0], times[-1], num_points)
        except Exception as e:
            print(f"计算插值参数时出错: {e}")
            return self.linear_interpolate(times, values)
        
        # 执行插值
        try:
            if method == 'linear' or len(times) < 5:
                # 线性插值 - 最简单、最稳定的方法
                new_values = np.interp(new_times, times, values)
            elif method == 'akima' and len(times) >= 5:  # Akima需要至少5个点
                # 尝试Akima插值，对异常值更鲁棒
                try:
                    akima_interp = interpolate.Akima1DInterpolator(times, values)
                    new_values = akima_interp(new_times)
                except Exception as e:
                    print(f"Akima插值失败: {e}，回退到线性插值")
                    new_values = np.interp(new_times, times, values)
            else:
                # 尝试三次样条插值
                try:
                    # 使用更安全的平滑参数
                    s = len(times) / 50.0  # 动态调整平滑参数
                    tck = interpolate.splrep(times, values, s=s)
                    new_values = interpolate.splev(new_times, tck, der=0)
                except Exception as e:
                    print(f"三次样条插值失败: {e}，回退到线性插值")
                    new_values = np.interp(new_times, times, values)
        except Exception as e:
            print(f"高级插值失败: {e}，回退到线性插值")
            # 最后的备选方案：返回原始数据
            return times, values
            
        return new_times, new_values
    
    def linear_interpolate(self, times, values):
        """简单的线性插值"""
        if len(times) < 2:
            return times, values
            
        # 检测时间间隔
        intervals = [times[i+1] - times[i] for i in range(len(times)-1)]
        if not intervals:
            return times, values
            
        avg_interval = sum(intervals) / len(intervals)
        
        # 创建新的均匀时间点
        new_times = np.linspace(times[0], times[-1], int((times[-1]-times[0])/avg_interval) + 1)
        
        # 线性插值
        new_values = np.interp(new_times, times, values)
        
        return new_times, new_values

    def clean_signal(self, ecg_signal, sampling_rate=500):
        """
        简化的信号清洗算法，避免使用neurokit2的滤波器
        使用简单的滤波方法，避免filter_length警告
        
        参数:
            ecg_signal: ECG信号数据
            sampling_rate: 采样率，默认500Hz
        
        返回:
            cleaned: 清洗后的信号
        """
        # 如果数据长度过短，直接返回原始信号
        if len(ecg_signal) < 20:
            return ecg_signal
        
        # 将列表转换为numpy数组以便于处理
        if not isinstance(ecg_signal, np.ndarray):
            ecg_signal = np.array(ecg_signal)
            
        try:
            # 第1步: 使用简单的移动平均滤波去除高频噪声
            window_size = min(5, len(ecg_signal) // 10)  # 自适应窗口大小
            if window_size < 2:
                window_size = 2  # 确保至少为2
                
            # 简单的移动平均滤波
            filtered = np.convolve(ecg_signal, np.ones(window_size)/window_size, mode='same')
            
            # 第2步: 去除基线漫游 - 使用简单的差分
            if len(filtered) > 20:
                # 计算信号的中位数
                median_val = np.median(filtered)
                # 去除基线 - 减去中位数
                detrended = filtered - median_val
            else:
                detrended = filtered
            
            # 第3步: 异常值处理 - 使用中位数绝对偏差(MAD)
            if len(detrended) > 20:
                # 计算MAD
                mad = np.median(np.abs(detrended - np.median(detrended)))
                # 定义阈值
                threshold = 5.0 * mad  # 5倍中位数绝对偏差
                # 限制异常值
                cleaned = np.clip(detrended, -threshold, threshold)
            else:
                cleaned = detrended
                
            # 第4步: 如果数据足够长，再次使用移动平均平滑信号
            if len(cleaned) > 10:
                window_size = min(3, len(cleaned) // 20)  # 更小的窗口大小保留更多细节
                if window_size >= 2:
                    final_smoothed = np.convolve(cleaned, np.ones(window_size)/window_size, mode='same')
                    return final_smoothed
            
            return cleaned
        except Exception as e:
            print(f"简化的信号清洗遇到错误: {e}")
            # 出现异常时返回原始信号
            return ecg_signal

    def interpolate_signal(self, times, values, method='cubic'):
        """
        插值信号方法，作为advanced_interpolate的别名
        为了与ecg_monitoring_system.py中的调用兼容
        
        参数:
            times: 时间点列表
            values: 对应的数值列表
            method: 插值方法，'linear'、'cubic'或'akima'
        
        返回:
            new_times: 新的均匀分布的时间点
            new_values: 对应的插值后的数值
        """
        return self.advanced_interpolate(times, values, method)
    
    def preprocessing(self, ecg_signal, sampling_rate=500):
        """
        简化的信号预处理方法，避免使用neurokit2的滤波器
        使用简单的滤波方法，避免filter_length警告
        
        参数:
            ecg_signal: ECG信号数据
            sampling_rate: 采样率，默认500Hz
            
        返回:
            cleaned_signal: 预处理后的信号
        """
        # 检查输入
        if ecg_signal is None or len(ecg_signal) == 0:
            print("预处理输入为空")
            return []
            
        # 将列表转换为numpy数组以便于处理
        if not isinstance(ecg_signal, np.ndarray):
            try:
                ecg_signal = np.array(ecg_signal)
            except Exception as e:
                print(f"无法转换信号为numpy数组: {e}")
                return ecg_signal
        
        # 使用简化的清洗算法
        cleaned_signal = self.clean_signal(ecg_signal, sampling_rate)
        
        # 对于较短的信号，直接返回清洗结果
        if len(ecg_signal) < 100:
            return cleaned_signal
        
        # 对于中等长度的信号，尝试额外的平滑处理
        try:
            # 使用自适应窗口大小的移动平均进行额外平滑
            window_size = min(5, len(cleaned_signal) // 50)
            if window_size >= 3:
                smoothed = np.convolve(cleaned_signal, np.ones(window_size)/window_size, mode='same')
                return smoothed
        except Exception as e:
            print(f"额外平滑处理失败: {e}")
            pass
                
        return cleaned_signal
