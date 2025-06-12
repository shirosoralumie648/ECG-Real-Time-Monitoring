from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
import json
import os
import logging
from typing import Optional
import serial.tools.list_ports

# 配置日志
logger = logging.getLogger(__name__)

# 导入新的读取器和WebSocket管理器
from readers.serial_reader import SerialReader
from websocket_manager import websocket_manager

# 创建上传目录
if not os.path.exists("./uploads"):
    os.makedirs("./uploads")

router = APIRouter()

# In-memory connection manager
connection_manager = {
    "connection": None,
    "type": None,
}


@router.get("/scan")
def scan_ports():
    """Scan for available serial ports."""
    ports = [port.device for port in serial.tools.list_ports.comports()]
    return {"ports": ports}


@router.post("/connect")
async def connect(
    type: str = Form(...),
    dataFormat: str = Form(...), # 数据格式参数
    port: Optional[str] = Form(None),
    baudrate: Optional[int] = Form(115200),  # 添加波特率参数，默认值为115200
    host: Optional[str] = Form(None),
    port_number: Optional[int] = Form(None),  # 重命名为port_number以避免与串口port混淆
    file: Optional[UploadFile] = File(None)
):
    """Connect to a data source."""
    # 停止任何现有的读取器连接
    await websocket_manager.stop_active_reader()
    
    # 根据连接类型创建并启动相应的读取器
    reader = None
    
    if type == "serial":
        if not port:
            raise HTTPException(status_code=400, detail="Port is required for serial connection")
            
        connection_info = {"port": port, "baudrate": baudrate}  # 使用传入的波特率参数
        connection_manager["connection"] = connection_info
        connection_manager["type"] = "serial"
        
        # 记录连接信息便于调试
        logger.info(f"Connecting to serial port {port} with baudrate {baudrate} and format {dataFormat}")
        
        try:
            # 创建串口读取器
            reader = SerialReader(
                connection_info=connection_info,
                data_format=dataFormat,
                websocket_manager=websocket_manager
            )
            # 启动读取器
            await reader.start()
            # 设置为活跃读取器
            websocket_manager.set_active_reader(reader)
            logger.info(f"Started serial reader on port {port} with format {dataFormat}")
            return {"message": f"Connected to serial port {port} with format {dataFormat}"}
        except Exception as e:
            logger.error(f"Failed to start serial reader: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to connect to serial port: {str(e)}")

    elif type == "udp":
        if not host or not port_number:
            raise HTTPException(status_code=400, detail="Host and port_number are required for UDP")
            
        connection_info = {"host": host, "port": port_number}
        connection_manager["connection"] = connection_info
        connection_manager["type"] = "udp"
        
        # 记录连接信息
        logger.info(f"Connecting to UDP {host}:{port_number} with format {dataFormat}")
        
        # UDP读取器待实现
        logger.warning("UDP reader not yet implemented")
        return {"message": f"Connected to UDP {host}:{port_number} (Reader not implemented yet)"}

    elif type == "file":
        if not file:
            raise HTTPException(status_code=400, detail="File is required for file playback")
            
        # 保存上传的文件以供回放
        file_content = await file.read()
        file_path = f"./uploads/{file.filename}"
        
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        connection_info = {"file_path": file_path}
        connection_manager["connection"] = connection_info
        connection_manager["type"] = "file"
        
        # 文件读取器待实现
        logger.warning("File reader not yet implemented")
        return {"message": f"Uploaded and saved file {file.filename} (Reader not implemented yet)"}

    else:
        raise HTTPException(status_code=400, detail="Unsupported connection type: {type}")


@router.post("/disconnect")
async def disconnect():
    # 停止任何活跃的读取器
    await websocket_manager.stop_active_reader()
    
    # 清除连接记录
    connection_manager["connection"] = None
    connection_manager["type"] = None
    
    logger.info("Disconnected from data source")
    return {"message": "Disconnected from data source"}
