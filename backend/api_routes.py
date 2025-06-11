# api_routes.py

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
import jwt

# 导入服务
from .user_service import user_service
from .patient_service import patient_service
from .ecg_monitoring_system import ecg_system

# 创建Blueprint
api = Blueprint('api', __name__)

# 用户相关路由
@api.route('/auth/register', methods=['POST'])
def register():
    """注册新用户"""
    data = request.get_json()
    
    # 检查必要字段
    required_fields = ['username', 'email', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({'success': False, 'message': f'缺少必要字段: {field}'}), 400
    
    # 注册用户
    result = user_service.register_user(
        username=data['username'],
        email=data['email'],
        password=data['password'],
        role=data.get('role', 'user')
    )
    
    if result['success']:
        return jsonify(result), 201
    else:
        return jsonify(result), 400

@api.route('/auth/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    
    # 检查必要字段
    if 'username' not in data or 'password' not in data:
        return jsonify({'success': False, 'message': '缺少用户名或密码'}), 400
    
    # 登录
    result = user_service.login(
        username=data['username'],
        password=data['password']
    )
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 401

@api.route('/auth/logout', methods=['POST'])
@login_required
def logout():
    """用户登出"""
    result = user_service.logout()
    return jsonify(result), 200

@api.route('/users/profile', methods=['GET'])
@login_required
def get_profile():
    """获取当前用户资料"""
    result = user_service.get_user_profile(current_user.id)
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 404

@api.route('/users/profile', methods=['PUT'])
@login_required
def update_profile():
    """更新当前用户资料"""
    data = request.get_json()
    result = user_service.update_user_profile(current_user.id, data)
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 400

@api.route('/users/change-password', methods=['POST'])
@login_required
def change_password():
    """修改密码"""
    data = request.get_json()
    
    # 检查必要字段
    if 'current_password' not in data or 'new_password' not in data:
        return jsonify({'success': False, 'message': '缺少当前密码或新密码'}), 400
    
    result = user_service.change_password(
        user_id=current_user.id,
        current_password=data['current_password'],
        new_password=data['new_password']
    )
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 400

# 患者相关路由
@api.route('/patients', methods=['POST'])
@login_required
def create_patient():
    """创建新患者"""
    data = request.get_json()
    result = patient_service.create_patient(data)
    if result['success']:
        return jsonify(result), 201
    else:
        return jsonify(result), 400

@api.route('/patients/<patient_id>', methods=['GET'])
@login_required
def get_patient(patient_id):
    """获取患者信息"""
    result = patient_service.get_patient(patient_id)
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 404

@api.route('/patients/<patient_id>', methods=['PUT'])
@login_required
def update_patient(patient_id):
    """更新患者信息"""
    data = request.get_json()
    result = patient_service.update_patient(patient_id, data)
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 400

@api.route('/patients/<patient_id>', methods=['DELETE'])
@login_required
def delete_patient(patient_id):
    """删除患者"""
    result = patient_service.delete_patient(patient_id)
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 404

@api.route('/patients', methods=['GET'])
@login_required
def list_patients():
    """获取患者列表"""
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # 获取过滤条件
    filters = {}
    filter_fields = ['name', 'gender', 'min_age', 'max_age']
    for field in filter_fields:
        if field in request.args:
            filters[field] = request.args.get(field)
    
    result = patient_service.list_patients(page, per_page, filters)
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 400

@api.route('/patients/<patient_id>/medical-records', methods=['POST'])
@login_required
def add_medical_record(patient_id):
    """添加病历记录"""
    data = request.get_json()
    result = patient_service.add_medical_record(patient_id, data)
    if result['success']:
        return jsonify(result), 201
    else:
        return jsonify(result), 400

@api.route('/patients/<patient_id>/medical-records', methods=['GET'])
@login_required
def get_medical_records(patient_id):
    """获取患者病历记录"""
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    result = patient_service.get_medical_records(patient_id, page, per_page)
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 400

# ECG监控相关路由
@api.route('/monitoring/set-patient', methods=['POST'])
@login_required
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
    ecg_system.set_patient_id(data['patient_id'])
    
    return jsonify({
        'success': True,
        'message': '已设置监测患者',
        'patient': patient_result['patient']
    }), 200
