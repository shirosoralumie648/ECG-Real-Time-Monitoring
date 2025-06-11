# config.py

import os
from datetime import timedelta

class Config:
    """u57fau7840u914du7f6eu7c7b"""
    # Flasku914du7f6e
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')
    DEBUG = False
    TESTING = False
    
    # u6570u636eu5e93u914du7f6e
    # InfluxDB
    INFLUXDB_URL = os.environ.get('INFLUXDB_URL', 'http://localhost:8086')
    INFLUXDB_TOKEN = os.environ.get('INFLUXDB_TOKEN', 'my-token')
    INFLUXDB_ORG = 'ecg_org'
    INFLUXDB_BUCKET = 'ecg_data'
    
    # MongoDB
    MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    MONGODB_DB_NAME = 'ecg_monitoring'
    
    # Redis
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
    REDIS_DB = int(os.environ.get('REDIS_DB', '0'))
    
    # JWTu914du7f6e
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-jwt-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    
    # u6587u4ef6u5b58u50a8
    FILE_DIRECTORY = '.'
    
    # Socket.IOu914du7f6e
    SOCKETIO_PING_TIMEOUT = 10
    SOCKETIO_PING_INTERVAL = 5
    SOCKETIO_MAX_HTTP_BUFFER_SIZE = 5 * 1024 * 1024
    
    # ECGu76d1u63a7u914du7f6e
    ECG_MAX_SAMPLES = 200
    ECG_BUFFER_MULTIPLIER = 5
    ECG_INTERPOLATION_METHOD = 'cubic'
    ECG_CONTINUITY_THRESHOLD = 2.0
    ECG_INTERPOLATION_THRESHOLD = 1.5

class DevelopmentConfig(Config):
    """u5f00u53d1u73afu5883u914du7f6e"""
    DEBUG = True

class TestingConfig(Config):
    """u6d4bu8bd5u73afu5883u914du7f6e"""
    TESTING = True
    DEBUG = True
    
    # u6d4bu8bd5u6570u636eu5e93
    MONGODB_DB_NAME = 'ecg_monitoring_test'
    INFLUXDB_BUCKET = 'ecg_data_test'

class ProductionConfig(Config):
    """u751fu4ea7u73afu5883u914du7f6e"""
    # u751fu4ea7u73afu5883u7279u5b9au914du7f6e
    pass

# u914du7f6eu5b57u5178
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# u83b7u53d6u5f53u524du914du7f6e
def get_config():
    env = os.environ.get('FLASK_ENV', 'development')
    return config_by_name.get(env, config_by_name['default'])
