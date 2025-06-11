# api/__init__.py

from flask import Blueprint

# 创建API主蓝图
api_bp = Blueprint('api', __name__)

# 导入所有路由蓝图
from .auth_routes import auth_bp
from .patient_routes import patient_bp
from .monitor_routes import monitor_bp
from .analysis_routes import analysis_bp
from .device_routes import device_bp
from .file_routes import file_bp
from .report_routes import report_bp
from .alert_routes import alert_bp

# 注册子蓝图
api_bp.register_blueprint(auth_bp, url_prefix='/auth')
api_bp.register_blueprint(patient_bp, url_prefix='/patients')
api_bp.register_blueprint(monitor_bp, url_prefix='/monitor')
api_bp.register_blueprint(analysis_bp, url_prefix='/analysis')
api_bp.register_blueprint(device_bp, url_prefix='/devices')
api_bp.register_blueprint(report_bp, url_prefix='/reports')
api_bp.register_blueprint(alert_bp, url_prefix='/alerts')
api_bp.register_blueprint(file_bp)

# 导出API蓝图
__all__ = ['api_bp']