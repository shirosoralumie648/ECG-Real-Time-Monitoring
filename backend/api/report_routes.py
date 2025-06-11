# report_routes.py

from flask import Blueprint, request, jsonify, send_file
from ..services.report_service import report_service
import os

# 创建蓝图
report_bp = Blueprint('report', __name__)

@report_bp.route('/generate/<patient_id>', methods=['POST'])
def generate_report(patient_id):
    """
    生成ECG分析报告
    
    Args:
        patient_id: 患者ID
        
    Request Body:
        {
            "session_id": "会话ID",
            "time_range": ["开始时间", "结束时间"] (可选)
        }
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        time_range = data.get('time_range')
        
        # 生成报告
        result = report_service.generate_ecg_report(patient_id, session_id, time_range)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'报告生成失败: {str(e)}'
        }), 500

@report_bp.route('/get/<report_id>', methods=['GET'])
def get_report(report_id):
    """
    获取报告信息
    
    Args:
        report_id: 报告ID
    """
    try:
        result = report_service.get_report(report_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取报告失败: {str(e)}'
        }), 500

@report_bp.route('/download/<report_id>', methods=['GET'])
def download_report(report_id):
    """
    下载报告文件
    
    Args:
        report_id: 报告ID
    """
    try:
        # 获取报告信息
        result = report_service.get_report(report_id)
        if not result['success']:
            return jsonify(result), 404
        
        # 获取文件路径
        file_path = result['report'].get('file_path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'message': '报告文件不存在'
            }), 404
        
        # 返回文件
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"ECG_Report_{report_id}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'下载报告失败: {str(e)}'
        }), 500

@report_bp.route('/list/<patient_id>', methods=['GET'])
def list_patient_reports(patient_id):
    """
    列出患者的所有报告
    
    Args:
        patient_id: 患者ID
    """
    try:
        # 分页参数
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        skip = (page - 1) * limit
        
        # 查询该患者的所有报告
        from ..data.database_manager import database_manager
        reports = list(database_manager.mongodb_db.reports.find(
            {'patient_id': patient_id},
            {'_id': 0}
        ).sort('created_at', -1).skip(skip).limit(limit))
        
        # 统计总数
        total = database_manager.mongodb_db.reports.count_documents({'patient_id': patient_id})
        
        # 处理日期时间对象为字符串
        for report in reports:
            if 'created_at' in report and hasattr(report['created_at'], 'isoformat'):
                report['created_at'] = report['created_at'].isoformat()
        
        return jsonify({
            'success': True,
            'reports': reports,
            'total': total,
            'page': page,
            'limit': limit,
            'pages': (total + limit - 1) // limit
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取报告列表失败: {str(e)}'
        }), 500
