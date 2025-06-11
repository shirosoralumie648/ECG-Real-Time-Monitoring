# ecg_monitoring_system.py

import time
import uuid
from datetime import datetime
from ..processing.ecg_data_processor import ECGDataProcessor
from ..devices.serial_reader import SerialPortReader
from ..data.data_storage import DataStorage  # 导入DataStorage
from ..data.database_manager import database_manager  # 导入数据库管理器
import numpy as np  # 导入 NumPy

class ECGMonitoringSystem:
    def __init__(self, socketio):
        self.socketio = socketio
        self.data_processor = ECGDataProcessor()
        self.data_storage = DataStorage()  # 实例DataStorage
        self.accumulated_data = {i: [] for i in range(12)}  # 存储12个导联的数据，包含 (timestamp, value)
        
        # 会话和患者相关字段
        self.session_id = str(uuid.uuid4())  # 生成唯一会话ID
        self.patient_id = None  # 当前患者ID，可以通过set_patient_id方法设置
        self.sample_counter = 0  # 数据计数器
        
        # 降低批处理大小，提高数据发送频率
        self.max_samples = 200   # 每次发送的数据点数量，从500降低到200
        
        # 数据处理参数
        self.interpolation_method = 'cubic'  # 插值方法：'linear', 'cubic', 'akima'
        self.continuity_threshold = 2.0      # 检测时间间隔异常的阈值倍数
        self.interpolation_threshold = 1.5   # 触发插值的时间间隔阈值倍数
        
        # 数据缓冲参数
        self.buffer_multiplier = 5          # 缓冲区大小为批处理大小的倍数
        
        self.start_timestamp = None
        self.end_timestamp = None
        
        # 数据来源相关变量
        self.data_source = None
        self.data_source_type = None
        self.file_replay_thread = None
        self.file_replay_running = False
        
        # 数据采集时间控制
        self.last_data_time = None
        self.fixed_sampling_interval = None  # 固定采样间隔，毫秒，自动计算

    # 连接串口设备
    def connect_serial(self, port='COM7', baudrate=921600):
        print(f"Connecting to serial port {port} at {baudrate} baud")
        
        # 如果已经有连接，先断开
        self.disconnect()
        
        try:
            # 创建并配置串口读取器
            self.data_source = SerialPortReader(port=port, baudrate=baudrate)
            self.data_source.register_callback(self.handle_new_data)
            
            # 只连接串口，不开始读取数据
            self.data_source.open()
            self.data_source_type = 'serial'
            
            # 发送连接状态通知
            self.socketio.emit('connection_status', {'status': 'connected', 'type': 'serial', 'port': port, 'baudrate': baudrate})
            self.socketio.emit('notification', {'message': f'已连接到串口 {port}，波特率 {baudrate}'})
            return True
        except Exception as e:
            error_msg = f"串口连接失败: {str(e)}"
            print(error_msg)
            self.socketio.emit('notification', {'message': error_msg, 'type': 'error'})
            self.socketio.emit('connection_status', {'status': 'disconnected'})
            raise
    
    # 连接UDP设备
    def connect_udp(self, local_ip='0.0.0.0', local_port=5001, remote_ip=None, remote_port=None):
        print(f"Connecting to UDP on {local_ip}:{local_port}")
        if remote_ip and remote_port:
            print(f"Remote endpoint set to {remote_ip}:{remote_port}")
        
        # 如果已经有连接，先断开
        self.disconnect()
        
        try:
            # 导入UDPReader类
            from ..devices.udp_reader import UDPReader
            
            # 创建UDP数据接收器
            self.data_source = UDPReader(
                local_ip=local_ip, 
                local_port=int(local_port), 
                remote_ip=remote_ip, 
                remote_port=int(remote_port) if remote_port else None
            )
            
            # 注册数据回调
            self.data_source.register_callback(self.handle_new_data)
            
            # 只打开UDP连接，不开始读取数据
            self.data_source.open()
            self.data_source_type = 'udp'
            
            # 发送连接状态和通知
            connection_info = {
                'status': 'connected', 
                'type': 'udp', 
                'local_ip': local_ip, 
                'local_port': local_port
            }
            
            if remote_ip and remote_port:
                connection_info['remote_ip'] = remote_ip
                connection_info['remote_port'] = remote_port
            
            self.socketio.emit('connection_status', connection_info)
            
            # 发送通知
            message = f'已连接到UDP，监听 {local_ip}:{local_port}'
            if remote_ip and remote_port:
                message += f'，远程端点 {remote_ip}:{remote_port}'
                
            self.socketio.emit('notification', {'message': message})
            return True
            
        except Exception as e:
            error_msg = f"UDP连接失败: {str(e)}"
            print(error_msg)
            self.socketio.emit('notification', {'message': error_msg, 'type': 'error'})
            self.socketio.emit('connection_status', {'status': 'disconnected'})
            raise
    
    # 连接蓝牙设备
    def connect_bluetooth(self, port, baudrate=921600):
        print(f"Connecting to bluetooth device on port {port} at {baudrate} baud")
        
        # 如果已经有连接，先断开
        self.disconnect()
        
        # 检查端口是否存在
        if port == "/dev/null":
            # 使用模拟数据源
            print("Using mock data source for Bluetooth")
            self.data_source_type = 'bluetooth_mock'
            self.socketio.emit('connection_status', {'status': 'connected', 'type': 'bluetooth', 'port': 'mock', 'baudrate': baudrate})
            self.socketio.emit('notification', {'message': f'已连接到模拟蓝牙设备'})
            return True
        
        try:
            # 蓝牙设备在服务器端已经被映射为串口
            # 因此可以直接使用SerialPortReader进行读取
            baudrate_int = int(baudrate)
            
            print(f"Using baudrate {baudrate_int} for Bluetooth device")
                
            # 创建串口读取器并注册回调
            self.data_source = SerialPortReader(port=port, baudrate=baudrate_int)
            self.data_source.register_callback(self.handle_new_data)
            
            # 只打开连接，不开始读取数据
            self.data_source.open()
            self.data_source_type = 'bluetooth'
            
            # 发送连接状态和通知
            self.socketio.emit('connection_status', {'status': 'connected', 'type': 'bluetooth', 'port': port, 'baudrate': baudrate_int})
            self.socketio.emit('notification', {'message': f'已连接到蓝牙设备 {port}，波特率 {baudrate_int}'})
            return True
            
        except Exception as e:
            error_msg = f"蓝牙连接失败: {str(e)}"
            print(error_msg)
            self.socketio.emit('notification', {'message': error_msg, 'type': 'error'})
            self.socketio.emit('connection_status', {'status': 'disconnected'})
            raise
    
    # 连接文件数据源
    def connect_file(self, file_name):
        print(f"Connecting to file data source: {file_name}")
        
        # 如果已经有连接，先断开
        self.disconnect()
        
        try:
            # 检查文件是否存在
            import os
            if not os.path.exists(file_name):
                raise FileNotFoundError(f"文件 {file_name} 不存在")
            
            # 设置文件数据源
            self.data_source_type = 'file'
            self.file_name = file_name
            
            # 发送连接状态
            self.socketio.emit('connection_status', {'status': 'connected', 'type': 'file', 'fileName': file_name})
            self.socketio.emit('notification', {'message': f'已连接到文件数据源: {file_name}'})
            return True
        except Exception as e:
            error_msg = f"文件连接失败: {str(e)}"
            print(error_msg)
            self.socketio.emit('notification', {'message': error_msg, 'type': 'error'})
            self.socketio.emit('connection_status', {'status': 'disconnected'})
            raise
    
    # 断开当前连接
    def disconnect(self):
        print("Disconnecting from current data source")
        
        if self.data_source:
            try:
                # 停止数据源
                if hasattr(self.data_source, 'close'):
                    self.data_source.close()
                    
                # 如果正在监测，先停止
                self.stop()
                
            except Exception as e:
                print(f"Error while disconnecting: {e}")
            finally:
                self.data_source = None
                
        # 重置数据源类型
        self.data_source_type = None
        
        # 发送断开连接状态
        self.socketio.emit('connection_status', {'status': 'disconnected'})
        self.socketio.emit('notification', {'message': '已断开数据源连接'})
    
    # 开始监测（连接后调用）
    def start_monitoring(self, speed=1.0):
        print(f"Starting monitoring with data source type: {self.data_source_type}")
        
        if not self.data_source_type:
            error_msg = "没有连接数据源，无法开始监测"
            print(error_msg)
            self.socketio.emit('notification', {'message': error_msg, 'type': 'error'})
            return False
            
        self.start_timestamp = time.time()
        self.data_storage.reset_data()
        
        try:
            # 根据数据源类型启动监测
            if self.data_source_type == 'file':
                # 文件回放模式需要特殊处理
                self._start_file_replay(speed)
                self.socketio.emit('notification', {'message': f'文件回放已开始: {self.file_name}, 速度 {speed}x'})
            elif self.data_source_type in ['serial', 'bluetooth', 'bluetooth_mock']:
                # 串口和蓝牙模式使用SerialPortReader
                if hasattr(self.data_source, 'start_reading'):
                    self.data_source.start_reading()
                else:
                    raise Exception(f"数据源{self.data_source_type}不支持start_reading方法")
            elif self.data_source_type == 'udp':
                # UDP模式
                if hasattr(self.data_source, 'start_reading'):
                    self.data_source.start_reading()
                else:
                    raise Exception("UDP数据源不支持start_reading方法")
            else:
                raise Exception(f"不支持的数据源类型: {self.data_source_type}")
            
            # 发送通知
            source_type_names = {
                'serial': '串口',
                'udp': 'UDP',
                'bluetooth': '蓝牙',
                'bluetooth_mock': '模拟蓝牙',
                'file': '文件'
            }
            
            source_type_name = source_type_names.get(self.data_source_type, self.data_source_type)
            self.socketio.emit('notification', {'message': f'{source_type_name}数据监测已开始'})
            return True
            
        except Exception as e:
            error_msg = f"启动监测失败: {str(e)}"
            print(error_msg)
            self.socketio.emit('notification', {'message': error_msg, 'type': 'error'})
            return False
            
    # 启动文件回放
    def _start_file_replay(self, speed=1.0):
        """启动文件回放线程"""
        # 停止现有的回放线程（如果有）
        if self.file_replay_thread and self.file_replay_running:
            self.file_replay_running = False
            self.file_replay_thread.join(timeout=1.0)
        
        # 启动新的文件回放线程
        self.file_replay_running = True
        self.file_replay_thread = threading.Thread(
            target=self._file_replay_worker,
            args=(self.file_name, speed),
            daemon=True
        )
        self.file_replay_thread.start()
    
    # 文件回放工作线程
    def _file_replay_worker(self, file_name, speed):
        """文件回放的工作线程"""
        try:
            # 加载文件数据
            import numpy as np
            import os
            
            file_path = os.path.join('.', file_name)
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                self.socketio.emit('notification', {'message': f'文件不存在: {file_path}', 'type': 'error'})
                return
            
            # 加载数据（根据文件类型选择不同的加载方式）
            if file_name.endswith('.npy'):
                data = np.load(file_path)
            elif file_name.endswith('.csv'):
                data = np.loadtxt(file_path, delimiter=',')
            elif file_name.endswith('.json'):
                import json
                with open(file_path, 'r') as f:
                    json_data = json.load(f)
                # 假设数据格式为 {"leads": [...], "timestamps": [...]}
                if isinstance(json_data, dict) and 'leads' in json_data:
                    data = np.array(json_data['leads'])
                else:
                    data = np.array(json_data)
            else:
                # 默认尝试作为文本文件读取
                data = np.loadtxt(file_path)
            
            # 计算回放间隔（根据速度调整）
            interval = 0.02 / speed  # 假设原始采样率是50Hz
            
            # 模拟数据流
            for i in range(0, len(data), 12):  # 假设每12个数据点为一组
                if not self.file_replay_running:
                    break
                
                # 获取一组数据
                if i + 12 <= len(data):
                    values = data[i:i+12]
                    timestamp = time.time()
                    
                    # 处理数据，就像从串口收到的一样
                    self.handle_new_data(values, timestamp)
                
                # 按照调整后的速度等待
                time.sleep(interval)
                
        except Exception as e:
            print(f"Error in file replay: {e}")
            self.socketio.emit('notification', {'message': f'文件回放错误: {str(e)}', 'type': 'error'})
        finally:
            self.file_replay_running = False
            print("File replay finished")
    
    # 停止监测
    def stop(self):
        print("Stopping ECG monitoring")
        self.end_timestamp = time.time()
        
        # 停止文件回放线程
        if self.file_replay_thread and self.file_replay_running:
            self.file_replay_running = False
            self.file_replay_thread.join(timeout=1.0)
            self.file_replay_thread = None
        
        # 停止其他类型的数据源读取
        if self.data_source and hasattr(self.data_source, 'is_running'):
            self.data_source.is_running = False
        
        # 保存数据
        if self.start_timestamp and self.end_timestamp:
            duration = self.end_timestamp - self.start_timestamp
            if duration > 5:  # 只保存超过5秒的记录
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                self.data_storage.save_data(f"ecg_data_{timestamp}.json")
        
        self.socketio.emit('notification', {'message': '数据监测已停止'})
        return {'status': 'stopped'}
    
    # 处理新数据
    def handle_new_data(self, values, timestamp):
        """
        处理新数据，增强了时间戳精确性和采样率控制
        
        参数:
            values: 原始数据值
            timestamp: 数据时间戳
        """
        # 使用传递过来的时间戳
        current_time = timestamp
        
        # 计算采样间隔，用于检测采样率
        if self.last_data_time is not None:
            interval = current_time - self.last_data_time
            
            # 如果还没有计算固定采样间隔，则计算
            if self.fixed_sampling_interval is None and interval > 0:
                # 使用前10个数据点的平均间隔作为固定采样间隔
                if len(self.accumulated_data[0]) >= 10:
                    times = [t for t, _ in self.accumulated_data[0][-10:]]
                    intervals = [times[i+1] - times[i] for i in range(len(times)-1)]
                    if intervals:
                        self.fixed_sampling_interval = sum(intervals) / len(intervals)
                        print(f"固定采样间隔设置为: {self.fixed_sampling_interval:.6f} 秒")
        
        # 更新最后一次数据时间
        self.last_data_time = current_time

        # 计算12导联数据
        leads_12 = self.data_processor.compute_12_leads(values)
        
        # 保存数据点
        self.data_storage.save_data_point(current_time, leads_12)

        # 将数据添加到累积缓冲区
        for i in range(12):
            self.accumulated_data[i].append((current_time, leads_12[i]))
        
        # 增加计数器
        self.sample_counter += 1

        # 当累积足够数据点时处理并发送
        if self.sample_counter >= self.max_samples:
            self.process_and_send_data()
            self.sample_counter = 0
            
    def set_patient_id(self, patient_id):
        """设置当前监测的患者ID
        
        Args:
            patient_id (str): 患者ID
        """
        self.patient_id = patient_id
        print(f"已设置患者ID: {patient_id}")
    
    def process_and_send_data(self):
        """
        处理累积的数据并发送到前端
        使用改进的插值算法和数据处理流程
        同时将数据存储到数据库中
        """
        # 处理累积的数据
        processed_signals = []
        time_stamps = []
        
        # 检查数据连续性的辅助函数
        def check_continuity(times):
            """检查时间序列的连续性并返回间隔统计信息"""
            if len(times) < 2:
                return True, None
            
            # 计算时间间隔
            intervals = [times[i+1] - times[i] for i in range(len(times)-1)]
            if not intervals:
                return True, None
            
            # 计算间隔统计信息
            median_interval = sorted(intervals)[len(intervals)//2]
            avg_interval = sum(intervals) / len(intervals)
            max_interval = max(intervals)
            min_interval = min(intervals)
            
            # 创建间隔统计信息字典
            interval_stats = {
                'median': median_interval,
                'mean': avg_interval,
                'max': max_interval,
                'min': min_interval,
                'range': max_interval - min_interval,
                'count': len(intervals)
            }
            
            # 使用自适应阈值检测异常间隔
            threshold_factor = self.continuity_threshold
            
            # 如果间隔非常均匀，使用更严格的阈值
            if max_interval / (min_interval + 1e-10) < 5:
                threshold_factor = 3.0
            
            # 检测异常间隔
            has_large_gap = max_interval > median_interval * threshold_factor
            
            # 只在有异常间隔时输出日志，减少日志数量
            if has_large_gap:
                # 每20次检测只输出一次日志，减少日志数量
                if self.sample_counter % 20 == 0:
                    print(f"检测到异常时间间隔: {max_interval:.4f}秒, 中位数间隔: {median_interval:.4f}秒, 平均间隔: {avg_interval:.4f}秒")
            
            return not has_large_gap, interval_stats
        
        # 处理每个导联的数据
        for i in range(12):
            # 获取最近的 max_samples 个数据点
            data = self.accumulated_data[i][-self.max_samples:]
            
            # 如果数据点数量足够，进行处理
            if len(data) >= 10:  # 降低最小数据点要求从18降到10
                # 分离时间戳和数据值
                times, values = zip(*data)
                times = list(times)
                values = list(values)
                
                # 检查时间序列是否单调递增
                is_monotonic = True
                for j in range(len(times)-1):
                    if times[j] >= times[j+1]:
                        is_monotonic = False
                        break
                        
                if not is_monotonic:
                    # 每10次检测只输出一次日志，减少日志数量
                    if self.sample_counter % 10 == 0:
                        print("时间序列不是单调递增的，但保留原始顺序")
                    # 不再对时间和值进行排序，保留原始顺序
                    pass
                
                # 检查数据连续性
                continuity_ok, _ = check_continuity(times)
                
                # 禁用插值处理，直接使用原始数据
                if not continuity_ok and len(times) > 2:
                    # 记录数据不连续的情况，但不进行插值处理
                    if self.sample_counter % 10 == 0:
                        print(f"检测到数据不连续，但保留原始数据 (间隔: {_.get('max'):.4f}秒)")
                
                # 对数据进行清洗
                try:
                    cleaned_signal = self.data_processor.clean_signal(values)
                    
                    # 将清洗后的信号转换为列表并添加到处理结果中
                    if isinstance(cleaned_signal, np.ndarray):
                        cleaned_signal = cleaned_signal.tolist()
                    processed_signals.append(cleaned_signal)
                except Exception as e:
                    print(f"信号清洗失败: {e}")
                    # 如果清洗失败，使用原始数据
                    processed_signals.append(values)

                # 仅在第一次迭代时获取时间戳
                if i == 0:
                    time_stamps = times
            else:
                # 数据长度不足，直接使用原始数据
                if data:  # 确保有数据
                    times, values = zip(*data)
                    processed_signals.append(list(values))  # 确保转换为列表
                    if i == 0:
                        time_stamps = list(times)  # 确保转换为列表
                else:
                    # 如果没有数据，添加空列表
                    processed_signals.append([])
                    if i == 0:
                        time_stamps = []

        # 确保所有数据都是JSON可序列化的
        def ensure_serializable(obj):
            if isinstance(obj, list):
                return [ensure_serializable(item) for item in obj]
            elif hasattr(obj, 'tolist'):
                return obj.tolist()
            elif hasattr(obj, 'item'):
                return obj.item()  # 处理标量类型
            else:
                return obj
                
        # 对所有数据进行处理
        serializable_signals = ensure_serializable(processed_signals)
        serializable_timestamps = ensure_serializable(time_stamps)
        
        # 将处理后的数据发送到前端
        self.socketio.emit('ecg_data', {
            'leads': serializable_signals,  # 12个导联的列表
            'time_stamps': serializable_timestamps  # 时间戳列表
        })
        print(f"Data emitted to frontend with {len(serializable_signals[0]) if serializable_signals and serializable_signals[0] else 0} samples")
        
        # 存储数据到数据库
        try:
            if serializable_signals and serializable_signals[0] and serializable_timestamps:
                # 准备元数据
                metadata = {
                    'session_id': self.session_id,
                    'data_source_type': self.data_source_type or 'unknown',
                    'sampling_rate': 280,  # 默认采样率
                    'timestamp': datetime.now().isoformat()
                }
                
                # 如果有患者ID，添加到元数据中
                if self.patient_id:
                    metadata['patient_id'] = self.patient_id
                    
                # 存储到InfluxDB
                database_manager.store_ecg_data(
                    patient_id=self.patient_id or 'unknown',
                    leads_data=serializable_signals,
                    timestamps=serializable_timestamps,
                    metadata=metadata
                )
                
                # 每100次存储一次分析结果到MongoDB
                if self.sample_counter % 100 == 0 and self.patient_id:
                    # 这里可以添加信号分析结果的存储
                    pass
        except Exception as e:
            print(f"数据存储失败: {e}")

        # 保持累计数据的长度，防止内存占用过大
        max_length = self.max_samples * 10  # 保留最近的数据
        for i in range(12):
            if len(self.accumulated_data[i]) > max_length:
                self.accumulated_data[i] = self.accumulated_data[i][-max_length:]
