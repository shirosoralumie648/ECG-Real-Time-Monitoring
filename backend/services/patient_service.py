# patient_service.py

from datetime import datetime
from bson import ObjectId

# 导入数据库管理器
from ..data.database_manager import database_manager

class PatientService:
    """患者服务类，负责患者相关操作"""
    
    @staticmethod
    def create_patient(patient_data):
        """创建新患者
        
        Args:
            patient_data (dict): 患者数据
        
        Returns:
            dict: 创建结果
        """
        # 检查必填字段
        required_fields = ['name', 'gender', 'birth_date']
        for field in required_fields:
            if field not in patient_data:
                return {'success': False, 'message': f'缺少必填字段: {field}'}
        
        # 添加创建时间
        patient_data['created_at'] = datetime.now()
        patient_data['updated_at'] = datetime.now()
        
        # 存储患者数据
        try:
            patient_id = database_manager.store_patient_info(patient_data)
            return {
                'success': True,
                'message': '患者创建成功',
                'patient_id': patient_id
            }
        except Exception as e:
            return {'success': False, 'message': f'患者创建失败: {str(e)}'}
    
    @staticmethod
    def get_patient(patient_id):
        """获取患者信息
        
        Args:
            patient_id (str): 患者ID
        
        Returns:
            dict: 患者信息
        """
        try:
            # 转换ID格式
            object_id = ObjectId(patient_id)
            
            # 查询患者
            patient_data = database_manager.mongodb_db.patients.find_one({'_id': object_id})
            if not patient_data:
                return {'success': False, 'message': '患者不存在'}
            
            # 转换ID为字符串
            patient_data['_id'] = str(patient_data['_id'])
            
            return {
                'success': True,
                'patient': patient_data
            }
        except Exception as e:
            return {'success': False, 'message': f'获取患者信息失败: {str(e)}'}
    
    @staticmethod
    def update_patient(patient_id, update_data):
        """更新患者信息
        
        Args:
            patient_id (str): 患者ID
            update_data (dict): 更新数据
        
        Returns:
            dict: 更新结果
        """
        try:
            # 转换ID格式
            object_id = ObjectId(patient_id)
            
            # 不允许更新敏感字段
            sensitive_fields = ['_id', 'created_at']
            for field in sensitive_fields:
                update_data.pop(field, None)
            
            # 添加更新时间
            update_data['updated_at'] = datetime.now()
            
            # 更新患者信息
            result = database_manager.mongodb_db.patients.update_one(
                {'_id': object_id},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                return {'success': True, 'message': '患者信息更新成功'}
            else:
                return {'success': False, 'message': '患者信息更新失败或无变化'}
        except Exception as e:
            return {'success': False, 'message': f'更新患者信息失败: {str(e)}'}
    
    @staticmethod
    def delete_patient(patient_id):
        """删除患者
        
        Args:
            patient_id (str): 患者ID
        
        Returns:
            dict: 删除结果
        """
        try:
            # 转换ID格式
            object_id = ObjectId(patient_id)
            
            # 删除患者
            result = database_manager.mongodb_db.patients.delete_one({'_id': object_id})
            
            if result.deleted_count > 0:
                return {'success': True, 'message': '患者删除成功'}
            else:
                return {'success': False, 'message': '患者不存在或删除失败'}
        except Exception as e:
            return {'success': False, 'message': f'删除患者失败: {str(e)}'}
    
    @staticmethod
    def list_patients(page=1, per_page=10, filters=None):
        """获取患者列表
        
        Args:
            page (int, optional): 页码
            per_page (int, optional): 每页数量
            filters (dict, optional): 过滤条件
        
        Returns:
            dict: 患者列表
        """
        try:
            # 构建查询条件
            query = {}
            if filters:
                # 姓名模糊查询
                if 'name' in filters and filters['name']:
                    query['name'] = {'$regex': filters['name'], '$options': 'i'}
                
                # 性别精确匹配
                if 'gender' in filters and filters['gender']:
                    query['gender'] = filters['gender']
                
                # 年龄范围查询
                if 'min_age' in filters and filters['min_age']:
                    # 计算出生日期上限
                    max_birth_date = datetime.now().replace(year=datetime.now().year - int(filters['min_age']))
                    query['birth_date'] = {'$lte': max_birth_date}
                
                if 'max_age' in filters and filters['max_age']:
                    # 计算出生日期下限
                    min_birth_date = datetime.now().replace(year=datetime.now().year - int(filters['max_age']) - 1)
                    if 'birth_date' in query:
                        query['birth_date']['$gte'] = min_birth_date
                    else:
                        query['birth_date'] = {'$gte': min_birth_date}
            
            # 计算分页
            skip = (page - 1) * per_page
            
            # 查询患者总数
            total = database_manager.mongodb_db.patients.count_documents(query)
            
            # 查询患者列表
            patients = list(database_manager.mongodb_db.patients.find(query)
                           .sort('created_at', -1)
                           .skip(skip)
                           .limit(per_page))
            
            # 转换ID为字符串
            for patient in patients:
                patient['_id'] = str(patient['_id'])
            
            return {
                'success': True,
                'patients': patients,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }
        except Exception as e:
            return {'success': False, 'message': f'获取患者列表失败: {str(e)}'}
    
    @staticmethod
    def add_medical_record(patient_id, record_data):
        """添加病历记录
        
        Args:
            patient_id (str): 患者ID
            record_data (dict): 病历数据
        
        Returns:
            dict: 添加结果
        """
        try:
            # 转换ID格式
            object_id = ObjectId(patient_id)
            
            # 检查患者是否存在
            patient = database_manager.mongodb_db.patients.find_one({'_id': object_id})
            if not patient:
                return {'success': False, 'message': '患者不存在'}
            
            # 添加记录时间和患者ID
            record_data['created_at'] = datetime.now()
            record_data['patient_id'] = patient_id
            
            # 存储病历记录
            result = database_manager.mongodb_db.medical_records.insert_one(record_data)
            
            return {
                'success': True,
                'message': '病历记录添加成功',
                'record_id': str(result.inserted_id)
            }
        except Exception as e:
            return {'success': False, 'message': f'添加病历记录失败: {str(e)}'}
    
    @staticmethod
    def get_medical_records(patient_id, page=1, per_page=10):
        """获取患者病历记录
        
        Args:
            patient_id (str): 患者ID
            page (int, optional): 页码
            per_page (int, optional): 每页数量
        
        Returns:
            dict: 病历记录列表
        """
        try:
            # 计算分页
            skip = (page - 1) * per_page
            
            # 查询病历总数
            total = database_manager.mongodb_db.medical_records.count_documents({'patient_id': patient_id})
            
            # 查询病历列表
            records = list(database_manager.mongodb_db.medical_records.find({'patient_id': patient_id})
                           .sort('created_at', -1)
                           .skip(skip)
                           .limit(per_page))
            
            # 转换ID为字符串
            for record in records:
                record['_id'] = str(record['_id'])
            
            return {
                'success': True,
                'records': records,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }
        except Exception as e:
            return {'success': False, 'message': f'获取病历记录失败: {str(e)}'}

# 初始化患者服务
patient_service = PatientService()
