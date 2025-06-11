# data_acquisition_service.py

import time
import json
import logging
import threading
from datetime import datetime
from collections import deque
from bson import ObjectId

# 导入数据库管理器和设备服务
from ..data.database_manager import database_manager
from .device_service import device_service

class DataAcquisitionService:
    """数据采集服务类，负责从设备读取原始数据"""
    
    def __init__(self):
        self.sampling_rate = 250  # 默认采样率(Hz)
        self.collecting = False   # 是否正在采集数据
        self.current_session_id = None
        self.current_patient_id = None
        self.buffer_size = 5000  # 默认缓冲区大小（样本数)
        self.data_buffer = {}
        self.data_listeners = []
        self.acquisition_thread = None
        self.stop_thread = False
        self.logger = logging.getLogger('data_acquisition_service')
        
        # 注册为设备服务的数据监听器
        device_service.register_data_listener(self._on_device_data)
    
    def start_acquisition(self, patient_id=None, config=None):
        """开始数据采集
        
        Args:
            patient_id (str, optional): 患者ID
            config (dict, optional): 配置参数
        
        Returns:
            dict: 启动结果
        """
        if self.collecting:
            return {'success': False, 'message': '数据采集已在进行中'}
        
        # 检查设备连接状态
        connection_status = device_service.get_connection_status()
        if not connection_status['status']['connected']:
            return {'success': False, 'message': '没有连接的设备'}
        
        try:
            # 配置参数
            if config:
                if 'sampling_rate' in config:
                    self.sampling_rate = config['sampling_rate']
                if 'buffer_size' in config:
                    self.buffer_size = config['buffer_size']
            
            # 创建新的数据采集会话
            session_data = {
                'patient_id': patient_id,
                'device_type': connection_status['status']['connection_type'],
                'device_params': connection_status['status']['connection_params'],
                'sampling_rate': self.sampling_rate,
                'started_at': datetime.now(),
                'status': 'active',
                'config': config
            }
            
            result = database_manager.mongodb_db.data_sessions.insert_one(session_data)
            self.current_session_id = str(result.inserted_id)
            self.current_patient_id = patient_id
            
            # 初始化缓冲区
            self.data_buffer = {
                'timestamp': deque(maxlen=self.buffer_size),
                'ecg': deque(maxlen=self.buffer_size),
                'temperature': deque(maxlen=self.buffer_size),
                'respiration': deque(maxlen=self.buffer_size),
                'spo2': deque(maxlen=self.buffer_size),
                'blood_pressure': deque(maxlen=self.buffer_size)
            }
            
            # 启动采集线程
            self.stop_thread = False
            self.collecting = True
            self.acquisition_thread = threading.Thread(target=self._acquisition_loop)
            self.acquisition_thread.daemon = True
            self.acquisition_thread.start()
            
            return {
                'success': True,
                'message': '数据采集已启动',
                'session_id': self.current_session_id
            }
        except Exception as e:
            self.logger.error(f"启动数据采集失败: {str(e)}")
            return {'success': False, 'message': f'启动数据采集失败: {str(e)}'}

    def stop_acquisition(self):
        """停止数据采集
        
        Returns:
            dict: 停止结果
        """
        if not self.collecting:
            return {'success': False, 'message': '没有正在进行的数据采集'}
        
        try:
            # 停止采集线程
            self.stop_thread = True
            if self.acquisition_thread and self.acquisition_thread.is_alive():
                self.acquisition_thread.join(2.0)  # 等待线程结束，最多2秒
            
            # 更新会话状态
            if self.current_session_id:
                database_manager.mongodb_db.data_sessions.update_one(
                    {'_id': ObjectId(self.current_session_id)},
                    {'$set': {'status': 'completed', 'ended_at': datetime.now()}}
                )
            
            # 重置状态
            self.collecting = False
            session_id = self.current_session_id
            self.current_session_id = None
            self.current_patient_id = None
            
            return {
                'success': True,
                'message': '数据采集已停止',
                'session_id': session_id
            }
        except Exception as e:
            self.logger.error(f"停止数据采集失败: {str(e)}")
            return {'success': False, 'message': f'停止数据采集失败: {str(e)}'}
    
    def get_acquisition_status(self):
        """获取数据采集状态
        
        Returns:
            dict: 采集状态
        """
        status = {
            'collecting': self.collecting,
            'session_id': self.current_session_id,
            'patient_id': self.current_patient_id,
            'sampling_rate': self.sampling_rate,
            'buffer_size': self.buffer_size,
            'buffer_usage': {k: len(v) for k, v in self.data_buffer.items()} if self.data_buffer else {}
        }
        return {'success': True, 'status': status}
    
    def get_current_data(self, channel=None, samples=100):
        """获取当前数据
        
        Args:
            channel (str, optional): 需要获取的通道，如果为None，返回所有通道
            samples (int, optional): 需要获取的样本数
        
        Returns:
            dict: 数据结果
        """
        if not self.collecting or not self.data_buffer:
            return {'success': False, 'message': '没有可用的数据'}
        
        try:
            result = {}
            
            if channel and channel in self.data_buffer:
                # 获取指定通道的数据
                buffer = self.data_buffer[channel]
                data = list(buffer)[-samples:] if len(buffer) > 0 else []
                result[channel] = data
            else:
                # 获取所有通道的数据
                for ch, buffer in self.data_buffer.items():
                    data = list(buffer)[-samples:] if len(buffer) > 0 else []
                    result[ch] = data
            
            return {
                'success': True,
                'data': result,
                'timestamp': datetime.now().isoformat(),
                'samples': samples
            }
        except Exception as e:
            self.logger.error(f"获取数据失败: {str(e)}")
            return {'success': False, 'message': f'获取数据失败: {str(e)}'}
    
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
        """注销数据监听器
        
        Args:
            listener (function): 监听器函数
        
        Returns:
            bool: 是否注销成功
        """
        if listener in self.data_listeners:
            self.data_listeners.remove(listener)
            return True
        return False
    
    def _on_device_data(self, data, device_type, addr=None):
        """处理来自设备的数据
        
        Args:
            data: 设备数据
            device_type (str): 设备类型
            addr (tuple, optional): 设备地址，只有UDP连接时有效
        """
        if not self.collecting:
            return
        
        try:
            # 解析数据
            # 注意：根据实际设备数据格式进行处理
            # 这里假设数据是JSON格式
            
            parsed_data = None
            if device_type == 'serial':
                try:
                    # 尝试解析JSON
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    parsed_data = json.loads(data)
                except:
                    # 如果不是JSON，可能是原始字节流或CSV格式
                    # 这里可以实现更复杂的解析逻辑
                    if isinstance(data, bytes):
                        # 处理字节流数据
                        pass
                    elif isinstance(data, str):
                        # 处理字符串数据，可能是CSV格式
                        pass
            elif device_type == 'udp' or device_type == 'bluetooth':
                # UDP和蓝牙数据处理类似
                try:
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    parsed_data = json.loads(data)
                except:
                    # 非JSON格式处理
                    pass
            
            # 如果成功解析了数据
            if parsed_data:
                # 存储到缓冲区
                timestamp = datetime.now()
                self.data_buffer['timestamp'].append(timestamp)
                
                # 处理不同类型的生理数据
                if 'ecg' in parsed_data:
                    self.data_buffer['ecg'].append(parsed_data['ecg'])
                if 'temperature' in parsed_data:
                    self.data_buffer['temperature'].append(parsed_data['temperature'])
                if 'respiration' in parsed_data:
                    self.data_buffer['respiration'].append(parsed_data['respiration'])
                if 'spo2' in parsed_data:
                    self.data_buffer['spo2'].append(parsed_data['spo2'])
                if 'blood_pressure' in parsed_data:
                    self.data_buffer['blood_pressure'].append(parsed_data['blood_pressure'])
                
                # 定期存储到数据库
                # 这里可以实现数据持久化
                
                # 通知所有监听器
                for listener in self.data_listeners:
                    try:
                        listener(parsed_data, timestamp)
                    except Exception as e:
                        self.logger.error(f"数据监听器处理失败: {str(e)}")
        except Exception as e:
            self.logger.error(f"处理设备数据失败: {str(e)}")
    
    def _acquisition_loop(self):
        """数据采集线程主函数"""
        last_store_time = time.time()
        store_interval = 5  # 每5秒存储一次数据
        
        while not self.stop_thread and self.collecting:
            try:
                # 检查是否需要将数据存储到数据库
                current_time = time.time()
                if current_time - last_store_time >= store_interval:
                    self._store_data_batch()
                    last_store_time = current_time
                
                time.sleep(0.1)  # 避免CPU使用过高
            except Exception as e:
                self.logger.error(f"采集线程异常: {str(e)}")
                time.sleep(1)  # 异常时等待一段时间
    
    def _store_data_batch(self):
        """将一批数据存储到数据库"""
        if not self.collecting or not self.current_session_id:
            return
        
        try:
            # 将缓冲区数据转换为列表
            data_to_store = {}
            for channel, buffer in self.data_buffer.items():
                if len(buffer) > 0:
                    # 只存储最近添加的数据
                    data_to_store[channel] = list(buffer)[-1000:]  # 存储最近1000个样本
            
            if data_to_store and len(data_to_store) > 0:
                # 创建数据批次记录
                batch_data = {
                    'session_id': self.current_session_id,
                    'patient_id': self.current_patient_id,
                    'timestamp': datetime.now(),
                    'data': data_to_store
                }
                
                # 存储到MongoDB
                database_manager.mongodb_db.data_batches.insert_one(batch_data)
                
                # 存储到InfluxDB（时间序列数据库）
                if 'ecg' in data_to_store and 'timestamp' in data_to_store:
                    try:
                        # 将数据转换为InfluxDB时间序列格式
                        points = []
                        timestamps = data_to_store['timestamp']
                        ecg_data = data_to_store['ecg']
                        
                        for i in range(min(len(timestamps), len(ecg_data))):
                            points.append({
                                'measurement': 'ecg_data',
                                'tags': {
                                    'session_id': self.current_session_id,
                                    'patient_id': str(self.current_patient_id) if self.current_patient_id else 'unknown'
                                },
                                'time': timestamps[i].isoformat(),
                                'fields': {
                                    'value': float(ecg_data[i])
                                }
                            })
                        
                        # 写入InfluxDB
                        database_manager.write_points_to_influxdb(points)
                    except Exception as e:
                        self.logger.error(f"存储到InfluxDB失败: {str(e)}")
        except Exception as e:
            self.logger.error(f"存储数据批次失败: {str(e)}")
