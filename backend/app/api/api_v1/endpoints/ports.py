from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional
import serial.tools.list_ports

router = APIRouter()

# Placeholder for a global connection manager
# In a real app, this would be a more robust class or service
connection_manager = {"connection": None, "type": None}

@router.get("/scan")
def scan_ports():
    """Scan for available serial ports."""
    ports = [port.device for port in serial.tools.list_ports.comports()]
    return {"ports": ports}

@router.post("/connect")
async def connect(
    type: str = Form(...),
    port: Optional[str] = Form(None),
    host: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """Connect to a data source."""
    # Disconnect any existing connection
    if connection_manager["connection"]:
        # In a real app, you would properly close the old connection
        pass

    if type == "serial":
        if not port:
            raise HTTPException(status_code=400, detail="Port is required for serial connection")
        connection_manager["connection"] = {"port": port}
        connection_manager["type"] = "serial"
        return {"message": f"Connected to serial port {port}"}

    elif type == "udp":
        if not host or not port:
            raise HTTPException(status_code=400, detail="Host and port are required for UDP")
        connection_manager["connection"] = {"host": host, "port": port}
        connection_manager["type"] = "udp"
        return {"message": f"Connected to UDP {host}:{port}"}

    elif type == "file":
        if not file:
            raise HTTPException(status_code=400, detail="File is required for file playback")
        # In a real app, you would save the file and start a playback thread
        # For now, just acknowledge the file
        connection_manager["connection"] = {"filename": file.filename}
        connection_manager["type"] = "file"
        return {"message": f"Started playback from {file.filename}"}

    else:
        raise HTTPException(status_code=400, detail="Unsupported connection type")

@router.post("/disconnect")
def disconnect():
    """Disconnect from the current data source."""
    connection_manager["connection"] = None
    connection_manager["type"] = None
    return {"message": "Disconnected successfully"}
