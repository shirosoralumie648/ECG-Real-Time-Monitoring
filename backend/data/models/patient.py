# patient.py

from datetime import datetime

class Patient:
    """患者模型类"""
    
    def __init__(self, patient_data):
        self.id = str(patient_data.get('_id'))
        self.name = patient_data.get('name')
        self.gender = patient_data.get('gender')
        self.birth_date = patient_data.get('birth_date')
        self.contact = patient_data.get('contact')
        self.medical_history = patient_data.get('medical_history', [])
        self.created_at = patient_data.get('created_at')
        self.updated_at = patient_data.get('updated_at')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'gender': self.gender,
            'birth_date': self.birth_date,
            'contact': self.contact,
            'medical_history': self.medical_history,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def calculate_age(self):
        """计算患者年龄"""
        if not self.birth_date:
            return None
        
        today = datetime.now()
        birth_date = self.birth_date
        
        # 如果birth_date是字符串，转换为datetime对象
        if isinstance(birth_date, str):
            try:
                birth_date = datetime.fromisoformat(birth_date)
            except ValueError:
                return None
        
        age = today.year - birth_date.year
        
        # 检查是否已过生日
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
            
        return age
