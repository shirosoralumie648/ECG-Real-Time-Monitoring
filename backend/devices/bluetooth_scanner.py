# bluetooth_scanner.py
# 用于扫描和连接蓝牙设备

import platform
import time
import threading
import os
import sys
import serial

# 检查操作系统类型并导入相应的蓝牙库
system = platform.system()

# 全局变量，存储已发现的蓝牙设备
discovered_devices = []
scanning_lock = threading.Lock()
is_scanning = False
scan_thread = None

# 蓝牙设备类
class BluetoothDevice:
    def __init__(self, address, name, rssi=None):
        self.address = address
        self.name = name if name else "未命名设备"
        self.rssi = rssi
        self.serial_port = None  # 连接后的串口对象
        
    def __str__(self):
        return f"{self.name} ({self.address})"
        
    def to_dict(self):
        return {
            "address": self.address,
            "name": self.name,
            "rssi": self.rssi
        }

# 初始化蓝牙模块
def init_bluetooth():
    global system
    
    try:
        if system == 'Linux':
            # 检查是否安装了必要的软件包
            if os.system('which bluetoothctl > /dev/null') != 0:
                print("警告: 未找到bluetoothctl，请安装bluez软件包")
                return False
                
            # 检查蓝牙服务是否运行
            if os.system('systemctl is-active --quiet bluetooth') != 0:
                print("警告: 蓝牙服务未运行")
                return False
                
            return True
            
        elif system == 'Windows':
            try:
                # 尝试导入Windows蓝牙库
                import bluetooth
                return True
            except ImportError:
                print("警告: 未找到PyBluez库，请安装: pip install pybluez")
                return False
                
        elif system == 'Darwin':  # macOS
            # macOS蓝牙支持需要特殊处理
            print("警告: macOS蓝牙支持有限")
            return False
            
        else:
            print(f"不支持的操作系统: {system}")
            return False
            
    except Exception as e:
        print(f"初始化蓝牙模块时出错: {e}")
        return False

# 开始扫描蓝牙设备
def start_scan():
    global discovered_devices, is_scanning, scan_thread
    
    with scanning_lock:
        if is_scanning:
            return False
        
        is_scanning = True
        discovered_devices = []
    
    # 创建扫描线程
    scan_thread = threading.Thread(target=_scan_worker)
    scan_thread.daemon = True
    scan_thread.start()
    
    return True

# 停止扫描
def stop_scan():
    global is_scanning
    
    with scanning_lock:
        is_scanning = False
    
    if scan_thread:
        scan_thread.join(timeout=2.0)
    
    return True

# 扫描工作线程
def _scan_worker():
    global discovered_devices, is_scanning, system
    
    try:
        if system == 'Linux':
            _scan_linux()
        elif system == 'Windows':
            _scan_windows()
        else:
            # 不支持的系统，生成一些模拟数据
            _scan_mock()
    except Exception as e:
        print(f"扫描蓝牙设备时出错: {e}")
    finally:
        with scanning_lock:
            is_scanning = False

# Linux系统上的蓝牙扫描
def _scan_linux():
    global discovered_devices, is_scanning
    
    # 使用bluetoothctl扫描设备
    os.system('bluetoothctl scan on &')
    
    # 扫描5秒
    scan_time = 0
    while is_scanning and scan_time < 5:
        # 获取设备列表
        import subprocess
        output = subprocess.check_output(['bluetoothctl', 'devices']).decode('utf-8')
        
        # 解析输出
        for line in output.splitlines():
            if line.startswith('Device '):
                parts = line.split(' ', 2)
                if len(parts) >= 3:
                    address = parts[1]
                    name = parts[2]
                    
                    # 检查是否已添加该设备
                    if not any(d.address == address for d in discovered_devices):
                        device = BluetoothDevice(address, name)
                        discovered_devices.append(device)
        
        time.sleep(1)
        scan_time += 1
    
    # 停止扫描
    os.system('bluetoothctl scan off')

# Windows系统上的蓝牙扫描
def _scan_windows():
    global discovered_devices, is_scanning
    
    try:
        import bluetooth
        
        # 使用PyBluez扫描设备
        devices = bluetooth.discover_devices(duration=5, lookup_names=True)
        
        for addr, name in devices:
            device = BluetoothDevice(addr, name)
            discovered_devices.append(device)
            
    except ImportError:
        print("未找到PyBluez库，使用模拟数据")
        _scan_mock()

