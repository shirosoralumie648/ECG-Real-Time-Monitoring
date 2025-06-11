# ecg_manager.py

"""
管理ECG监控系统的单例模块
这个模块提供了一个全局的ECG监控系统实例，避免循环导入问题
"""

# 全局变量，用于存储ECG监控系统实例
_ecg_system = None
_socketio = None

def init(socketio_instance):
    """
    初始化ECG管理器
    
    Args:
        socketio_instance: SocketIO实例
    """
    global _socketio
    _socketio = socketio_instance

def get_ecg_system():
    """
    获取ECG监控系统实例（延迟初始化）
    
    Returns:
        ECGMonitoringSystem实例
    """
    global _ecg_system, _socketio
    
    if _ecg_system is None and _socketio is not None:
        # 导入放在函数内部避免循环导入
        from .monitoring_service import ECGMonitoringSystem
        _ecg_system = ECGMonitoringSystem(_socketio)
        
    return _ecg_system
