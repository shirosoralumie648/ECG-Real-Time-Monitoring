# port_scanner.py
# 用于扫描系统上可用的串口

import sys
import glob
import serial
import platform

def scan_ports():
    """
    扫描系统上可用的串口
    
    返回:
        list: 可用串口列表
    """
    available_ports = []
    system = platform.system()
    
    try:
        if system == 'Windows':
            # Windows系统上扫描串口
            for i in range(256):
                port = f'COM{i}'
                try:
                    s = serial.Serial(port)
                    s.close()
                    available_ports.append(port)
                except (OSError, serial.SerialException):
                    pass
                    
        elif system == 'Linux' or system == 'Darwin':  # Linux或macOS
            # Linux系统上扫描串口
            ports = glob.glob('/dev/tty[A-Za-z]*')
            for port in ports:
                try:
                    s = serial.Serial(port)
                    s.close()
                    available_ports.append(port)
                except (OSError, serial.SerialException):
                    pass
        
        # 如果没有找到任何串口，添加一些常见的串口作为备选
        if not available_ports:
            if system == 'Windows':
                available_ports = ['COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7']
            else:
                available_ports = ['/dev/ttyUSB0', '/dev/ttyACM0', '/dev/ttyS0']
    
    except Exception as e:
        print(f"扫描串口时出错: {e}")
        # 添加一些默认值
        if system == 'Windows':
            available_ports = ['COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7']
        else:
            available_ports = ['/dev/ttyUSB0', '/dev/ttyACM0', '/dev/ttyS0']
    
    return available_ports

if __name__ == '__main__':
    # 测试扫描功能
    ports = scan_ports()
    print(f"可用串口: {ports}")
