# web_server.py

import eventlet
import numpy as np
from matplotlib import pyplot as plt


from .ecg_data_processor import ECGDataProcessor
from .ecg_signal_analyzer import ECGSignalAnalyzer
from .respiration_processor import RespirationProcessor
from .respiration_monitoring_system import RespirationMonitoringSystem

eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify,send_file
from flask_socketio import SocketIO
import time  # 引入time模块用于时间戳
import os
import io
import neurokit2 as nk


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet', ping_timeout=20, ping_interval=10)


from .ecg_monitoring_system import ECGMonitoringSystem

ecg_system = ECGMonitoringSystem(socketio)
# 初始化呼吸监测系统，设置UDP接收端口为1347
respiration_system = RespirationMonitoringSystem(socketio, host='127.0.0.1', port=1347)


FILE_DIRECTORY = '.'


@app.route('/process_edr', methods=['POST'])
def process_edr():
    file_name = request.json.get('file_name')

    if not file_name:
        return "No file specified", 400

    file_path = os.path.join(FILE_DIRECTORY, file_name)

    # 读取文件数据
    ecg_data = np.load(file_path)

    # 导联I的ECG数据
    ecg_processor = ECGDataProcessor()
    cleaned_signal = ecg_processor.preprocessing(ecg_data)

    # 使用ECGSignalAnalyzer分析信号
    ecg_analyzer = ECGSignalAnalyzer()
    edr = ecg_analyzer.analyze_edr(cleaned_signal)

    nk.signal_plot(edr)

    fig = plt.gcf()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)

    return send_file(buf, mimetype='image/png')


@app.route('/process_ecg', methods=['POST'])
def process_ecg():
    file_name = request.json.get('file_name')

    if not file_name:
        return "No file specified", 400

    file_path = os.path.join(FILE_DIRECTORY, file_name)

    # 读取文件数据
    ecg_data = np.load(file_path)

    # 导联I的ECG数据
    ecg_processor = ECGDataProcessor()
    cleaned_signal = ecg_processor.preprocessing(ecg_data)

    # 使用ECGSignalAnalyzer分析信号
    ecg_analyzer = ECGSignalAnalyzer()
    signals, info = ecg_analyzer.extract_features(cleaned_signal)
    plt.figure(figsize=(13, 7))

    nk.ecg_plot(signals, info)

    fig = plt.gcf()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)

    return send_file(buf, mimetype='image/png')

@app.route('/process_hrv', methods=['POST'])
def process_hrv():
    file_name = request.json.get('file_name')

    if not file_name:
        return "No file specified", 400

    file_path = os.path.join(FILE_DIRECTORY, file_name)

    # 读取文件数据
    ecg_data = np.load(file_path)

    # 导联I的ECG数据
    ecg_processor = ECGDataProcessor()
    cleaned_signal = ecg_processor.preprocessing(ecg_data)

    # 使用ECGSignalAnalyzer分析信号
    ecg_analyzer = ECGSignalAnalyzer()
    hrv_metrics = ecg_analyzer.analyze_hrv(cleaned_signal)
    hrv_metrics
    #print(hrv_metrics)
    #plt.figure(figsize=(13, 7))
    #ecg_analyzer.plot_hrv(hrv_metrics)

    fig = plt.gcf()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)

    return send_file(buf, mimetype='image/png')


@app.route('/get_files', methods=['GET'])
def get_files():
    files = [f for f in os.listdir(FILE_DIRECTORY) if f.startswith('lead_0')]
    return jsonify(files)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    print("Received /start request")
    ecg_system.start()
    # 同时启动呼吸监测系统
    respiration_system.start()
    return jsonify({'status': 'started'}), 200

@app.route('/stop', methods=['POST'])
def stop():
    print("Received /stop request")
    ecg_system.stop()
    # 同时停止呼吸监测系统
    respiration_system.stop()
    return jsonify({'status': 'stopped'})

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    analysis_type = data.get('action')
    ecg_signal = ecg_system.accumulated_data[1]  # 以导联II为例
    if len(ecg_signal) < 500:  # 确保有足够的数据进行分析
        return jsonify({'result': '数据不足，无法进行分析'})
    if analysis_type == 'ecg_features':
        signals, info = ecg_system.data_processor.extract_features(ecg_signal)
        result = generate_analysis_result(signals, info)
    elif analysis_type == 'heart_rate':
        hrv_metrics = ecg_system.data_processor.analyze_heart_rate(ecg_signal)
        result = hrv_metrics.to_html()
    elif analysis_type == 'clinical_indices':
        clinical_indices = ecg_system.data_processor.calculate_clinical_indices(ecg_signal)
        result = generate_clinical_indices_result(clinical_indices)
    elif analysis_type == 'respiration_rate':  # 添加呼吸频率分析
        respiration_signal = respiration_system.accumulated_data
        respiration_rate = respiration_processor.calculate_respiration_rate(respiration_signal)
        result = str(respiration_rate)
    else:
        result = '未知的分析类型'
    return jsonify({'result': result})

def generate_analysis_result(signals, info):
    import base64
    from io import BytesIO
    import matplotlib.pyplot as plt

    plt.figure()
    plt.plot(signals['ECG_Clean'])
    plt.plot(signals['ECG_R_Peaks'], signals['ECG_Clean'][signals['ECG_R_Peaks']], 'ro')
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('ascii')
    html_img = f'<img src="data:image/png;base64,{image_base64}"/>'
    return html_img

if __name__ == '__main__':
    socketio.run(app, debug=True)
