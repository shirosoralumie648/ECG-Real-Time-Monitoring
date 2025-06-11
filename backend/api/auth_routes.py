# auth_routes.py

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

# 导入服务
from ..services.user_service import user_service

# 创建Blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
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

@auth_bp.route('/login', methods=['POST'])
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

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """用户登出"""
    result = user_service.logout()
    return jsonify(result), 200

@auth_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """获取当前用户资料"""
    result = user_service.get_user_profile(current_user.id)
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 404

@auth_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """更新当前用户资料"""
    data = request.get_json()
    result = user_service.update_user_profile(current_user.id, data)
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 400

@auth_bp.route('/change-password', methods=['POST'])
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
