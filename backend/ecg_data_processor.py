#ecg_data_processor.py

import neurokit2 as nk
#定义ECGDataProcessor类，负责计算12导联、信号预处理等功能

class ECGDataProcessor:
    def compute_12_leads(self, leads):
        I, II, V1, V2, V3, V4, V5, V6 = leads
        III = II - I
        aVR = -(I + II) / 2
        aVL = (I - II) / 2
        aVF = (II + III) / 2
        return [I, II, III, aVR, aVL, aVF, V1, V2, V3, V4, V5, V6]

    def clean_signal(self, ecg_signal, sampling_rate=500):
        #cleaned = nk.ecg_clean(ecg_signal, sampling_rate=sampling_rate=320)
        filter1 = nk.signal_filter(ecg_signal, sampling_rate, highcut=80, method='fir', show=False)
        #filter2 = nk.signal_filter(filter1, sampling_rate, lowcut=0.5, method='fir', show=False)
        filter3 = nk.signal_filter(filter1, sampling_rate, method='powerline', powerline=50, show=False)
        cleaned = nk.signal_detrend(filter3, order=0)
        return cleaned

    def preprocessing(self, ecg_signal, sampling_rate=500):
        # 信号预处理
        cleaned_signal = nk.ecg_clean(ecg_signal, sampling_rate)
        return cleaned_signal
