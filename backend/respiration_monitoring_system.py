# respiration_monitoring_system.py

import time
import numpy as np
from .respiration_udp_receiver import RespirationUDPReceiver
from .respiration_processor import RespirationProcessor
from .data_storage import DataStorage

class RespirationMonitoringSystem:
    """呼吸波形数据监测系统"""
    
    def __init__(self, socketio, host='127.0.0.1', port=1347, sampling_rate=100):
        """初始化呼吸波形数据监测系统
        
        Args:
            socketio: Flask-SocketIOu5b9eu4f8b
            host: UDPu670du52a1u5668u4e3bu673au5730u5740
            port: UDPu670du52a1u5668u7aefu53e3
            sampling_rate: u547cu5438u6ce2u5f62u91c7u6837u7387
        """
        self.socketio = socketio
        self.udp_receiver = RespirationUDPReceiver(host, port)
        self.udp_receiver.register_callback(self.handle_new_data)
        self.processor = RespirationProcessor(sampling_rate=sampling_rate)
        
        # u521du59cbu5316u6570u636eu5b58u50a8
        self.data_storage = DataStorage()
        self.storage_key = 'respiration'
        
        # 初始化数据累积
        self.accumulated_data = []  # u5b58u50a8 (timestamp, value) u5bf9
        self.sample_counter = 0
        self.max_samples = 500  # u6bcfu6b21u53d1u9001u7684u6570u636eu70b9u6570u91cf
        self.start_timestamp = None
        self.end_timestamp = None
    
    def start(self):
        """u542fu52a8u547cu5438u76d1u6d4bu7cfbu7edf"""
        print("RespirationMonitoringSystem starting...")
        self.start_timestamp = time.time()
        # u91cdu7f6eu6570u636e
        self.accumulated_data = []
        self.sample_counter = 0
        # u542fu52a8UDPu63a5u6536u5668
        success = self.udp_receiver.start()
        if success:
            print("RespirationMonitoringSystem started successfully")
            return True
        else:
            print("Failed to start RespirationMonitoringSystem")
            return False
    
    def stop(self):
        """u505cu6b62u547cu5438u76d1u6d4bu7cfbu7edf"""
        print("RespirationMonitoringSystem stopping...")
        self.end_timestamp = time.time()
        # u505cu6b62UDPu63a5u6536u5668
        self.udp_receiver.stop()
        
        # u5982u679cu6709u6570u636euff0cu4fddu5b58u5230u6587u4ef6
        if len(self.accumulated_data) > 0:
            times, values = zip(*self.accumulated_data)
            np_values = np.array(values)
            # u4fddu5b58u6570u636e
            self.data_storage.save_data('respiration', np_values, 
                                       self.start_timestamp, 
                                       self.end_timestamp)
        
        print("RespirationMonitoringSystem stopped")
        return True
    
    def handle_new_data(self, values, timestamp):
        """u5904u7406u65b0u63a5u6536u5230u7684u547cu5438u6570u636e
        
        Args:
            values: u89e3u6790u540eu7684u6d6eu70b9u6570u503cu5217u8868
            timestamp: u6570u636eu63a5u6536u65f6u95f4u6233
        """
        # u5982u679cu6709u591au4e2au901au9053uff0cu6211u4eecu53eau53d6u7b2cu4e00u4e2au4f5cu4e3au547cu5438u4fe1u53f7
        # u8fd9u91ccu53efu4ee5u6839u636eu5b9eu9645u60c5u51b5u4feeu6539
        if len(values) > 0:
            respiration_value = values[0]
            
            # u5c06u65b0u6570u636eu6dfbu52a0u5230u7d2fu79efu6570u636eu4e2d
            self.accumulated_data.append((timestamp, respiration_value))
            self.sample_counter += 1
            
            # u5f53u79efu7d2fu4e86u8db3u591fu7684u6570u636eu70b9u540eu8fdbu884cu5904u7406u548cu53d1u9001
            if self.sample_counter >= self.max_samples:
                self.process_and_send_data()
                self.sample_counter = 0
    
    def process_and_send_data(self):
        """u5904u7406u5e76u53d1u9001u6570u636eu5230u524du7aef"""
        if len(self.accumulated_data) >= 20:  # u786eu4fddu6709u8db3u591fu7684u6570u636eu8fdbu884cu5904u7406
            # u83b7u53d6u6700u65b0u7684 max_samples u4e2au6570u636eu70b9
            recent_data = self.accumulated_data[-self.max_samples:]
            times, values = zip(*recent_data)
            
            # u5c06u65f6u95f4u548cu503cu8f6cu6362u4e3au5217u8868
            times_list = list(times)
            values_list = list(values)
            
            # u9884u5904u7406u6570u636e
            try:
                cleaned_signal = self.processor.preprocess(values_list)
                processed_values = cleaned_signal.tolist()
            except Exception as e:
                print(f"Error preprocessing respiration data: {e}")
                processed_values = values_list
            
            # u8ba1u7b97u547cu5438u7387uff08u5982u679cu6709u8db3u591fu6570u636euff09
            try:
                features = self.processor.get_respiration_features(np.array(values_list))
                respiration_rate = features.get('respiration_rate', None)
            except Exception as e:
                print(f"Error calculating respiration rate: {e}")
                respiration_rate = None
            
            # u53d1u9001u6570u636eu5230u524du7aef
            self.socketio.emit('respiration_data', {
                'values': processed_values,
                'time_stamps': times_list,
                'respiration_rate': respiration_rate
            })
            print(f"Respiration data emitted to frontend with {len(processed_values)} samples")
            
            # u4fddu6301u7d2fu8ba1u6570u636eu7684u957fu5ea6uff0cu9632u6b62u5185u5b58u5360u7528u8fc7u5927
            max_length = self.max_samples * 10  # u4fddu7559u6700u65b0u7684u6570u636e
            if len(self.accumulated_data) > max_length:
                self.accumulated_data = self.accumulated_data[-max_length:]
    
    def analyze_respiration(self, data=None):
        """u5206u6790u547cu5438u6570u636eu5e76u8fd4u56deu7ed3u679c
        
        Args:
            data: u8981u5206u6790u7684u547cu5438u6570u636euff0cu5982u679cu4e3aNoneu5219u4f7fu7528u5f53u524du7d2fu79efu7684u6570u636e
            
        Returns:
            dict: u5206u6790u7ed3u679c
        """
        if data is None:
            # u4f7fu7528u5f53u524du7d2fu79efu7684u6570u636e
            if len(self.accumulated_data) < 100:
                return {"error": "u6570u636eu4e0du8db3uff0cu65e0u6cd5u5206u6790"}
            
            _, values = zip(*self.accumulated_data[-500:])  # u53d6u6700u8fd1500u4e2au6570u636eu70b9
            data = np.array(values)
        
        # u7528u5904u7406u5668u5206u6790u547cu5438u6570u636e
        try:
            features = self.processor.get_respiration_features(data)
            return features
        except Exception as e:
            print(f"Error analyzing respiration data: {e}")
            return {"error": str(e)}
    
    def get_latest_data(self, n_samples=500):
        """u83b7u53d6u6700u65b0u7684u547cu5438u6570u636e
        
        Args:
            n_samples: u8981u8fd4u56deu7684u6570u636eu70b9u6570u91cf
            
        Returns:
            tuple: (times, values) u5143u7ec4
        """
        if len(self.accumulated_data) == 0:
            return [], []
        
        # u83b7u53d6u6700u65b0u7684n_samplesu4e2au6570u636eu70b9
        recent_data = self.accumulated_data[-n_samples:]
        times, values = zip(*recent_data)
        
        return list(times), list(values)
