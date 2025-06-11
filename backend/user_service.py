# user_service.py

import os
import jwt
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required

# 导入数据库管理器
from .database_manager import database_manager

# 初始化Bcrypt
bcrypt = Bcrypt()

# 初始化LoginManager
login_manager = LoginManager()

# JWT配置
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key')
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

class User(UserMixin):
    """用户模型类"""
    
    def __init__(self, user_data):
        self.id = str(user_data.get('_id'))
        self.username = user_data.get('username')
        self.email = user_data.get('email')
        self.password_hash = user_data.get('password_hash')
        self.role = user_data.get('role', 'user')  # 默认角色为普通用户
        self.created_at = user_data.get('created_at')
        self.last_login = user_data.get('last_login')
        self.is_active = user_data.get('is_active', True)
    
    def check_password(self, password):
        """检查密码是否正确"""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def get_token(self):
        """生成JWT令牌"""
        token_data = {
            'user_id': self.id,
            'username': self.username,
            'role': self.role,
            'exp': datetime.utcnow() + JWT_ACCESS_TOKEN_EXPIRES
        }
        return jwt.encode(token_data, JWT_SECRET_KEY, algorithm='HS256')
    
    @staticmethod
    def verify_token(token):
        """验证JWT令牌"""
        try:
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            return data
        except:
            return None

@login_manager.user_loader
def load_user(user_id):
    """加载用户"""
    user_data = database_manager.mongodb_db.users.find_one({'_id': user_id})
    if user_data:
        return User(user_data)
    return None

class UserService:
    """用户服务类，负责用户相关操作"""
    
    @staticmethod
    def register_user(username, email, password, role='user'):
        """注册新用户
        
        Args:
            username (str): 用户名
            email (str): 邮箱
            password (str): 密码
            role (str, optional): 角色
        
        Returns:
            dict: 注册结果
        """
        # 检查用户名是否已存在
        if database_manager.mongodb_db.users.find_one({'username': username}):
            return {'success': False, 'message': '用户名已存在'}
        
        # 检查邮箱是否已存在
        if database_manager.mongodb_db.users.find_one({'email': email}):
            return {'success': False, 'message': '邮箱已存在'}
        
        # 创建新用户
        user_data = {
            'username': username,
            'email': email,
            'password_hash': bcrypt.generate_password_hash(password).decode('utf-8'),
            'role': role,
            'created_at': datetime.now(),
            'last_login': None,
            'is_active': True
        }
        
        # 存储用户数据
        user_id = database_manager.mongodb_db.users.insert_one(user_data).inserted_id
        
        return {
            'success': True,
            'message': '注册成功',
            'user_id': str(user_id)
        }
    
    @staticmethod
    def login(username, password):
        """用户登录
        
        Args:
            username (str): 用户名
            password (str): 密码
        
        Returns:
            dict: 登录结果
        """
        # 查找用户
        user_data = database_manager.mongodb_db.users.find_one({'username': username})
        if not user_data:
            return {'success': False, 'message': '用户名或密码错误'}
        
        # 创建用户对象
        user = User(user_data)
        
        # 检查密码
        if not user.check_password(password):
            return {'success': False, 'message': '用户名或密码错误'}
        
        # 检查用户状态
        if not user.is_active:
            return {'success': False, 'message': '账户已被禁用'}
        
        # 更新最后登录时间
        database_manager.mongodb_db.users.update_one(
            {'_id': user_data['_id']},
            {'$set': {'last_login': datetime.now()}}
        )
        
        # 登录用户
        login_user(user)
        
        # 生成令牌
        token = user.get_token()
        
        return {
            'success': True,
            'message': '登录成功',
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role
            }
        }
    
    @staticmethod
    def logout():
        """用户登出"""
        logout_user()
        return {'success': True, 'message': '登出成功'}
    
    @staticmethod
    def get_user_profile(user_id):
        """获取用户资料
        
        Args:
            user_id (str): 用户ID
        
        Returns:
            dict: 用户资料
        """
        user_data = database_manager.mongodb_db.users.find_one({'_id': user_id})
        if not user_data:
            return {'success': False, 'message': '用户不存在'}
        
        # 移除敏感信息
        user_data.pop('password_hash', None)
        
        return {
            'success': True,
            'user': user_data
        }
    
    @staticmethod
    def update_user_profile(user_id, update_data):
        """更新用户资料
        
        Args:
            user_id (str): 用户ID
            update_data (dict): 更新数据
        
        Returns:
            dict: 更新结果
        """
        # 不允许更新敏感字段
        sensitive_fields = ['_id', 'password_hash', 'role', 'created_at']
        for field in sensitive_fields:
            update_data.pop(field, None)
        
        # 更新用户资料
        result = database_manager.mongodb_db.users.update_one(
            {'_id': user_id},
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            return {'success': True, 'message': '资料更新成功'}
        else:
            return {'success': False, 'message': '资料更新失败或无变化'}
    
    @staticmethod
    def change_password(user_id, current_password, new_password):
        """修改密码
        
        Args:
            user_id (str): 用户ID
            current_password (str): 当前密码
            new_password (str): 新密码
        
        Returns:
            dict: 修改结果
        """
        # 查找用户
        user_data = database_manager.mongodb_db.users.find_one({'_id': user_id})
        if not user_data:
            return {'success': False, 'message': '用户不存在'}
        
        # 创建用户对象
        user = User(user_data)
        
        # 检查当前密码
        if not user.check_password(current_password):
            return {'success': False, 'message': '当前密码错误'}
        
        # 更新密码
        new_password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        result = database_manager.mongodb_db.users.update_one(
            {'_id': user_id},
            {'$set': {'password_hash': new_password_hash}}
        )
        
        if result.modified_count > 0:
            return {'success': True, 'message': '密码修改成功'}
        else:
            return {'success': False, 'message': '密码修改失败'}

# 初始化用户服务
user_service = UserService()
