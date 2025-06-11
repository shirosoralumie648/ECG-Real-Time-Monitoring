# user.py

from datetime import datetime
from flask_login import UserMixin
import jwt
from ...config import get_config

config = get_config()

class User(UserMixin):
    """u7528u6237u6a21u578bu7c7b"""
    
    def __init__(self, user_data):
        self.id = str(user_data.get('_id'))
        self.username = user_data.get('username')
        self.email = user_data.get('email')
        self.password_hash = user_data.get('password_hash')
        self.role = user_data.get('role', 'user')  # u9ed8u8ba4u89d2u8272u4e3au666eu901au7528u6237
        self.created_at = user_data.get('created_at')
        self.last_login = user_data.get('last_login')
        self.is_active = user_data.get('is_active', True)
    
    def check_password(self, password, bcrypt):
        """u68c0u67e5u5bc6u7801u662fu5426u6b63u786e"""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def get_token(self):
        """u751fu6210JWTu4ee4u724c"""
        token_data = {
            'user_id': self.id,
            'username': self.username,
            'role': self.role,
            'exp': datetime.utcnow() + config.JWT_ACCESS_TOKEN_EXPIRES
        }
        return jwt.encode(token_data, config.JWT_SECRET_KEY, algorithm='HS256')
    
    @staticmethod
    def verify_token(token):
        """u9a8cu8bc1JWTu4ee4u724c"""
        try:
            data = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=['HS256'])
            return data
        except:
            return None
