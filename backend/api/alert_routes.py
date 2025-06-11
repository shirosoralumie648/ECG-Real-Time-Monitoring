# alert_routes.py

from flask import Blueprint, request, jsonify
from flask_login import login_required

# 导入报警服务
from ..services.alert_service import get_alert_service

# 创建蓝图
alert_bp = Blueprint('alert', __name__)

@alert_bp.route('/thresholds', methods=['GET'])
def get_thresholds():
    """
    获取报警阈值设置
    """
    try:
        alert_service = get_alert_service()
        if not alert_service:
            return jsonify({
                'success': False,
                'message': '报警服务未初始化'
            }), 500
        
        result = alert_service.get_thresholds()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取报警阈值失败: {str(e)}'
        }), 500

@alert_bp.route('/thresholds', methods=['POST'])
def set_threshold():
    """
    设置报警阈值
    """
    try:
        data = request.get_json()
        threshold_name = data.get('name')
        value = data.get('value')
        
        if not threshold_name or value is None:
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400
        
        alert_service = get_alert_service()
        if not alert_service:
            return jsonify({
                'success': False,
                'message': '报警服务未初始化'
            }), 500
        
        result = alert_service.set_threshold(threshold_name, float(value))
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'设置报警阈值失败: {str(e)}'
        }), 500

@alert_bp.route('/patient/<patient_id>', methods=['GET'])
def get_patient_alerts(patient_id):
    """
    获取患者的报警历史
    """
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        severity = request.args.get('severity')
        
        alert_service = get_alert_service()
        if not alert_service:
            return jsonify({
                'success': False,
                'message': '报警服务未初始化'
            }), 500
        
        result = alert_service.get_patient_alerts(patient_id, limit, (page-1)*limit, severity)
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取报警历史失败: {str(e)}'
        }), 500

@alert_bp.route('/start', methods=['POST'])
def start_monitoring():
    """
    启动报警监控
    """
    try:
        alert_service = get_alert_service()
        if not alert_service:
            return jsonify({
                'success': False,
                'message': '报警服务未初始化'
            }), 500
        
        result = alert_service.start_monitoring()
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'启动报警监控失败: {str(e)}'
        }), 500

@alert_bp.route('/stop', methods=['POST'])
def stop_monitoring():
    """
    停止报警监控
    """
    try:
        alert_service = get_alert_service()
        if not alert_service:
            return jsonify({
                'success': False,
                'message': '报警服务未初始化'
            }), 500
        
        result = alert_service.stop_monitoring()
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'停止报警监控失败: {str(e)}'
        }), 500
