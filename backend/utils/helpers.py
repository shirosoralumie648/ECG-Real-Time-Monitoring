# helpers.py

import os
import time
import json
import numpy as np
from datetime import datetime

def ensure_serializable(obj):
    """u786eu4fddu5bf9u8c61u662fJSONu53efu5e8fu5217u5316u7684
    
    Args:
        obj: u8981u5e8fu5217u5316u7684u5bf9u8c61
        
    Returns:
        u53efu5e8fu5217u5316u7684u5bf9u8c61
    """
    if isinstance(obj, list):
        return [ensure_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: ensure_serializable(value) for key, value in obj.items()}
    elif hasattr(obj, 'tolist'):
        return obj.tolist()
    elif hasattr(obj, 'item'):
        return obj.item()  # u5904u7406u6807u91cfu7c7bu578b
    elif isinstance(obj, (datetime, np.datetime64)):
        return obj.isoformat()
    else:
        return obj

def format_timestamp(timestamp):
    """u683cu5f0fu5316u65f6u95f4u6233
    
    Args:
        timestamp: u65f6u95f4u6233
        
    Returns:
        u683cu5f0fu5316u7684u65f6u95f4u5b57u7b26u4e32
    """
    if isinstance(timestamp, (int, float)):
        dt = datetime.fromtimestamp(timestamp)
    elif isinstance(timestamp, str):
        try:
            dt = datetime.fromisoformat(timestamp)
        except ValueError:
            return timestamp
    elif isinstance(timestamp, datetime):
        dt = timestamp
    else:
        return str(timestamp)
    
    return dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

def generate_session_id():
    """u751fu6210u4f1au8bddID
    
    Returns:
        u4f1au8bddIDu5b57u7b26u4e32
    """
    timestamp = int(time.time() * 1000)
    random_part = os.urandom(4).hex()
    return f"{timestamp}-{random_part}"

def save_to_json(data, filename):
    """u5c06u6570u636eu4fddu5b58u4e3aJSONu6587u4ef6
    
    Args:
        data: u8981u4fddu5b58u7684u6570u636e
        filename: u6587u4ef6u540d
        
    Returns:
        bool: u662fu5426u6210u529f
    """
    try:
        # u786eu4fddu6570u636eu662fu53efu5e8fu5217u5316u7684
        serializable_data = ensure_serializable(data)
        
        # u4fddu5b58u5230u6587u4ef6
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(serializable_data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"u4fddu5b58JSONu6587u4ef6u5931u8d25: {e}")
        return False

def load_from_json(filename):
    """u4eceJSONu6587u4ef6u52a0u8f7du6570u636e
    
    Args:
        filename: u6587u4ef6u540d
        
    Returns:
        u52a0u8f7du7684u6570u636e
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"u52a0u8f7dJSONu6587u4ef6u5931u8d25: {e}")
        return None
