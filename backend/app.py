# app.py

# 确保在所有导入之前执行monkey_patch
import eventlet
eventlet.monkey_patch()

# 标准库导入
import os
import sys

# 第三方库导入
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS

# 导入配置
from .config import get_config

# 初始化配置
config = get_config()

# 预先导入API蓝图
from .api import api_bp

def create_app():
    """
    创建Flask应用实例
    """
    # 创建Flask应用
    app = Flask(__name__)
    
    # 加载配置
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['DEBUG'] = config.DEBUG
    
    # 初始化扩展
    bcrypt = Bcrypt(app)
    login_manager = LoginManager(app)
    
    # 自定义未授权处理函数，返回JSON而不是重定向
    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({"success": False, "message": "请先登录"}), 401
    
    CORS(app)  # 启用跨域支持
    
    # 注册蓝图
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # 注册首页路由
    @app.route('/')
    def home():
        return render_template('home.html')
    
    @app.route('/ecg')
    def ecg():
        return render_template('index.html')
    
    @app.route('/respiration')
    def respiration():
        return render_template('respiration.html')
    
    # 用户加载回调
    @login_manager.user_loader
    def load_user(user_id):
        # 导入放在函数内部避免循环导入
        from .data.database_manager import database_manager
        from .services.user_service import User
        
        user_data = database_manager.mongodb_db.users.find_one({'_id': user_id})
        if user_data:
            return User(user_data)
        return None
    
    return app

def create_socketio(app):
    """
    创建SocketIO实例
    """
    # 初始化SocketIO
    socketio = SocketIO(
        app, 
        cors_allowed_origins='*', 
        async_mode='eventlet', 
        ping_timeout=config.SOCKETIO_PING_TIMEOUT,
        ping_interval=config.SOCKETIO_PING_INTERVAL,
        max_http_buffer_size=config.SOCKETIO_MAX_HTTP_BUFFER_SIZE,
        manage_session=False,
        engineio_logger=False,
        logger=False
    )
    
    return socketio

# 创建应用和SocketIO实例
app = create_app()
socketio = create_socketio(app)

# 初始化各种服务
from .services import ecg_manager
from .services.alert_service import init_alert_service
ecg_manager.init(socketio)

# 初始化报警服务
init_alert_service(socketio)

# 初始化数据库连接
from .data.database_manager import database_manager
# 确保创建必要的数据库目录
import os
os.makedirs(os.path.join(os.path.dirname(__file__), 'data', 'reports'), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), 'data', 'fonts'), exist_ok=True)