# 模拟蓝牙扫描（用于不支持的系统或测试）
def _scan_mock():
    global discovered_devices, is_scanning
    
    # 模拟扫描延迟
    time.sleep(2)
    
    # 添加一些模拟设备
    mock_devices = [
        ("00:11:22:33:44:55", "模拟心电设备 (115200)"),
        ("AA:BB:CC:DD:EE:FF", "ECG Monitor (9600)"),
        ("12:34:56:78:90:AB", "BT Health Device (38400)")
    ]
    
    for addr, name in mock_devices:
        device = BluetoothDevice(addr, name)
        discovered_devices.append(device)

# 获取已发现的设备列表
def get_discovered_devices():
    return [device.to_dict() for device in discovered_devices]

# 连接到蓝牙设备并创建串口
def connect_device(address):
    global discovered_devices, system
    
    # 查找设备
    device = next((d for d in discovered_devices if d.address == address), None)
    if not device:
        return None, "设备未找到"
    
    try:
        # 关闭模拟模式，使用真实蓝牙连接
        use_mock = False
        
        if use_mock:
            # 模拟模式，返回一个虚拟串口
            print(f"模拟模式: 连接到蓝牙设备 {device.name} ({device.address})")
            
            # 根据设备名称选择合适的波特率
            suggested_baudrate = 921600  # 默认使用高波特率
            # 如果设备名称中包含特定波特率信息，则使用该波特率
            if "9600" in device.name:
                suggested_baudrate = 9600
            elif "38400" in device.name:
                suggested_baudrate = 38400
            elif "115200" in device.name:
                suggested_baudrate = 115200
            
            print(f"建议使用波特率: {suggested_baudrate}")
            
            # 返回一个已知存在的串口名称
            if system == 'Linux':
                # 在Linux上尝试使用实际的串口
                mock_ports = ["/dev/ttyS0", "/dev/ttyUSB0", "/dev/ttyACM0"]
                for tty in mock_ports:
                    if os.path.exists(tty):
                        try:
                            # 尝试打开串口测试是否可用
                            test_ser = serial.Serial(tty, suggested_baudrate, timeout=0.1)
                            test_ser.close()
                            return tty, None
                        except:
                            continue
                
                # 如果没有找到实际可用的串口，返回一个模拟串口
                return "/dev/null", None
            else:
                # Windows系统
                return "COM1", None
        
        if system == 'Linux':
            # 在Linux上，使用rfcomm连接蓝牙设备
            import subprocess
            
            # 检查rfcomm命令是否可用
            try:
                subprocess.check_call("which rfcomm", shell=True)
            except subprocess.CalledProcessError:
                return None, "rfcomm命令不可用，请安装bluez包"
            
            # 检查用户权限
            try:
                # 尝试创建一个测试文件在/dev目录
                test_cmd = "touch /dev/test_bluetooth_perm && rm /dev/test_bluetooth_perm"
                subprocess.check_call(test_cmd, shell=True)
            except subprocess.CalledProcessError:
                return None, "没有足够的权限访问/dev目录，请使用sudo运行程序"
            
            # 查找可用的rfcomm设备号 - 增加搜索范围到20个设备
            for i in range(20):
                rfcomm_dev = f"/dev/rfcomm{i}"
                if not os.path.exists(rfcomm_dev):
                    try:
                        # 先释放可能存在的绑定
                        try:
                            subprocess.call(f"rfcomm release {i}", shell=True, stderr=subprocess.DEVNULL)
                        except:
                            pass
                        
                        # 绑定蓝牙设备到rfcomm端口
                        cmd = f"rfcomm bind {i} {address}"
                        subprocess.check_call(cmd, shell=True)
                        
                        # 等待设备文件创建
                        timeout = 5  # 等待5秒
                        while timeout > 0 and not os.path.exists(rfcomm_dev):
                            time.sleep(0.5)
                            timeout -= 0.5
                        
                        if not os.path.exists(rfcomm_dev):
                            return None, f"创建{rfcomm_dev}超时"
                        
                        # 设置文件权限
                        try:
                            subprocess.check_call(f"sudo chmod 666 {rfcomm_dev}", shell=True)
                        except:
                            pass
                        
                        # 尝试打开串口，使用高波特率
                        try:
                            ser = serial.Serial(rfcomm_dev, 921600, timeout=1)
                            device.serial_port = ser
                            return rfcomm_dev, None
                        except Exception as e:
                            # 解绑端口
                            subprocess.call(f"rfcomm release {i}", shell=True)
                            return None, f"无法打开串口: {e}"
                    except subprocess.CalledProcessError as e:
                        return None, f"rfcomm命令失败: {e}"
            
            # 尝试创建新的rfcomm设备
            try:
                # 尝试直接使用rfcomm0，强制释放并重新绑定
                rfcomm_dev = "/dev/rfcomm0"
                subprocess.call("rfcomm release 0", shell=True, stderr=subprocess.DEVNULL)
                cmd = f"rfcomm bind 0 {address}"
                subprocess.check_call(cmd, shell=True)
                
                # 等待设备文件创建
                timeout = 5  # 等待5秒
                while timeout > 0 and not os.path.exists(rfcomm_dev):
                    time.sleep(0.5)
                    timeout -= 0.5
                
                if not os.path.exists(rfcomm_dev):
                    return None, f"创建{rfcomm_dev}超时"
                
                # 设置文件权限
                try:
                    subprocess.check_call(f"sudo chmod 666 {rfcomm_dev}", shell=True)
                except:
                    pass
                
                # 尝试打开串口
                try:
                    ser = serial.Serial(rfcomm_dev, 921600, timeout=1)
                    device.serial_port = ser
                    return rfcomm_dev, None
                except Exception as e:
                    # 解绑端口
                    subprocess.call(f"rfcomm release 0", shell=True)
                    return None, f"无法打开串口: {e}"
            except Exception as e:
                return None, f"创建rfcomm设备失败: {e}"
            
        elif system == 'Windows':
            # 在Windows上，蓝牙设备通常会映射为COM端口
            # 这里需要用户手动指定COM端口
            return f"COM1", "在Windows上，请手动选择蓝牙设备对应的COM端口"
            
        else:
            return None, f"不支持的操作系统: {system}"
            
    except Exception as e:
        return None, f"连接蓝牙设备时出错: {e}"

