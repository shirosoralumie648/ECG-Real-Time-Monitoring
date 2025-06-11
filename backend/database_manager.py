# database_manager.py

import os
import time
from datetime import datetime

# InfluxDB
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# MongoDB
from pymongo import MongoClient

# Redis
import redis

class DatabaseManager:
    """数据库管理器，负责与各种数据库的连接和操作"""
    
    def __init__(self):
        self.influxdb_client = None
        self.influxdb_org = "ecg_org"
        self.influxdb_bucket = "ecg_data"
        self.influxdb_token = os.environ.get("INFLUXDB_TOKEN", "my-token")
        self.influxdb_url = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
        
        self.mongodb_client = None
        self.mongodb_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
        self.mongodb_db_name = "ecg_monitoring"
        
        self.redis_client = None
        self.redis_host = os.environ.get("REDIS_HOST", "localhost")
        self.redis_port = int(os.environ.get("REDIS_PORT", "6379"))
        self.redis_db = int(os.environ.get("REDIS_DB", "0"))
        
        # 初始化连接
        self._init_connections()
    
    def _init_connections(self):
        """初始化所有数据库连接"""
        try:
            # 初始化InfluxDB连接
            self.influxdb_client = InfluxDBClient(
                url=self.influxdb_url,
                token=self.influxdb_token,
                org=self.influxdb_org
            )
            # 检查连接并创建bucket（如果不存在）
            self._check_influxdb()
            
            print(f"InfluxDB连接成功: {self.influxdb_url}")
        except Exception as e:
            print(f"InfluxDB连接失败: {e}")
            self.influxdb_client = None
        
        try:
            # 初始化MongoDB连接
            self.mongodb_client = MongoClient(self.mongodb_uri)
            self.mongodb_db = self.mongodb_client[self.mongodb_db_name]
            # 检查连接
            self.mongodb_client.server_info()
            print(f"MongoDB连接成功: {self.mongodb_uri}")
        except Exception as e:
            print(f"MongoDB连接失败: {e}")
            self.mongodb_client = None
        
        try:
            # 初始化Redis连接
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db
            )
            # 检查连接
            self.redis_client.ping()
            print(f"Redis连接成功: {self.redis_host}:{self.redis_port}")
        except Exception as e:
            print(f"Redis连接失败: {e}")
            self.redis_client = None
    
    def _check_influxdb(self):
        """检查InfluxDB连接并创建必要的bucket"""
        if not self.influxdb_client:
            return
        
        try:
            buckets_api = self.influxdb_client.buckets_api()
            bucket_list = buckets_api.find_buckets().buckets
            bucket_names = [bucket.name for bucket in bucket_list]
            
            if self.influxdb_bucket not in bucket_names:
                print(f"创建InfluxDB bucket: {self.influxdb_bucket}")
                buckets_api.create_bucket(bucket_name=self.influxdb_bucket, org=self.influxdb_org)
        except Exception as e:
            print(f"检查InfluxDB bucket时出错: {e}")
    
    def store_ecg_data(self, patient_id, leads_data, timestamps, metadata=None):
        """存储ECG数据到InfluxDB
        
        Args:
            patient_id (str): 患者ID
            leads_data (list): 导联数据列表，每个元素是一个导联的数据数组
            timestamps (list): 时间戳列表
            metadata (dict, optional): 元数据
        
        Returns:
            bool: 是否成功
        """
        if not self.influxdb_client:
            print("InfluxDB客户端未初始化，无法存储数据")
            return False
        
        try:
            write_api = self.influxdb_client.write_api(write_options=SYNCHRONOUS)
            points = []
            
            # 为每个导联的每个数据点创建一个Point
            for i, lead_data in enumerate(leads_data):
                for j, value in enumerate(lead_data):
                    if j < len(timestamps):  # 确保有对应的时间戳
                        point = Point("ecg_readings") \
                            .tag("patient_id", patient_id) \
                            .tag("lead", f"lead_{i}") \
                            .field("value", float(value)) \
                            .time(timestamps[j] * 10**9)  # 转换为纳秒时间戳
                        
                        # 添加元数据标签
                        if metadata:
                            for key, val in metadata.items():
                                point = point.tag(key, str(val))
                        
                        points.append(point)
            
            # 批量写入数据
            write_api.write(bucket=self.influxdb_bucket, org=self.influxdb_org, record=points)
            return True
        except Exception as e:
            print(f"存储ECG数据到InfluxDB时出错: {e}")
            return False
    
    def store_patient_info(self, patient_data):
        """存储患者信息到MongoDB
        
        Args:
            patient_data (dict): 患者数据
        
        Returns:
            str: 患者ID
        """
        if not self.mongodb_client:
            print("MongoDB客户端未初始化，无法存储患者信息")
            return None
        
        try:
            # 确保有创建时间
            if 'created_at' not in patient_data:
                patient_data['created_at'] = datetime.now()
            
            # 更新已有患者或创建新患者
            if '_id' in patient_data:
                result = self.mongodb_db.patients.update_one(
                    {"_id": patient_data["_id"]},
                    {"$set": patient_data}
                )
                return str(patient_data["_id"])
            else:
                result = self.mongodb_db.patients.insert_one(patient_data)
                return str(result.inserted_id)
        except Exception as e:
            print(f"存储患者信息到MongoDB时出错: {e}")
            return None
    
    def store_analysis_result(self, analysis_data):
        """存储分析结果到MongoDB
        
        Args:
            analysis_data (dict): 分析数据
        
        Returns:
            str: 分析结果ID
        """
        if not self.mongodb_client:
            print("MongoDB客户端未初始化，无法存储分析结果")
            return None
        
        try:
            # 确保有创建时间
            if 'created_at' not in analysis_data:
                analysis_data['created_at'] = datetime.now()
            
            result = self.mongodb_db.analysis_results.insert_one(analysis_data)
            return str(result.inserted_id)
        except Exception as e:
            print(f"存储分析结果到MongoDB时出错: {e}")
            return None
    
    def cache_data(self, key, value, expiration=3600):
        """缓存数据到Redis
        
        Args:
            key (str): 缓存键
            value (str): 缓存值
            expiration (int, optional): 过期时间（秒）
        
        Returns:
            bool: 是否成功
        """
        if not self.redis_client:
            print("Redis客户端未初始化，无法缓存数据")
            return False
        
        try:
            self.redis_client.set(key, value, ex=expiration)
            return True
        except Exception as e:
            print(f"缓存数据到Redis时出错: {e}")
            return False
    
    def get_cached_data(self, key):
        """从Redis获取缓存数据
        
        Args:
            key (str): 缓存键
        
        Returns:
            str: 缓存值
        """
        if not self.redis_client:
            print("Redis客户端未初始化，无法获取缓存数据")
            return None
        
        try:
            value = self.redis_client.get(key)
            return value.decode('utf-8') if value else None
        except Exception as e:
            print(f"从Redis获取缓存数据时出错: {e}")
            return None
    
    def close_connections(self):
        """关闭所有数据库连接"""
        try:
            if self.influxdb_client:
                self.influxdb_client.close()
        except Exception as e:
            print(f"关闭InfluxDB连接时出错: {e}")
        
        try:
            if self.mongodb_client:
                self.mongodb_client.close()
        except Exception as e:
            print(f"关闭MongoDB连接时出错: {e}")
        
        try:
            if self.redis_client:
                self.redis_client.close()
        except Exception as e:
            print(f"关闭Redis连接时出错: {e}")

# 单例模式
database_manager = DatabaseManager()
