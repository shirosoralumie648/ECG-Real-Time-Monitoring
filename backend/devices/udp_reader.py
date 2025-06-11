# udp_reader.py

import socket
import threading
import eventlet
import time

class UDPReader:
    def __init__(self, local_ip='0.0.0.0', local_port=5001, remote_ip=None, remote_port=None):
        self.local_ip = local_ip
        self.local_port = local_port
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.socket = None
        self.is_running = False
        self.callbacks = []
        self.buffer = bytearray()
        
    def open(self):
        try:
            # 创建UDP套接字
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # 设置超时，避免阻塞
            self.socket.settimeout(0.5)
            
            # 绑定到本地地址和端口
            self.socket.bind((self.local_ip, self.local_port))
            
            print(f"UDP socket bound to {self.local_ip}:{self.local_port}")
            
            # 如果指定了远程地址，可以设置为连接模式（可选）
            if self.remote_ip and self.remote_port:
                print(f"Remote endpoint set to {self.remote_ip}:{self.remote_port}")
            
            return True
                
        except Exception as e:
            print(f"Failed to open UDP socket: {e}")
            raise
    
    def start_reading(self):
        """开始读取数据"""
        if not self.socket:
            raise Exception("UDP套接字未创建，无法开始读取数据")
            
        self.is_running = True
        
        # 使用eventlet绿线程启动数据接收
        if hasattr(eventlet, 'spawn'):
            eventlet.spawn(self.read_data)
            print(f"Started reading from UDP socket {self.local_ip}:{self.local_port} with eventlet")
        else:
            # 如果eventlet不可用，使用标准线程
            threading.Thread(target=self.read_data, daemon=True).start()
            print(f"Started reading from UDP socket {self.local_ip}:{self.local_port} with threading")
    
    def close(self):
        self.is_running = False
        if self.socket:
            self.socket.close()
            self.socket = None
    
    def read_data(self):
        consecutive_errors = 0
        max_errors = 5
        
        while self.is_running:
            try:
                # 尝试接收数据
                try:
                    data, addr = self.socket.recvfrom(4096)  # 缓冲区大小
                    
                    # 如果设置了远程端点，检查数据是否来自预期的源
                    if self.remote_ip and self.remote_port:
                        if addr[0] != self.remote_ip or addr[1] != self.remote_port:
                            print(f"Received data from unexpected source: {addr}, expected {self.remote_ip}:{self.remote_port}")
                            continue
                    
                    if data:
                        print(f"Received {len(data)} bytes from {addr}")
                        # 处理接收到的数据
                        self._handle_data(data)
                        consecutive_errors = 0  # 重置错误计数
                
                except socket.timeout:
                    # 超时是正常的，不计入错误
                    pass
                    
                except socket.error as e:
                    consecutive_errors += 1
                    print(f"Socket error: {e}. Error count: {consecutive_errors}")
                
                # 如果连续错误超过限制，重新创建套接字
                if consecutive_errors >= max_errors:
                    print(f"Too many consecutive errors ({consecutive_errors}), reconnecting...")
                    try:
                        if self.socket:
                            self.socket.close()
                        
                        # 重新创建套接字
                        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        self.socket.settimeout(0.5)
                        self.socket.bind((self.local_ip, self.local_port))
                        consecutive_errors = 0
                    except Exception as e:
                        print(f"Failed to reconnect: {e}")
                
                # 让出控制权
                eventlet.sleep(0.01)
                
            except Exception as e:
                consecutive_errors += 1
                print(f"Unexpected error in read_data: {e}. Error count: {consecutive_errors}")
                eventlet.sleep(0.5)
    
    def _handle_data(self, data):
        # 将数据添加到缓冲区
        self.buffer.extend(data)
        
        # 解析数据帧 - 这里需要根据实际协议进行调整
        self._parse_frames()
        
        # 通知回调函数
        for callback in self.callbacks:
            callback(data)
    
    def _parse_frames(self):
        # 这里需要根据实际的数据格式实现帧解析
        # 例如，如果数据是按照某种帧格式发送的，需要在这里解析
        # 简单示例：假设每个帧以特定字节结束
        frame_end = bytes([0xFF, 0xFF])  # 示例帧结束标记
        
        while True:
            end_index = self.buffer.find(frame_end)
            if end_index != -1:
                # 找到一个完整的帧
                frame = self.buffer[:end_index + len(frame_end)]
                # 处理帧数据 - 这里只是示例，需要根据实际协议调整
                self._process_frame(frame)
                # 从缓冲区中移除已处理的帧
                self.buffer = self.buffer[end_index + len(frame_end):]
            else:
                # 没有找到完整的帧，等待更多数据
                break
    
    def _process_frame(self, frame):
        # 处理单个数据帧 - 需要根据实际协议实现
        # 这里只是一个示例
        print(f"Processing frame: {len(frame)} bytes")
        # 实际处理逻辑...
    
    def register_callback(self, callback):
        """注册一个回调函数，当接收到新数据时调用"""
        self.callbacks.append(callback)
    
    def send_data(self, data):
        """向远程端点发送数据"""
        if not self.socket:
            raise Exception("Socket is not open")
        
        if not self.remote_ip or not self.remote_port:
            raise Exception("Remote endpoint not specified")
        
        try:
            bytes_sent = self.socket.sendto(data, (self.remote_ip, self.remote_port))
            print(f"Sent {bytes_sent} bytes to {self.remote_ip}:{self.remote_port}")
            return bytes_sent
        except Exception as e:
            print(f"Failed to send data: {e}")
            raise
