# file_routes.py - 文件操作相关的API路由

import os
import json
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required

# 创建蓝图
file_bp = Blueprint('file', __name__, url_prefix='/api/files')

@file_bp.route('', methods=['GET'])
# @login_required  # 暂时禁用登录要求
def get_files():
    """获取可用的ECG数据文件列表"""
    try:
        # 获取数据目录
        data_dir = os.path.join(current_app.root_path, '..', 'data')
        
        # 确保目录存在
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        # 获取所有JSON文件
        files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
        
        return jsonify(files)
    except Exception as e:
        current_app.logger.error(f"获取文件列表出错: {str(e)}")
        return jsonify([])

@file_bp.route('/<filename>', methods=['GET'])
# @login_required  # 暂时禁用登录要求
def get_file(filename):
    """获取指定文件的内容"""
    try:
        # 获取数据目录
        data_dir = os.path.join(current_app.root_path, '..', 'data')
        file_path = os.path.join(data_dir, filename)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': f'文件 {filename} 不存在'}), 404
        
        # 读取文件内容
        with open(file_path, 'r') as f:
            content = json.load(f)
        
        return jsonify(content)
    except Exception as e:
        current_app.logger.error(f"获取文件内容出错: {str(e)}")
        return jsonify({'success': False, 'message': f'获取文件内容出错: {str(e)}'}), 500