# 断开蓝牙设备连接
def disconnect_device(address):
    global discovered_devices, system
    
    # 查找设备
    device = next((d for d in discovered_devices if d.address == address), None)
    if not device:
        return False, "设备未找到"
    
    try:
        # 关闭串口连接
        if device.serial_port:
            device.serial_port.close()
            device.serial_port = None
        
        if system == 'Linux':
            # 在Linux上，解绑rfcomm设备
            import subprocess
            
            # 增加搜索范围到20个设备
            for i in range(20):
                rfcomm_dev = f"/dev/rfcomm{i}"
                if os.path.exists(rfcomm_dev):
                    # 检查是否是我们的设备
                    try:
                        output = subprocess.check_output(['rfcomm', 'show', str(i)]).decode('utf-8')
                        if address in output:
                            print(f"释放rfcomm{i}设备")
                            subprocess.call(f"rfcomm release {i}", shell=True)
                            # 不要立即返回，继续检查其他可能的映射
                    except Exception as e:
                        print(f"检查rfcomm{i}时出错: {e}")
                        # 尝试强制释放
                        try:
                            subprocess.call(f"rfcomm release {i}", shell=True, stderr=subprocess.DEVNULL)
                        except:
                            pass
        
        return True, None
            
    except Exception as e:
        return False, f"断开蓝牙设备连接时出错: {e}"

# 测试代码
if __name__ == "__main__":
    print(f"当前操作系统: {system}")
    
    if init_bluetooth():
        print("蓝牙模块初始化成功")
        
        print("开始扫描蓝牙设备...")
        start_scan()
        
        # 等待扫描完成
        time.sleep(6)
        
        print("发现的设备:")
        for i, device in enumerate(discovered_devices):
            print(f"{i+1}. {device}")
            
        if discovered_devices:
            # 尝试连接第一个设备
            device = discovered_devices[0]
            print(f"尝试连接到 {device}...")
            
            port, error = connect_device(device.address)
            if port:
                print(f"连接成功，串口: {port}")
                
                # 断开连接
                disconnect_device(device.address)
                print("已断开连接")
            else:
                print(f"连接失败: {error}")
    else:
        print("蓝牙模块初始化失败")
