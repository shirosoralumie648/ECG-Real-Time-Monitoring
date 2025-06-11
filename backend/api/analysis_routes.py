# analysis_routes.py

from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user
import os
import io
import numpy as np
import matplotlib.pyplot as plt

# 导入服务
from ..processing.ecg_signal_analyzer import ECGSignalAnalyzer
from ..processing.ecg_data_processor import ECGDataProcessor
from ..config import get_config

config = get_config()

# 创建Blueprint
analysis_bp = Blueprint('analysis', __name__, url_prefix='/api/analysis')

@analysis_bp.route('/process-ecg', methods=['POST'])
# @login_required  # 暂时禁用登录要求
def process_ecg():
    """处理ECG数据"""
    file_name = request.json.get('file_name')

    if not file_name:
        return jsonify({'success': False, 'message': '未指定文件'}), 400

    file_path = os.path.join(config.FILE_DIRECTORY, file_name)

    # 读取文件数据
    try:
        ecg_data = np.load(file_path)
    except Exception as e:
        return jsonify({'success': False, 'message': f'文件读取失败: {str(e)}'}), 500

    # 处理ECG数据
    ecg_processor = ECGDataProcessor()
    cleaned_signal = ecg_processor.preprocessing(ecg_data)

    # 分析信号
    ecg_analyzer = ECGSignalAnalyzer()
    signals, info = ecg_analyzer.extract_features(cleaned_signal)
    plt.figure(figsize=(13, 7))

    try:
        import neurokit2 as nk
        nk.ecg_plot(signals, info)

        fig = plt.gcf()

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150)
        buf.seek(0)
        plt.close(fig)

        return send_file(buf, mimetype='image/png')
    except Exception as e:
        plt.close()
        return jsonify({'success': False, 'message': f'分析失败: {str(e)}'}), 500

@analysis_bp.route('/process-hrv', methods=['POST'])
# @login_required  # 暂时禁用登录要求
def process_hrv():
    """处理心率变异性"""
    file_name = request.json.get('file_name')

    if not file_name:
        return jsonify({'success': False, 'message': '未指定文件'}), 400

    file_path = os.path.join(config.FILE_DIRECTORY, file_name)

    # 读取文件数据
    try:
        ecg_data = np.load(file_path)
    except Exception as e:
        return jsonify({'success': False, 'message': f'文件读取失败: {str(e)}'}), 500

    # 处理ECG数据
    ecg_processor = ECGDataProcessor()
    cleaned_signal = ecg_processor.preprocessing(ecg_data)

    # 分析心率变异性
    ecg_analyzer = ECGSignalAnalyzer()
    hrv_metrics = ecg_analyzer.analyze_hrv(cleaned_signal)

    try:
        # 创建图表
        plt.figure(figsize=(13, 7))
        ecg_analyzer.plot_hrv(hrv_metrics)

        fig = plt.gcf()

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150)
        buf.seek(0)
        plt.close(fig)

        return send_file(buf, mimetype='image/png')
    except Exception as e:
        plt.close()
        return jsonify({'success': False, 'message': f'分析失败: {str(e)}'}), 500

@analysis_bp.route('/process-edr', methods=['POST'])
# @login_required  # 暂时禁用登录要求
def process_edr():
    """处理ECG导出呼吸"""
    file_name = request.json.get('file_name')

    if not file_name:
        return jsonify({'success': False, 'message': '未指定文件'}), 400

    file_path = os.path.join(config.FILE_DIRECTORY, file_name)

    # 读取文件数据
    try:
        ecg_data = np.load(file_path)
    except Exception as e:
        return jsonify({'success': False, 'message': f'文件读取失败: {str(e)}'}), 500

    # 处理ECG数据
    ecg_processor = ECGDataProcessor()
    cleaned_signal = ecg_processor.preprocessing(ecg_data)

    # 分析ECG导出呼吸
    ecg_analyzer = ECGSignalAnalyzer()
    edr = ecg_analyzer.analyze_edr(cleaned_signal)

    try:
        # 创建图表
        import neurokit2 as nk
        nk.signal_plot(edr)

        fig = plt.gcf()

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150)
        buf.seek(0)
        plt.close(fig)

        return send_file(buf, mimetype='image/png')
    except Exception as e:
        plt.close()
        return jsonify({'success': False, 'message': f'分析失败: {str(e)}'}), 500

@analysis_bp.route('/analyze', methods=['POST'])
# @login_required  # 暂时禁用登录要求
def analyze():
    """分析ECG数据"""
    action = request.json.get('action')
    
    if not action:
        return jsonify({'success': False, 'message': '未指定分析操作'}), 400
    
    try:
        # 根据不同的分析操作执行不同的分析
        if action == 'basic':
            result = '基本ECG分析结果'
        elif action == 'hrv':
            result = '心率变异性分析结果'
        elif action == 'edr':
            result = 'ECG导出呼吸分析结果'
        else:
            return jsonify({'success': False, 'message': f'不支持的分析操作: {action}'}), 400
        
        return jsonify({'success': True, 'result': result}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'分析失败: {str(e)}'}), 500
