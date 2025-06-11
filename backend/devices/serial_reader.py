#serial_reader.py
import time

import eventlet
eventlet.monkey_patch()

import serial
import struct
import threading

class SerialPortReader:
    FRAME_TAIL = b'\x00\x00\x80\x7F'

    def __init__(self, port='COM7', baudrate=921600):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.is_running = False
        self.callbacks = []
        self.buffer = bytearray()
        
        # 添加固定采样率机制相关参数
        self.fixed_sampling_rate = True     # 是否启用固定采样率
        self.target_sampling_rate = 500     # 目标采样率（Hz）
        self.sampling_interval = 1.0 / self.target_sampling_rate  # 采样间隔（秒）
        self.last_sample_time = None       # 上次采样时间
        self.sample_count = 0              # 采样计数器
        self.time_correction_factor = 1.0  # 时间校正因子
        
        # 数据统计参数
        self.stats = {
            'frames_received': 0,
            'frames_processed': 0,
            'errors': 0,
            'start_time': None,
            'actual_sampling_rate': 0
        }

    def open(self):
        try:
            # 添加更多的串口配置选项
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
                write_timeout=None,
                inter_byte_timeout=None
            )
            
            # 检查串口是否成功打开
            if not self.serial_conn.is_open:
                self.serial_conn.open()
                
            print(f"Serial port {self.port} opened successfully")
            return True
        except serial.SerialException as e:
            print(f"Serial exception when opening port {self.port}: {e}")
            raise
        except Exception as e:
            print(f"Failed to open serial port {self.port}: {e}")
            raise
    
    def start_reading(self):
        """开始读取数据"""
        if not self.serial_conn or not self.serial_conn.is_open:
            raise Exception("串口未打开，无法开始读取数据")
            
        self.is_running = True
        
        # 只使用一种线程方式，避免冲突
        if hasattr(eventlet, 'spawn'):
            # 使用Eventlet的绿线程
            eventlet.spawn(self.read_data)
            print(f"Started reading from serial port {self.port} with eventlet")
        else:
            # 如果eventlet不可用，使用标准线程
            threading.Thread(target=self.read_data, daemon=True).start()
            print(f"Started reading from serial port {self.port} with threading")

    def close(self):
        self.is_running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()

    def read_data(self):
        """
        改进的数据读取方法，实现固定采样率机制和时间戳精确控制
        """
        consecutive_errors = 0
        max_errors = 5  # 最大连续错误次数
        
        # 初始化统计数据
        self.stats['start_time'] = time.time()
        self.last_sample_time = self.stats['start_time']
        
        # 计算目标读取间隔 - 为了保证不错过数据，读取间隔应小于采样间隔
        read_interval = min(0.005, self.sampling_interval / 2)  # 最小5毫秒，或采样间隔的一半
        
        while self.is_running:
            try:
                # 检查是否应该进行采样（固定采样率模式）
                current_time = time.time()
                
                if self.fixed_sampling_rate:
                    # 如果距离上次采样的时间小于采样间隔，等待一段时间
                    time_since_last_sample = current_time - self.last_sample_time
                    if time_since_last_sample < self.sampling_interval:
                        # 计算需要等待的时间
                        wait_time = max(0, self.sampling_interval - time_since_last_sample)
                        # 使用更精确的等待方式
                        if wait_time > 0.001:  # 如果等待时间大于1毫秒
                            eventlet.sleep(wait_time)
                        continue
                
                # 检查串口是否仍然打开
                if not self.serial_conn or not self.serial_conn.is_open:
                    print("Serial port is closed, attempting to reopen...")
                    try:
                        if self.serial_conn:
                            self.serial_conn.open()
                        else:
                            # 如果串口对象不存在，重新创建
                            self.open()
                    except Exception as e:
                        print(f"Failed to reopen serial port: {e}")
                        consecutive_errors += 1
                        eventlet.sleep(1)  # 等待一秒再重试
                        continue
                
                # 尝试读取数据
                in_waiting = self.serial_conn.in_waiting
                if in_waiting > 0:
                    # 更新采样时间
                    self.last_sample_time = time.time()
                    self.sample_count += 1
                    
                    # 读取数据
                    data = self.serial_conn.read(in_waiting)
                    if data:
                        self.stats['frames_received'] += 1
                        self.buffer.extend(data)
                        self._parse_frames()
                        consecutive_errors = 0  # 重置错误计数
                        
                        # 计算实际采样率并调整时间校正因子
                        if self.sample_count % 100 == 0 and self.stats['start_time']:
                            elapsed_time = time.time() - self.stats['start_time']
                            if elapsed_time > 0:
                                self.stats['actual_sampling_rate'] = self.sample_count / elapsed_time
                                # 调整时间校正因子
                                if self.stats['actual_sampling_rate'] > 0:
                                    self.time_correction_factor = self.target_sampling_rate / self.stats['actual_sampling_rate']
                                    print(f"实际采样率: {self.stats['actual_sampling_rate']:.2f} Hz, 校正因子: {self.time_correction_factor:.4f}")
                    else:
                        # 设备报告可读但没有返回数据
                        consecutive_errors += 1
                        self.stats['errors'] += 1
                        print(f"设备报告数据但返回为空. 错误计数: {consecutive_errors}")
                else:
                    # 没有数据可读，读取一个字节并设置超时
                    try:
                        # 使用非阻塞方式检查是否有数据可读
                        if self.serial_conn.timeout != 0:
                            old_timeout = self.serial_conn.timeout
                            self.serial_conn.timeout = 0
                            data = self.serial_conn.read(1)
                            self.serial_conn.timeout = old_timeout
                        else:
                            data = self.serial_conn.read(1)
                            
                        if data:
                            self.last_sample_time = time.time()
                            self.sample_count += 1
                            self.stats['frames_received'] += 1
                            self.buffer.extend(data)
                            self._parse_frames()
                            consecutive_errors = 0  # 重置错误计数
                    except serial.SerialException as e:
                        consecutive_errors += 1
                        self.stats['errors'] += 1
                        print(f"读取时发生串口异常: {e}. 错误计数: {consecutive_errors}")
                
                # 如果连续错误超过限制，重新连接
                if consecutive_errors >= max_errors:
                    print(f"连续错误过多 ({consecutive_errors})，正在重新连接...")
                    try:
                        if self.serial_conn:
                            self.serial_conn.close()
                        eventlet.sleep(1)  # 等待一秒
                        self.open()  # 使用open方法重新打开串口
                        consecutive_errors = 0
                    except Exception as e:
                        print(f"重新连接失败: {e}")
                        self.stats['errors'] += 1
                
                # 使用动态调整的读取间隔
                eventlet.sleep(read_interval)
                
            except serial.SerialException as e:
                consecutive_errors += 1
                self.stats['errors'] += 1
                print(f"串口异常: {e}. 错误计数: {consecutive_errors}")
                eventlet.sleep(0.5)  # 出错后等待一段时间
                
            except Exception as e:
                consecutive_errors += 1
                self.stats['errors'] += 1
                print(f"read_data中发生意外错误: {e}. 错误计数: {consecutive_errors}")
                eventlet.sleep(0.5)  # 出错后等待一段时间

    def _parse_frames(self):
        """
        解析数据帧并应用时间戳精确控制
        """
        frames_processed = 0
        
        while True:
            tail_index = self.buffer.find(self.FRAME_TAIL)
            if tail_index != -1:
                frame_end = tail_index + len(self.FRAME_TAIL)
                if tail_index > 0:
                    frame_data = self.buffer[:tail_index]
                    try:
                        # 获取当前时间戳并应用校正因子
                        current_time = time.time()
                        
                        # 如果启用了固定采样率，使用计算的时间戳
                        if self.fixed_sampling_rate and self.stats['start_time'] is not None:
                            # 计算基于采样计数的理论时间戳
                            frames_processed += 1
                            theoretical_time = self.stats['start_time'] + (frames_processed / self.target_sampling_rate)
                            
                            # 应用校正因子来调整时间戳
                            # 使用加权平均来平滑时间戳变化
                            weight = 0.8  # 理论时间的权重
                            adjusted_time = (theoretical_time * weight) + (current_time * (1 - weight))
                            
                            # 确保时间戳不会大于当前时间
                            current_time = min(adjusted_time, current_time)
                        
                        # 解析数据帧
                        values = self.parse_frame(frame_data)
                        self.stats['frames_processed'] += 1
                        
                        # 确保值是Python原生列表，而不是NumPy数组
                        if hasattr(values, 'tolist'):
                            values = values.tolist()
                        
                        # 递归检查列表中的所有元素，确保没有NumPy数组
                        def convert_numpy_to_list(obj):
                            if isinstance(obj, list):
                                return [convert_numpy_to_list(item) for item in obj]
                            elif hasattr(obj, 'tolist'):
                                return obj.tolist()
                            else:
                                return obj
                        
                        values = convert_numpy_to_list(values)
                        
                        # 回调函数传递解析的值和精确时间戳
                        for callback in self.callbacks:
                            callback(values, current_time)
                    except Exception as e:
                        self.stats['errors'] += 1
                        print(f"解析帧时出错: {e}")
                self.buffer = self.buffer[frame_end:]
            else:
                break

    def parse_frame(self, data):
        expected_length = 4 * 8
        if len(data) != expected_length:
            raise ValueError(f"Frame length mismatch: expected {expected_length}, got {len(data)}")
        values = []
        for i in range(8):
            bytes_ = data[i*4:(i+1)*4]
            value = struct.unpack('<f', bytes_)[0]
            values.append(value)
        return values

    def register_callback(self, callback):
        self.callbacks.append(callback)
