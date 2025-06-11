# web_server.py

# 确保在所有导入之前执行monkey_patch
import eventlet
eventlet.monkey_patch()

# 导入其他模块
import numpy as np
import matplotlib.pyplot as plt
import os
import io
import time
import json
from datetime import datetime

# 导入Flask相关库
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from flask_bcrypt import Bcrypt
from flask_cors import CORS

# 导入微服务组件
from .services.user_service import user_service, User
from .services.patient_service import patient_service
from .services.device_service import device_service
from .services.data_acquisition_service import data_acquisition_service
from .services.data_processing_service import data_processing_service
from .services.storage_service import storage_service
from .services.report_service import report_service
from .services.analysis_service import ecg_analysis_service

# 导入API路由
from .api.device_routes import device_bp
from .api.auth_routes import auth_bp
from .api.patient_routes import patient_bp
from .api.report_routes import report_bp
from .api.analysis_routes import analysis_bp

# 初始化报警服务
from .services.alert_service import init_alert_service, get_alert_service

# 创建Flask应用
app = Flask(__name__, 
static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key_for_development')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 会话有效期（秒）

# 初始化扩展
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # 未登录时重定向到登录页面
login_manager.login_message = '请先登录'
CORS(app)  # 启用跨域支持

# 优化Socket.IO配置以减少延迟并提高性能
socketio = SocketIO(
    app, 
    cors_allowed_origins='*', 
    async_mode='eventlet', 
    ping_timeout=10,           # 降低 ping 超时时间以更快地检测连接丢失
    ping_interval=5,           # 降低 ping 间隔以保持连接活跃
    max_http_buffer_size=5*1024*1024,  # 增加HTTP缓冲区大小以处理更大的数据包
    manage_session=False,      # 禁用会话管理以提高性能
    engineio_logger=False,     # 禁用引擎日志以提高性能
    logger=False               # 禁用日志以提高性能
)

# 初始化报警服务，传入socketio实例用于实时通知
alert_service = init_alert_service(socketio)

# 用户加载函数
@login_manager.user_loader
def load_user(user_id):
    return user_service.get_user_by_id(user_id)

# 注册API蓝图
app.register_blueprint(device_bp, url_prefix='/api/device')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(patient_bp, url_prefix='/api/patient')
app.register_blueprint(report_bp, url_prefix='/api/report')
app.register_blueprint(analysis_bp)

# 设置数据存储目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
REPORT_DIR = os.path.join(DATA_DIR, 'reports')

# 确保目录存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)


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
def home():
    return render_template('home.html')

@app.route('/ecg')
def index():
    return render_template('index.html')

@app.route('/respiration')
def respiration():
    return render_template('respiration.html')

# 连接数据源
@app.route('/connect', methods=['POST'])
def connect():
    print("Received /connect request")
    
    # 获取数据来源配置
    source_config = request.get_json()
    if not source_config:
        return jsonify({'status': 'error', 'message': '缺少数据来源配置'}), 400
    
    print(f"Data source config for connection: {source_config}")
    
    try:
        # 根据数据来源类型连接不同的设备
        source_type = source_config.get('type')
        
        if source_type == 'serial':
            # 串口模式
            port = source_config.get('port', 'COM7')
            baudrate = source_config.get('baudrate', 921600)
            ecg_system.connect_serial(port, baudrate)
            
        elif source_type == 'udp':
            # UDP模式
            local_ip = source_config.get('local_ip', '0.0.0.0')
            local_port = source_config.get('local_port', 5001)
            remote_ip = source_config.get('remote_ip')
            remote_port = source_config.get('remote_port')
            ecg_system.connect_udp(local_ip, local_port, remote_ip, remote_port)
            
        elif source_type == 'bluetooth':
            # 蓝牙模式
            port = source_config.get('port')
            baudrate = source_config.get('baudrate', 9600)
            if not port:
                return jsonify({'status': 'error', 'message': '缺少蓝牙设备串口'}), 400
            ecg_system.connect_bluetooth(port, baudrate)
            
        elif source_type == 'file':
            # 文件回放模式
            file_name = source_config.get('fileName')
            if not file_name:
                return jsonify({'status': 'error', 'message': '缺少文件名'}), 400
            ecg_system.connect_file(file_name)
            
        else:
            return jsonify({'status': 'error', 'message': f'不支持的数据来源类型: {source_type}'}), 400
        
        return jsonify({'status': 'connected'}), 200
    
    except Exception as e:
        print(f"Error connecting to data source: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# 断开数据源连接
@app.route('/disconnect', methods=['POST'])
def disconnect():
    print("Received /disconnect request")
    
    try:
        ecg_system.disconnect()
        return jsonify({'status': 'disconnected'}), 200
    except Exception as e:
        print(f"Error disconnecting data source: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/start', methods=['POST'])
def start():
    print("Received /start request")
    
    try:
        # 获取回放速度（如果是文件模式）
        source_config = request.get_json() or {}
        speed = source_config.get('speed', 1.0)
        
        # 开始监测
        if ecg_system.start_monitoring(speed):
            return jsonify({'status': 'started'}), 200
        else:
            return jsonify({'status': 'error', 'message': '启动监测失败'}), 500
    
    except Exception as e:
        print(f"Error starting ECG system: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/stop', methods=['POST'])
def stop():
    print("Received /stop request")
    ecg_system.stop()
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

# 获取可用串口列表
@app.route('/get_serial_ports', methods=['GET'])
def get_serial_ports():
    ports = scan_ports()
    return jsonify(ports)

# 初始化蓝牙模块
@app.route('/init_bluetooth', methods=['GET'])
def init_bt():
    success = init_bluetooth()
    return jsonify({'success': success})

# 开始扫描蓝牙设备
@app.route('/scan_bluetooth', methods=['POST'])
def scan_bt():
    success = start_scan()
    return jsonify({'success': success})

# 停止扫描蓝牙设备
@app.route('/stop_bluetooth_scan', methods=['POST'])
def stop_bt_scan():
    success = stop_scan()
    return jsonify({'success': success})

# 获取已发现的蓝牙设备
@app.route('/get_bluetooth_devices', methods=['GET'])
def get_bt_devices():
    devices = get_discovered_devices()
    return jsonify(devices)

# 连接蓝牙设备
@app.route('/connect_bluetooth', methods=['POST'])
def connect_bt():
    data = request.get_json()
    if not data or 'address' not in data:
        return jsonify({'success': False, 'message': '缺少设备地址'}), 400
        
    address = data['address']
    port, error = connect_device(address)
    
    if port:
        return jsonify({'success': True, 'port': port})
    else:
        return jsonify({'success': False, 'message': error}), 400

# 断开蓝牙设备连接
@app.route('/disconnect_bluetooth', methods=['POST'])
def disconnect_bt():
    data = request.get_json()
    if not data or 'address' not in data:
        return jsonify({'success': False, 'message': '缺少设备地址'}), 400
        
    address = data['address']
    success, error = disconnect_device(address)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': error}), 400

# 呈吸监测相关的路由
# 首页和主要视图路由
@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/monitor')
def monitor():
    return render_template('index.html')

@app.route('/respiration')
def respiration():
    return render_template('respiration.html')

@app.route('/patients')
@login_required
def patients():
    return render_template('patients.html')

# API接口 - 患者管理
@app.route('/api/patients', methods=['GET'])
@login_required
def get_patients():
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 10))
    search = request.args.get('search', '')
    
    result = patient_service.get_patients(limit, offset, search)
    return jsonify(result)

@app.route('/api/patients/<patient_id>', methods=['GET'])
@login_required
def get_patient(patient_id):
    result = patient_service.get_patient(patient_id)
    return jsonify(result)

# API接口 - 报告管理
@app.route('/api/reports/generate', methods=['POST'])
@login_required
def generate_report():
    data = request.get_json()
    patient_id = data.get('patient_id')
    session_id = data.get('session_id')
    time_range = data.get('time_range')
    
    if not patient_id or not session_id:
        return jsonify({
            'success': False,
            'message': '缺少必要参数'
        }), 400
    
    result = report_service.generate_ecg_report(patient_id, session_id, time_range)
    return jsonify(result)

@app.route('/api/reports/<report_id>', methods=['GET'])
@login_required
def get_report(report_id):
    result = report_service.get_report(report_id)
    return jsonify(result)

# API接口 - 报警管理
@app.route('/api/alerts/<patient_id>', methods=['GET'])
@login_required
def get_patient_alerts(patient_id):
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    severity = request.args.get('severity')
    
    alert_service = get_alert_service()
    result = alert_service.get_patient_alerts(patient_id, limit, offset, severity)
    return jsonify(result)

@app.route('/api/alerts/thresholds', methods=['GET'])
@login_required
def get_alert_thresholds():
    alert_service = get_alert_service()
    result = alert_service.get_thresholds()
    return jsonify(result)

@app.route('/api/alerts/thresholds', methods=['POST'])
@login_required
def set_alert_threshold():
    data = request.get_json()
    threshold_name = data.get('name')
    value = data.get('value')
    
    if not threshold_name or value is None:
        return jsonify({
            'success': False,
            'message': '缺少必要参数'
        }), 400
    
    alert_service = get_alert_service()
    result = alert_service.set_threshold(threshold_name, value)
    return jsonify(result)

# API接口 - 分析服务
@app.route('/api/analysis/ecg', methods=['POST'])
def analyze_ecg():
    data = request.get_json()
    patient_id = data.get('patient_id', 'unknown')
    ecg_data = data.get('ecg_data')
    timestamps = data.get('timestamps')
    lead_index = data.get('lead_index', 0)
    sampling_rate = data.get('sampling_rate', 500)
    
    if not ecg_data or not timestamps:
        return jsonify({
            'success': False,
            'message': '缺少必要的ECG数据或时间戳'
        }), 400
    
    result = ecg_analysis_service.analyze_ecg_data(
        patient_id,
        ecg_data,
        timestamps,
        lead_index,
        sampling_rate
    )
    
    return jsonify(result)

# Socket.IO事件处理
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    
@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')
    
@socketio.on('start_monitoring')
def handle_start_monitoring(data):
    patient_id = data.get('patient_id')
    config = data.get('config', {})
    
    # 启动数据采集服务
    result = data_acquisition_service.start_acquisition(patient_id, config)
    emit('monitoring_status', result)
    
@socketio.on('stop_monitoring')
def handle_stop_monitoring():
    # 停止数据采集服务
    result = data_acquisition_service.stop_acquisition()
    emit('monitoring_status', result)
    
@socketio.on('set_lead')
def handle_set_lead(data):
    lead_index = data.get('lead_index', 0)
    data_processing_service.set_active_lead(lead_index)
    
@socketio.on('connect_device')
def handle_connect_device(data):
    device_type = data.get('type')
    config = data.get('config', {})
    
    if device_type == 'serial':
        port = config.get('port')
        baudrate = config.get('baudrate', 921600)
        result = device_service.connect_serial(port, baudrate)
    elif device_type == 'udp':
        host = config.get('host', '0.0.0.0')
        port = config.get('port', 8888)
        result = device_service.connect_udp(host, port)
    elif device_type == 'bluetooth':
        device_address = config.get('device_address')
        result = device_service.connect_bluetooth(device_address)
    else:
        result = {'success': False, 'message': '不支持的设备类型'}
        
    emit('device_status', result)

@socketio.on('disconnect_device')
def handle_disconnect_device():
    result = device_service.disconnect()
    emit('device_status', result)

# 启动应用
if __name__ == '__main__':
    # 初始化数据存储相关服务
    
    # 启动报警监控
    alert_service.start_monitoring()
    
    # 运行Web服务器
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
