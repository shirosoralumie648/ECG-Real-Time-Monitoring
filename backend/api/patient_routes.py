# patient_routes.py

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

# 导入服务
from ..services.patient_service import patient_service

# 创建Blueprint
patient_bp = Blueprint('patient', __name__)

@patient_bp.route('', methods=['POST'])
# @login_required  # 暂时禁用登录要求
def create_patient():
    """创建新患者"""
    data = request.get_json()
    result = patient_service.create_patient(data)
    if result['success']:
        return jsonify(result), 201
    else:
        return jsonify(result), 400

@patient_bp.route('/<patient_id>', methods=['GET'])
# @login_required  # 暂时禁用登录要求
def get_patient(patient_id):
    """获取患者信息"""
    result = patient_service.get_patient(patient_id)
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 404

@patient_bp.route('/<patient_id>', methods=['PUT'])
# @login_required  # 暂时禁用登录要求
def update_patient(patient_id):
    """更新患者信息"""
    data = request.get_json()
    result = patient_service.update_patient(patient_id, data)
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 400

@patient_bp.route('/<patient_id>', methods=['DELETE'])
# @login_required  # 暂时禁用登录要求
def delete_patient(patient_id):
    """删除患者"""
    result = patient_service.delete_patient(patient_id)
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 404

@patient_bp.route('', methods=['GET'])
# @login_required  # 暂时禁用登录要求
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

@patient_bp.route('/<patient_id>/medical-records', methods=['POST'])
# @login_required  # 暂时禁用登录要求
def add_medical_record(patient_id):
    """添加病历记录"""
    data = request.get_json()
    result = patient_service.add_medical_record(patient_id, data)
    if result['success']:
        return jsonify(result), 201
    else:
        return jsonify(result), 400

@patient_bp.route('/<patient_id>/medical-records', methods=['GET'])
# @login_required  # 暂时禁用登录要求
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
