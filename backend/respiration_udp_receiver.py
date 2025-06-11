# respiration_udp_receiver.py

import socket
import struct
import time
import threading
import eventlet

eventlet.monkey_patch()

class RespirationUDPReceiver:
    """接收呼吸波形数据的UDP接收器，适用于VOFA+的Firewater格式"""
    
    def __init__(self, host='127.0.0.1', port=1347):
        """初始化UDP接收器
        
        Args:
            host: UDP服务器主机地址
            port: UDP服务器端口
        """
        self.host = host
        self.port = port
        self.sock = None
        self.is_running = False
        self.callbacks = []
        self.buffer = bytearray()
        # Firewater格式的帧尾标识
        self.FRAME_TAIL = b'\x00\x00\x80\x7F'
        
    def start(self):
        """启动UDP接收器"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.host, self.port))
            self.sock.settimeout(0.5) # 设置超时，便于优雅退出
            self.is_running = True
            # 使用Eventlet的绿线程
            eventlet.spawn(self.receive_data)
            # 同时使用传统线程作为备份
            threading.Thread(target=self.receive_data, daemon=True).start()
            print(f"UDP receiver started on {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Failed to start UDP receiver: {e}")
            return False
    
    def stop(self):
        """停止UDP接收器"""
        self.is_running = False
        if self.sock:
            self.sock.close()
            self.sock = None
        print("UDP receiver stopped")
    
    def receive_data(self):
        """接收UDP数据的主循环"""
        while self.is_running and self.sock:
            try:
                data, addr = self.sock.recvfrom(4096)
                if data:
                    self.buffer.extend(data)
                    self._parse_frames()
                eventlet.sleep(0)  # 让出控制权
            except socket.timeout:
                # 超时是正常的，继续循环
                pass
            except Exception as e:
                print(f"Error receiving UDP data: {e}")
                if not self.is_running:
                    break
    
    def _parse_frames(self):
        """解析Firewater格式的数据帧"""
        while True:
            tail_index = self.buffer.find(self.FRAME_TAIL)
            if tail_index != -1:
                frame_end = tail_index + len(self.FRAME_TAIL)
                if tail_index > 0:
                    frame_data = self.buffer[:tail_index]
                    try:
                        # 获取当前时间戳
                        current_time = time.time()
                        # 解析浮点数据
                        values = self.parse_frame(frame_data)
                        # 调用回调函数，传递解析后的值和时间戳
                        for callback in self.callbacks:
                            callback(values, current_time)
                    except Exception as e:
                        print(f"Error parsing frame: {e}")
                # 移除已处理的数据
                self.buffer = self.buffer[frame_end:]
            else:
                break
    
    def parse_frame(self, data):
        """解析Firewater格式的数据帧内容
        
        Args:
            data: 原始数据帧，不包含帧尾
            
        Returns:
            list: 解析出的浮点数值列表
        """
        # 确保数据长度是4的倍数（每个浮点数占4字节）
        if len(data) % 4 != 0:
            raise ValueError(f"Invalid frame length: {len(data)}")
        
        values = []
        # 每4个字节解析一个浮点数
        for i in range(0, len(data), 4):
            if i + 4 <= len(data):
                bytes_ = data[i:i+4]
                value = struct.unpack('<f', bytes_)[0]  # 小端格式浮点数
                values.append(value)
        
        return values
    
    def register_callback(self, callback):
        """注册数据回调函数
        
        Args:
            callback: 回调函数，接收参数(values, timestamp)
        """
        self.callbacks.append(callback)
