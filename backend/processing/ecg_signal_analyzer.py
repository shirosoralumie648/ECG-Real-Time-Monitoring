#ecg_signal_analyzer.py

import neurokit2 as nk
from matplotlib import pyplot as plt


#定义ECGSignalAnalyzer类，提供ECG信号特征提取和分析的功能

class ECGSignalAnalyzer:
    def extract_features(self, ecg_signal, sampling_rate=500):
        signals, info = nk.ecg_process(ecg_signal, sampling_rate=sampling_rate)
        return signals, info

    def analyze_hrv(self, ecg_signal, sampling_rate=500):
        peaks, info = nk.ecg_peaks(ecg_signal, sampling_rate=sampling_rate)
        hrv_metrics = nk.hrv(peaks, sampling_rate=sampling_rate, show=True)
        return hrv_metrics

    def analyze_edr(self, ecg_signal, sampling_rate=500):
        rpeaks, info = nk.ecg_peaks(ecg_signal, sampling_rate=sampling_rate)
        ecg_rate = nk.ecg_rate(rpeaks, sampling_rate, desired_length=len(ecg_signal))
        edr = nk.ecg_rsp(ecg_rate, sampling_rate)

        return edr

    def calculate_clinical_indices(self, ecg_signal, sampling_rate=400):
        clinical_indices = {}
        # TODO: 实现ST段改变、QT离散度等分析
        return clinical_indices

    def plot_hrv(self, hrv_metrics):
        # 假设 hrv_metrics 是一个包含 HRV 指标的字典
        try:
            sdnn = float(hrv_metrics['HRV_SDNN'].iloc[0]) if 'HRV_SDNN' in hrv_metrics else None
            rmssd = float(hrv_metrics['HRV_RMSSD'].iloc[0]) if 'HRV_RMSSD' in hrv_metrics else None
        except ValueError as e:
            print(f"Error converting HRV values: {e}")
            return

        # 如果指标都存在，绘制图表
        if sdnn is not None and rmssd is not None:
            plt.figure(figsize=(10, 6))
            plt.bar(['HRV_SDNN', 'HRV_RMSSD'], [sdnn, rmssd], color=['blue', 'orange'])
            plt.title('HRV Metrics')
            plt.xlabel('Metric')
            plt.ylabel('Value (ms)')
            plt.show()
        else:
            plt.figure(figsize=(10, 6))
            plt.text(0.5, 0.5, 'Required HRV metrics not available\nPlease check the data input',
                     horizontalalignment='center',
                     verticalalignment='center',
                     transform=plt.gca().transAxes)
            plt.title('HRV Metrics')
            plt.xlabel('Metric')
            plt.ylabel('Value (ms)')
            plt.show()