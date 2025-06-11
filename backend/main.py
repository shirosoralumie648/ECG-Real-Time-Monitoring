# main.py

# 确保在所有导入之前执行monkey_patch
import eventlet
eventlet.monkey_patch()

import os
import sys

# 添加项目根目录到系统路径
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

# 导入应用和SocketIO
from backend.app import app, socketio
from backend.config import get_config

# 获取配置
config = get_config()

if __name__ == '__main__':
    # 运行应用
    print(f"启动ECG实时监控系统服务器 (环境: {os.environ.get('FLASK_ENV', 'development')})...")
    socketio.run(
        app, 
        debug=config.DEBUG, 
        host='0.0.0.0',
        port=5001
    )
