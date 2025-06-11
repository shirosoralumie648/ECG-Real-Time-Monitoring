# device_routes.py

from flask import Blueprint, jsonify, request
from flask_login import login_required
import serial.tools.list_ports
import os
import subprocess
import json
import platform

# 导入设备服务
from ..services.device_service import device_service

# 创建Blueprint
device_bp = Blueprint('device', __name__)

@device_bp.route('/serial-ports', methods=['GET'])
# @login_required  # 暂时禁用登录要求
def get_serial_ports():
    """获取可用串口列表"""
    try:
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'device': port.device,
                'description': port.description,
                'hwid': port.hwid,
                'manufacturer': port.manufacturer if hasattr(port, 'manufacturer') else None
            })
        
        return jsonify({
            'success': True,
            'ports': ports
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取串口列表失败: {str(e)}'
        }), 500

@device_bp.route('/connect/serial', methods=['POST'])
# @login_required  # 暂时禁用登录要求
def connect_serial_device():
    """连接串口设备"""
    try:
        data = request.get_json()
        if not data or 'port' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必要参数: port'
            }), 400
        
        port = data['port']
        baudrate = data.get('baudrate', 921600)  # 默认波特率
        timeout = data.get('timeout', 1)  # 默认超时时间
        
        result = device_service.connect_serial(port, baudrate, timeout)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'连接串口设备失败: {str(e)}'
        }), 500

@device_bp.route('/connect/udp', methods=['POST'])
# @login_required  # 暂时禁用登录要求
def connect_udp_device():
    """连接UDP设备"""
    try:
        data = request.get_json()
        host = data.get('host', '0.0.0.0')  # 默认监听所有接口
        port = data.get('port', 8888)  # 默认端口
        
        if not port:
            return jsonify({
                'success': False,
                'message': '缺少必要参数: port'
            }), 400
        
        result = device_service.connect_udp(host, port)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'连接UDP设备失败: {str(e)}'
        }), 500

@device_bp.route('/connect/bluetooth', methods=['POST'])
# @login_required  # 暂时禁用登录要求
def connect_bluetooth_device():
    """连接蓝牙设备"""
    try:
        data = request.get_json()
        if not data or 'device_address' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必要参数: device_address'
            }), 400
        
        device_address = data['device_address']
        
        result = device_service.connect_bluetooth(device_address)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'连接蓝牙设备失败: {str(e)}'
        }), 500

@device_bp.route('/disconnect', methods=['POST'])
# @login_required  # 暂时禁用登录要求
def disconnect_device():
    """断开当前设备连接"""
    try:
        result = device_service.disconnect()
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'断开设备连接失败: {str(e)}'
        }), 500

@device_bp.route('/status', methods=['GET'])
# @login_required  # 暂时禁用登录要求
def get_device_status():
    """获取设备连接状态"""
    try:
        result = device_service.get_connection_status()
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取设备状态失败: {str(e)}'
        }), 500

@device_bp.route('/bluetooth-devices', methods=['GET'])
# @login_required  # 暂时禁用登录要求
def get_bluetooth_devices():
    """获取可用蓝牙设备列表"""
    try:
        # 根据操作系统调用不同的方法获取蓝牙设备列表
        system = platform.system()
        devices = []
        
        if system == 'Linux':
            devices = get_bluetooth_devices_linux()
        elif system == 'Windows':
            devices = get_bluetooth_devices_windows()
        elif system == 'Darwin':  # macOS
            devices = []  # 需要实现macOS蓝牙设备扫描
        
        return jsonify({
            'success': True,
            'devices': devices
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取蓝牙设备列表失败: {str(e)}'
        }), 500

def get_bluetooth_devices_linux():
    """在Linux系统上获取蓝牙设备列表"""
    try:
        # 使用bluetoothctl命令获取设备列表
        result = subprocess.run(
            ['bluetoothctl', 'devices'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            devices = []
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip():
                    # 解析设备信息，格式通常为: "Device XX:XX:XX:XX:XX:XX DeviceName"
                    parts = line.strip().split(' ', 2)
                    if len(parts) >= 3 and parts[0] == 'Device':
                        devices.append({
                            'address': parts[1],
                            'name': parts[2] if len(parts) > 2 else 'Unknown Device'
                        })
            return devices
        else:
            return []
    except Exception as e:
        print(f"获取蓝牙设备失败: {str(e)}")
        return []

def get_bluetooth_devices_windows():
    """在Windows系统上获取蓝牙设备列表"""
    try:
        # 使用PowerShell获取蓝牙设备列表
        result = subprocess.run(
            ['powershell', '-Command', "Get-PnpDevice -Class Bluetooth | ConvertTo-Json"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            devices = []
            try:
                device_list = json.loads(result.stdout)
                # 处理返回的是单个设备而非列表的情况
                if not isinstance(device_list, list):
                    device_list = [device_list]
                    
                for device in device_list:
                    if 'FriendlyName' in device and 'DeviceID' in device:
                        devices.append({
                            'address': device['DeviceID'],
                            'name': device['FriendlyName']
                        })
                return devices
            except json.JSONDecodeError:
                return []
        else:
            return []
    except Exception as e:
        print(f"获取蓝牙设备失败: {str(e)}")
        return []
