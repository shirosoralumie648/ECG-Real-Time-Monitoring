# analysis_service.py

import numpy as np
from scipy import signal
from ..data.database_manager import database_manager
from datetime import datetime

class ECGAnalysisService:
    """
    ECG分析服务类，负责ECG信号的高级分析
    """
    
    @staticmethod
    def detect_qrs_complexes(ecg_signal, sampling_rate=500):
        """
        检测QRS复合波
        
        Args:
            ecg_signal (list/array): ECG信号数据
            sampling_rate (int): 采样率
            
        Returns:
            dict: QRS检测结果
        """
        try:
            # 确保输入是numpy数组
            ecg_signal = np.array(ecg_signal)
            
            # 带通滤波 (5-15 Hz)
            low = 5.0 / (sampling_rate / 2)
            high = 15.0 / (sampling_rate / 2)
            b, a = signal.butter(3, [low, high], 'bandpass')
            filtered_ecg = signal.filtfilt(b, a, ecg_signal)
            
            # 微分
            diff_ecg = np.diff(filtered_ecg)
            
            # 平方
            squared_ecg = diff_ecg ** 2
            
            # 移动平均积分
            window_size = int(sampling_rate * 0.15)  # 150 ms
            integrated_ecg = np.convolve(squared_ecg, np.ones(window_size)/window_size, mode='same')
            
            # 自适应阈值
            threshold = 0.3 * np.max(integrated_ecg)
            
            # 峰值检测
            peaks, _ = signal.find_peaks(integrated_ecg, height=threshold, distance=int(sampling_rate * 0.2))
            
            # 计算RR间隔
            rr_intervals = np.diff(peaks) / sampling_rate * 1000  # 转换为毫秒
            
            # 心率计算（每分钟心跳次数）
            if len(rr_intervals) > 0:
                heart_rate = 60000 / np.mean(rr_intervals)
            else:
                heart_rate = 0
                
            return {
                'success': True,
                'qrs_locations': peaks.tolist(),
                'rr_intervals': rr_intervals.tolist(),
                'heart_rate': heart_rate,
                'qrs_count': len(peaks)
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'QRS检测失败: {str(e)}'
            }
    
    @staticmethod
    def analyze_heart_rate_variability(rr_intervals):
        """
        分析心率变异性
        
        Args:
            rr_intervals (list/array): RR间隔（毫秒）
            
        Returns:
            dict: 心率变异性分析结果
        """
        try:
            # 确保输入是numpy数组
            rr_intervals = np.array(rr_intervals)
            
            if len(rr_intervals) < 2:
                return {
                    'success': False,
                    'message': 'RR间隔数据不足'
                }
            
            # 时域分析
            sdnn = np.std(rr_intervals)  # RR间隔标准差
            rmssd = np.sqrt(np.mean(np.diff(rr_intervals) ** 2))  # 相邻RR间隔差的均方根
            nn50 = sum(abs(np.diff(rr_intervals)) > 50)  # 相邻RR间隔差>50ms的数量
            pnn50 = (nn50 / len(rr_intervals)) * 100  # nn50占比
            
            return {
                'success': True,
                'sdnn': sdnn,  # RR间隔标准差 (ms)
                'rmssd': rmssd,  # 相邻RR间隔差的均方根 (ms)
                'nn50': nn50,  # 相邻RR间隔差>50ms的数量
                'pnn50': pnn50  # 相邻RR间隔差>50ms的百分比
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'心率变异性分析失败: {str(e)}'
            }
    
    @staticmethod
    def detect_arrhythmia(rr_intervals, qrs_morphology=None):
        """
        心律失常检测
        
        Args:
            rr_intervals (list/array): RR间隔（毫秒）
            qrs_morphology (list/array, optional): QRS形态特征
            
        Returns:
            dict: 心律失常检测结果
        """
        try:
            # 确保输入是numpy数组
            rr_intervals = np.array(rr_intervals)
            
            if len(rr_intervals) < 3:
                return {
                    'success': False,
                    'message': 'RR间隔数据不足'
                }
            
            # 设置阈值
            bradycardia_threshold = 1000  # 心动过缓阈值 (>1000ms 或 <60bpm)
            tachycardia_threshold = 600   # 心动过速阈值 (<600ms 或 >100bpm)
            irregular_threshold = 0.2     # 不规则阈值 (相邻RR间隔变化>20%)
            
            # 分析RR间隔
            mean_rr = np.mean(rr_intervals)
            rr_diff_percent = np.abs(np.diff(rr_intervals) / rr_intervals[:-1])
            
            # 检测心动过缓/过速
            is_bradycardia = mean_rr > bradycardia_threshold
            is_tachycardia = mean_rr < tachycardia_threshold
            
            # 检测不规则心律
            is_irregular = np.any(rr_diff_percent > irregular_threshold)
            irregular_beats = np.sum(rr_diff_percent > irregular_threshold)
            
            # 分析结果
            arrhythmia_types = []
            if is_bradycardia:
                arrhythmia_types.append('心动过缓')
            if is_tachycardia:
                arrhythmia_types.append('心动过速')
            if is_irregular:
                arrhythmia_types.append('心律不齐')
                
            severity = 'none'  # 正常
            if len(arrhythmia_types) > 0:
                if irregular_beats > len(rr_intervals) * 0.3 or is_bradycardia and mean_rr > 1200 or is_tachycardia and mean_rr < 500:
                    severity = 'high'  # 高风险
                else:
                    severity = 'low'   # 低风险
            
            return {
                'success': True,
                'detected': len(arrhythmia_types) > 0,
                'arrhythmia_types': arrhythmia_types,
                'mean_rr': mean_rr,
                'irregular_beats': int(irregular_beats),
                'severity': severity
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'心律失常检测失败: {str(e)}'
            }
    
    @staticmethod
    def analyze_ecg_data(patient_id, ecg_data, timestamps, lead_index=0, sampling_rate=500):
        """
        综合分析ECG数据并存储结果
        
        Args:
            patient_id (str): 患者ID
            ecg_data (list): ECG数据 (多导联)
            timestamps (list): 时间戳
            lead_index (int): 要分析的导联索引
            sampling_rate (int): 采样率
            
        Returns:
            dict: 分析结果
        """
        try:
            # 选择指定导联的数据
            if lead_index < len(ecg_data):
                lead_data = ecg_data[lead_index]
            else:
                return {
                    'success': False,
                    'message': f'导联索引{lead_index}超出范围'
                }
            
            # 检测QRS复合波
            qrs_result = ECGAnalysisService.detect_qrs_complexes(lead_data, sampling_rate)
            if not qrs_result['success']:
                return qrs_result
                
            # 心率变异性分析
            hrv_result = ECGAnalysisService.analyze_heart_rate_variability(qrs_result['rr_intervals'])
            
            # 心律失常检测
            arrhythmia_result = ECGAnalysisService.detect_arrhythmia(qrs_result['rr_intervals'])
            
            # 组合分析结果
            analysis_result = {
                'patient_id': patient_id,
                'timestamp': datetime.now().isoformat(),
                'heart_rate': qrs_result['heart_rate'],
                'qrs_count': qrs_result['qrs_count'],
                'hrv_metrics': hrv_result if hrv_result['success'] else None,
                'arrhythmia': arrhythmia_result if arrhythmia_result['success'] else None,
                'lead_index': lead_index,
                'analysis_duration': len(lead_data) / sampling_rate  # 分析时长（秒）
            }
            
            # 存储分析结果到MongoDB
            database_manager.mongodb_db.ecg_analysis.insert_one(analysis_result)
            
            return {
                'success': True,
                'message': '分析完成',
                'result': analysis_result
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'ECG分析失败: {str(e)}'
            }

# 初始化分析服务
ecg_analysis_service = ECGAnalysisService()
