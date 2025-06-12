import sys
import os
import logging

# 将项目根目录添加到sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) # backend的上一级是项目根目录
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 设置基本日志级别为DEBUG，以便观察详细日志
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 配置基本日志
logger = logging.getLogger(__name__)

# 添加当前目录到Python路径，解决导入问题
sys.path.insert(0, os.path.abspath("."))

try:
    # 导入WebSocket管理器和FastAPI应用
    from websocket_manager import websocket_manager
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    # 导入必要的路由器
    from app.api.api_v1.endpoints import websocket
    from app.api.api_v1.endpoints import ports
    
    # 创建FastAPI应用
    app = FastAPI(title="ECG实时监测系统")
    
    # 设置CORS，允许前端访问
    origins = [
        "http://localhost:3000",
        "http://localhost",
        "http://127.0.0.1:3000",
        "http://127.0.0.1",
        "*",
    ]
    
    # 详细配置CORS，确保预检请求(OPTIONS)也被正确处理
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=86400,  # CORS预检请求的缓存时间
    )
    
    logger.info("已配置CORS中间件，允许来源: %s", origins)
    
    # 添加路由
    app.include_router(websocket.router, prefix="/api/v1")
    app.include_router(ports.router, prefix="/api/v1/ports")
    
    @app.get("/")
    def read_root():
        return {"message": "欢迎使用ECG实时监测系统API"}
    
    # 启动应用
    if __name__ == "__main__":
        import uvicorn
        logger.info("启动ECG实时监测系统后端服务...")
        uvicorn.run(app, host="0.0.0.0", port=8000)
        
except Exception as e:
    logger.error(f"启动服务失败: {str(e)}")
    import traceback
    traceback.print_exc()
