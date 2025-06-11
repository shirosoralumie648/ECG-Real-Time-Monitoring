# device_service.py

import serial
import serial.tools.list_ports
import socket
import time
import threading
import logging
import json
from bson import ObjectId
from datetime import datetime

# 导入数据库管理器
from ..data.database_manager import database_manager

class DeviceService:
    """设备连接服务类，负责管理串口、UDP、蓝牙等数据源连接"""
    
    def __init__(self):
        self.connected = False
        self.connection_type = None
        self.connection_params = {}
        self.serial_port = None
        self.udp_socket = None
        self.bluetooth_socket = None
        self.stop_thread = False
        self.data_thread = None
        self.data_listeners = []
        self.logger = logging.getLogger('device_service')
    
    def get_available_serial_ports(self):
        """获取可用的串口列表
        
        Returns:
            list: 串口列表
        """
        ports = []
        try:
            available_ports = list(serial.tools.list_ports.comports())
            for port in available_ports:
                ports.append({
                    'port': port.device,
                    'description': port.description,
                    'hwid': port.hwid
                })
            return {'success': True, 'ports': ports}
        except Exception as e:
            self.logger.error(f"获取串口列表失败: {str(e)}")
            return {'success': False, 'message': f'获取串口列表失败: {str(e)}'}
    
    def connect_serial(self, port, baudrate=921600, timeout=1):
        """连接串口设备
        
        Args:
            port (str): 串口名称
            baudrate (int, optional): 波特率
            timeout (int, optional): 超时时间
        
        Returns:
            dict: 连接结果
        """
        if self.connected:
            return {'success': False, 'message': '已有设备连接，请先断开'}
        
        try:
            self.serial_port = serial.Serial(port, baudrate, timeout=timeout)
            self.connected = True
            self.connection_type = 'serial'
            self.connection_params = {
                'port': port,
                'baudrate': baudrate,
                'timeout': timeout
            }
            
            # 启动数据读取线程
            self.stop_thread = False
            self.data_thread = threading.Thread(target=self._read_serial_data)
            self.data_thread.daemon = True
            self.data_thread.start()
            
            # 记录设备连接
            device_info = {
                'device_type': 'serial',
                'port': port,
                'baudrate': baudrate,
                'connected_at': datetime.now(),
                'status': 'connected'
            }
            database_manager.mongodb_db.device_connections.insert_one(device_info)
            
            return {
                'success': True,
                'message': f'串口连接成功: {port}, {baudrate}bps',
                'connection_id': self.connection_type
            }
        except Exception as e:
            self.logger.error(f"串口连接失败: {str(e)}")
            return {'success': False, 'message': f'串口连接失败: {str(e)}'}
    
    def connect_udp(self, host='0.0.0.0', port=8888):
        """连接UDP设备
        
        Args:
            host (str, optional): 主机地址
            port (int, optional): 端口号
        
        Returns:
            dict: 连接结果
        """
        if self.connected:
            return {'success': False, 'message': '已有设备连接，请先断开'}
        
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind((host, port))
            self.connected = True
            self.connection_type = 'udp'
            self.connection_params = {
                'host': host,
                'port': port
            }
            
            # 启动数据读取线程
            self.stop_thread = False
            self.data_thread = threading.Thread(target=self._read_udp_data)
            self.data_thread.daemon = True
            self.data_thread.start()
            
            # 记录设备连接
            device_info = {
                'device_type': 'udp',
                'host': host,
                'port': port,
                'connected_at': datetime.now(),
                'status': 'connected'
            }
            database_manager.mongodb_db.device_connections.insert_one(device_info)
            
            return {
                'success': True,
                'message': f'UDP连接成功: {host}:{port}',
                'connection_id': self.connection_type
            }
        except Exception as e:
            self.logger.error(f"UDP连接失败: {str(e)}")
            return {'success': False, 'message': f'UDP连接失败: {str(e)}'}
    
    def connect_bluetooth(self, device_address):
        """连接蓝牙设备
        
        Args:
            device_address (str): 蓝牙设备地址
        
        Returns:
            dict: 连接结果
        """
        if self.connected:
            return {'success': False, 'message': '已有设备连接，请先断开'}
        
        try:
            # 注意：这里需要根据具体的蓝牙库实现
            # 例如使用PyBluez或其他蓝牙库
            # 这里只是一个示例框架
            self.bluetooth_socket = None  # 替换为实际的蓝牙连接代码
            self.connected = True
            self.connection_type = 'bluetooth'
            self.connection_params = {
                'device_address': device_address
            }
            
            # 启动数据读取线程
            self.stop_thread = False
            self.data_thread = threading.Thread(target=self._read_bluetooth_data)
            self.data_thread.daemon = True
            self.data_thread.start()
            
            # 记录设备连接
            device_info = {
                'device_type': 'bluetooth',
                'device_address': device_address,
                'connected_at': datetime.now(),
                'status': 'connected'
            }
            database_manager.mongodb_db.device_connections.insert_one(device_info)
            
            return {
                'success': True,
                'message': f'蓝牙连接成功: {device_address}',
                'connection_id': self.connection_type
            }
        except Exception as e:
            self.logger.error(f"蓝牙连接失败: {str(e)}")
            return {'success': False, 'message': f'蓝牙连接失败: {str(e)}'}
    
    def disconnect(self):
        """断开设备连接
        
        Returns:
            dict: 断开结果
        """
        if not self.connected:
            return {'success': False, 'message': '没有连接的设备'}
        
        try:
            # 停止数据读取线程
            self.stop_thread = True
            if self.data_thread and self.data_thread.is_alive():
                self.data_thread.join(2.0)  # 等待线程结束，最多2秒
            
            # 关闭连接
            if self.connection_type == 'serial' and self.serial_port:
                self.serial_port.close()
                self.serial_port = None
            elif self.connection_type == 'udp' and self.udp_socket:
                self.udp_socket.close()
                self.udp_socket = None
            elif self.connection_type == 'bluetooth' and self.bluetooth_socket:
                # 关闭蓝牙连接的代码
                self.bluetooth_socket = None
            
            # 更新设备连接状态
            database_manager.mongodb_db.device_connections.update_one(
                {'device_type': self.connection_type, 'status': 'connected'},
                {'$set': {'status': 'disconnected', 'disconnected_at': datetime.now()}}
            )
            
            self.connected = False
            old_type = self.connection_type
            self.connection_type = None
            self.connection_params = {}
            
            return {'success': True, 'message': f'{old_type}设备断开成功'}
        except Exception as e:
            self.logger.error(f"断开设备连接失败: {str(e)}")
            return {'success': False, 'message': f'断开设备连接失败: {str(e)}'}
    
    def get_connection_status(self):
        """获取设备连接状态
        
        Returns:
            dict: 连接状态
        """
        status = {
            'connected': self.connected,
            'connection_type': self.connection_type,
            'connection_params': self.connection_params
        }
        return {'success': True, 'status': status}
    
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
    
    def _read_serial_data(self):
        """读取串口数据的线程函数"""
        while not self.stop_thread and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.readline().strip()
                    if data:
                        # 通知所有监听器
                        for listener in self.data_listeners:
                            try:
                                listener(data, 'serial')
                            except Exception as e:
                                self.logger.error(f"处理串口数据时出错: {str(e)}")
            except Exception as e:
                self.logger.error(f"读取串口数据时出错: {str(e)}")
                time.sleep(0.1)
    
    def _read_udp_data(self):
        """读取UDP数据的线程函数"""
        self.udp_socket.settimeout(0.5)  # 设置超时，使线程可以正常退出
        while not self.stop_thread and self.udp_socket:
            try:
                data, addr = self.udp_socket.recvfrom(4096)
                if data:
                    # 通知所有监听器
                    for listener in self.data_listeners:
                        try:
                            listener(data, 'udp', addr)
                        except Exception as e:
                            self.logger.error(f"处理UDP数据时出错: {str(e)}")
            except socket.timeout:
                # 超时是正常的，继续尝试
                pass
            except Exception as e:
                self.logger.error(f"读取UDP数据时出错: {str(e)}")
                time.sleep(0.1)
    
    def _read_bluetooth_data(self):
        """读取蓝牙数据的线程函数"""
        # 注意：这里需要根据具体的蓝牙库实现
        # 这里只是一个示例框架
        while not self.stop_thread and self.bluetooth_socket:
            try:
                # 实现蓝牙数据读取逻辑
                data = None  # 替换为实际的蓝牙数据读取代码
                if data:
                    # 通知所有监听器
                    for listener in self.data_listeners:
                        try:
                            listener(data, 'bluetooth')
                        except Exception as e:
                            self.logger.error(f"处理蓝牙数据时出错: {str(e)}")
                time.sleep(0.1)  # 避免CPU占用过高
            except Exception as e:
                self.logger.error(f"读取蓝牙数据时出错: {str(e)}")
                time.sleep(0.1)

# 初始化设备服务
device_service = DeviceService()
