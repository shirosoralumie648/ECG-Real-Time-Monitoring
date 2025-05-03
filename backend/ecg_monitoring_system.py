# ecg_monitoring_system.py

import time
from .ecg_data_processor import ECGDataProcessor
from .serial_reader import SerialPortReader
from .data_storage import DataStorage  # 导入DataStorage
import numpy as np  # 导入 NumPy

class ECGMonitoringSystem:
    def __init__(self, socketio):
        self.socketio = socketio
        self.serial_reader = SerialPortReader()
        self.serial_reader.register_callback(self.handle_new_data)
        self.data_processor = ECGDataProcessor()
        self.data_storage = DataStorage()  # 实例化DataStorage
        self.accumulated_data = {i: [] for i in range(12)}  # 存储12个导联的数据，包含 (timestamp, value)
        self.sample_counter = 0  # 数据计数器
        self.max_samples = 500   # 每次发送的数据点数量
        self.start_timestamp = None
        self.end_timestamp = None

    def start(self):
        print("ECGMonitoringSystem started")
        self.start_timestamp = time.time()
        self.data_storage.reset_data() # 重置数据存储
        self.serial_reader.open()

    def stop(self):
        print("ECGMonitoringSystem stopped")
        self.end_timestamp = time.time() # 获取结束时间戳
        self.serial_reader.close() # 关闭串口
        self.data_storage.save_all_leads(self.start_timestamp, self.end_timestamp) # 保存数据

    def handle_new_data(self, values, timestamp):
        # 使用传递过来的时间戳而不是再次获取
        current_time = timestamp

        leads_12 = self.data_processor.compute_12_leads(values)
        self.data_storage.save_data_point(current_time, leads_12)

        for i in range(12):
            self.accumulated_data[i].append((current_time, leads_12[i]))
        self.sample_counter += 1

        if self.sample_counter >= self.max_samples:
            self.process_and_send_data()
            self.sample_counter = 0

    def process_and_send_data(self):
        # 处理累积的数据
        processed_signals = []
        time_stamps = []

        for i in range(12):
            # 获取最近的 max_samples 个数据点和时间戳
            data = self.accumulated_data[i][-self.max_samples:]  # 形如 [(timestamp, value), ...]
            if len(data) >= 18:
                # 分离时间戳和数据值
                times, values = zip(*data)
                times = list(times)
                values = list(values)

                # 对数据进行清洗
                cleaned_signal = self.data_processor.clean_signal(values)
                processed_signals.append(cleaned_signal.tolist())

                # 仅在第一次迭代时获取时间戳
                if i == 0:
                    time_stamps = times
            else:
                # 数据长度不足，直接使用原始数据
                times, values = zip(*data)
                processed_signals.append(values)
                if i == 0:
                    time_stamps = times

        # 将处理后的数据发送到前端，包含时间戳和这批数据
        self.socketio.emit('ecg_data', {
            'leads': processed_signals,  # 12个导联的列表，每个导联是这批数据的列表
            'time_stamps': time_stamps  # 这批数据的时间戳列表
        })
        print(f"Data emitted to frontend with {self.max_samples} samples")

        # 保持累计数据的长度，防止内存占用过大
        max_length = self.max_samples * 10  # 保留最近的数据
        for i in range(12):
            if len(self.accumulated_data[i]) > max_length:
                self.accumulated_data[i] = self.accumulated_data[i][-max_length:]
