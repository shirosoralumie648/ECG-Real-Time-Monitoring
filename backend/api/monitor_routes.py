# monitor_routes.py

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

# 导入服务
from ..services.patient_service import patient_service
from ..services.ecg_manager import get_ecg_system

# 创建Blueprint
monitor_bp = Blueprint('monitor', __name__)

@monitor_bp.route('/connect', methods=['POST'])
# @login_required  # 暂时禁用登录要求
def connect():
    """连接数据源"""
    data = request.get_json()
    source_type = data.get('source_type')
    
    try:
        if source_type == 'serial':
            port = data.get('port', 'COM7')
            baudrate = int(data.get('baudrate', 921600))
            get_ecg_system().connect_serial(port=port, baudrate=baudrate)
            return jsonify({
                'success': True,
                'message': f'已连接到串口 {port}，波特率 {baudrate}',
                'type': 'serial',
                'port': port,
                'baudrate': baudrate
            })
        
        elif source_type == 'udp':
            local_ip = data.get('local_ip', '0.0.0.0')
            local_port = int(data.get('local_port', 5001))
            remote_ip = data.get('remote_ip')
            remote_port = int(data.get('remote_port')) if data.get('remote_port') else None
            
            get_ecg_system().connect_udp(
                local_ip=local_ip,
                local_port=local_port,
                remote_ip=remote_ip,
                remote_port=remote_port
            )
            
            return jsonify({
                'success': True,
                'message': f'已连接到UDP {local_ip}:{local_port}',
                'type': 'udp',
                'local_ip': local_ip,
                'local_port': local_port,
                'remote_ip': remote_ip,
                'remote_port': remote_port
            })
        
        elif source_type == 'bluetooth':
            port = data.get('port')
            baudrate = int(data.get('baudrate', 921600))
            
            if not port:
                return jsonify({
                    'success': False,
                    'message': '缺少蓝牙设备端口'
                }), 400
            
            get_ecg_system().connect_bluetooth(port=port, baudrate=baudrate)
            
            return jsonify({
                'success': True,
                'message': f'已连接到蓝牙设备 {port}，波特率 {baudrate}',
                'type': 'bluetooth',
                'port': port,
                'baudrate': baudrate
            })
        
        elif source_type == 'file':
            file_name = data.get('file_name')
            
            if not file_name:
                return jsonify({
                    'success': False,
                    'message': '缺少文件名'
                }), 400
            
            get_ecg_system().connect_file(file_name=file_name)
            
            return jsonify({
                'success': True,
                'message': f'已连接到文件 {file_name}',
                'type': 'file',
                'file_name': file_name
            })
        
        else:
            return jsonify({
                'success': False,
                'message': f'不支持的数据源类型: {source_type}'
            }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'连接失败: {str(e)}'
        }), 500

@monitor_bp.route('/disconnect', methods=['POST'])
# @login_required  # 暂时禁用登录要求
def disconnect():
    """断开数据源连接"""
    try:
        get_ecg_system().disconnect()
        return jsonify({
            'success': True,
            'message': '已断开连接'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'断开连接失败: {str(e)}'
        }), 500

@monitor_bp.route('/start', methods=['POST'])
# @login_required  # 暂时禁用登录要求
def start():
    """开始监测"""
    data = request.get_json()
    speed = float(data.get('speed', 1.0))
    
    try:
        get_ecg_system().start_monitoring(speed=speed)
        return jsonify({
            'success': True,
            'message': '开始监测',
            'speed': speed
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'开始监测失败: {str(e)}'
        }), 500

@monitor_bp.route('/stop', methods=['POST'])
# @login_required  # 暂时禁用登录要求
def stop():
    """停止监测"""
    try:
        get_ecg_system().stop()
        return jsonify({
            'success': True,
            'message': '停止监测'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'停止监测失败: {str(e)}'
        }), 500

@monitor_bp.route('/set-patient', methods=['POST'])
# @login_required  # 暂时禁用登录要求
def set_monitoring_patient():
    """设置当前监测的患者"""
    data = request.get_json()
    
    # 检查必要字段
    if 'patient_id' not in data:
        return jsonify({'success': False, 'message': '缺少患者ID'}), 400
    
    # 检查患者是否存在
    patient_result = patient_service.get_patient(data['patient_id'])
    if not patient_result['success']:
        return jsonify({'success': False, 'message': '患者不存在'}), 404
    
    # 设置患者ID
    get_ecg_system().set_patient_id(data['patient_id'])
    
    return jsonify({
        'success': True,
        'message': '已设置监测患者',
        'patient': patient_result['patient']
    }), 200
