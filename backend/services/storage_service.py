# storage_service.py

import os
import time
import json
import logging
import threading
from datetime import datetime, timedelta
from bson import ObjectId

# u5bfcu5165u6570u636eu5e93u7ba1u7406u5668
from ..data.database_manager import database_manager

class StorageService:
    """u5b58u50a8u670du52a1u7c7buff0cu8d1fu8d23u7ba1u7406u6570u636eu5b58u50a8u3001u5907u4efdu3001u5f52u6863"""
    
    def __init__(self):
        self.backup_in_progress = False
        self.archive_in_progress = False
        self.backup_thread = None
        self.archive_thread = None
        self.logger = logging.getLogger('storage_service')
        
        # u521bu5efau5fc5u8981u7684u5b58u50a8u76eeu5f55
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        self.backup_dir = os.path.join(self.data_dir, 'backups')
        self.archive_dir = os.path.join(self.data_dir, 'archives')
        
        self._ensure_directories()
    
    def _ensure_directories(self):
        """u786eu4fddu5fc5u8981u7684u76eeu5f55u5b58u5728"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.archive_dir, exist_ok=True)
    
    def store_ecg_data(self, patient_id, session_id, ecg_data, timestamp=None):
        """u5b58u50a8ECGu6570u636e
        
        Args:
            patient_id (str): u60a3u8005ID
            session_id (str): u4f1au8bddID
            ecg_data (list): ECGu6570u636e
            timestamp (datetime, optional): u65f6u95f4u6233
        
        Returns:
            dict: u5b58u50a8u7ed3u679c
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            # u5c06u6570u636eu5b58u50a8u5230MongoDB
            data_point = {
                'patient_id': patient_id,
                'session_id': session_id,
                'type': 'ecg',
                'data': ecg_data,
                'timestamp': timestamp,
                'created_at': datetime.now()
            }
            
            result = database_manager.mongodb_db.physiological_data.insert_one(data_point)
            
            # u5c06u6570u636eu5b58u50a8u5230InfluxDB
            try:
                points = [{
                    'measurement': 'ecg_data',
                    'tags': {
                        'patient_id': patient_id,
                        'session_id': session_id
                    },
                    'time': timestamp.isoformat(),
                    'fields': {
                        'value': float(ecg_data) if isinstance(ecg_data, (int, float)) else float(ecg_data[0])
                    }
                }]
                
                database_manager.write_points_to_influxdb(points)
            except Exception as e:
                self.logger.error(f"u5b58u50a8u5230InfluxDBu5931u8d25: {str(e)}")
            
            return {
                'success': True,
                'message': 'ECGu6570u636eu5b58u50a8u6210u529f',
                'data_id': str(result.inserted_id)
            }
        except Exception as e:
            self.logger.error(f"u5b58u50a8ECGu6570u636eu5931u8d25: {str(e)}")
            return {'success': False, 'message': f'u5b58u50a8ECGu6570u636eu5931u8d25: {str(e)}'}
    
    def store_physiological_data(self, patient_id, session_id, data_type, data, timestamp=None):
        """u5b58u50a8u751fu7406u6570u636e
        
        Args:
            patient_id (str): u60a3u8005ID
            session_id (str): u4f1au8bddID
            data_type (str): u6570u636eu7c7bu578buff08u5982'heart_rate', 'spo2', 'temperature'u7b49uff09
            data: u751fu7406u6570u636e
            timestamp (datetime, optional): u65f6u95f4u6233
        
        Returns:
            dict: u5b58u50a8u7ed3u679c
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            # u5c06u6570u636eu5b58u50a8u5230MongoDB
            data_point = {
                'patient_id': patient_id,
                'session_id': session_id,
                'type': data_type,
                'data': data,
                'timestamp': timestamp,
                'created_at': datetime.now()
            }
            
            result = database_manager.mongodb_db.physiological_data.insert_one(data_point)
            
            # u5c06u6570u636eu5b58u50a8u5230InfluxDB
            try:
                points = [{
                    'measurement': data_type,
                    'tags': {
                        'patient_id': patient_id,
                        'session_id': session_id
                    },
                    'time': timestamp.isoformat(),
                    'fields': {
                        'value': float(data) if isinstance(data, (int, float)) else 0.0
                    }
                }]
                
                database_manager.write_points_to_influxdb(points)
            except Exception as e:
                self.logger.error(f"u5b58u50a8u5230InfluxDBu5931u8d25: {str(e)}")
            
            return {
                'success': True,
                'message': f'{data_type}u6570u636eu5b58u50a8u6210u529f',
                'data_id': str(result.inserted_id)
            }
        except Exception as e:
            self.logger.error(f"u5b58u50a8{data_type}u6570u636eu5931u8d25: {str(e)}")
            return {'success': False, 'message': f'u5b58u50a8{data_type}u6570u636eu5931u8d25: {str(e)}'}
    
    def store_analysis_result(self, patient_id, session_id, analysis_type, result_data):
        """u5b58u50a8u5206u6790u7ed3u679c
        
        Args:
            patient_id (str): u60a3u8005ID
            session_id (str): u4f1au8bddID
            analysis_type (str): u5206u6790u7c7bu578buff08u5982'heart_rate_variability', 'arrhythmia_detection'u7b49uff09
            result_data (dict): u5206u6790u7ed3u679cu6570u636e
        
        Returns:
            dict: u5b58u50a8u7ed3u679c
        """
        try:
            # u5c06u5206u6790u7ed3u679cu5b58u50a8u5230MongoDB
            analysis_record = {
                'patient_id': patient_id,
                'session_id': session_id,
                'type': analysis_type,
                'data': result_data,
                'created_at': datetime.now()
            }
            
            result = database_manager.mongodb_db.analysis_results.insert_one(analysis_record)
            
            return {
                'success': True,
                'message': f'{analysis_type}u5206u6790u7ed3u679cu5b58u50a8u6210u529f',
                'result_id': str(result.inserted_id)
            }
        except Exception as e:
            self.logger.error(f"u5b58u50a8{analysis_type}u5206u6790u7ed3u679cu5931u8d25: {str(e)}")
            return {'success': False, 'message': f'u5b58u50a8{analysis_type}u5206u6790u7ed3u679cu5931u8d25: {str(e)}'}
    
    def retrieve_ecg_data(self, patient_id=None, session_id=None, start_time=None, end_time=None, limit=1000):
        """u68c0u7d22ECGu6570u636e
        
        Args:
            patient_id (str, optional): u60a3u8005ID
            session_id (str, optional): u4f1au8bddID
            start_time (datetime, optional): u5f00u59cbu65f6u95f4
            end_time (datetime, optional): u7ed3u675fu65f6u95f4
            limit (int, optional): u8fd4u56deu6570u636eu7684u6700u5927u6570u91cf
        
        Returns:
            dict: u67e5u8be2u7ed3u679c
        """
        try:
            # u6784u5efau67e5u8be2u6761u4ef6
            query = {'type': 'ecg'}
            
            if patient_id:
                query['patient_id'] = patient_id
            
            if session_id:
                query['session_id'] = session_id
            
            time_query = {}
            if start_time:
                time_query['$gte'] = start_time
            
            if end_time:
                time_query['$lte'] = end_time
            
            if time_query:
                query['timestamp'] = time_query
            
            # u6267u884cu67e5u8be2
            results = list(database_manager.mongodb_db.physiological_data.find(query)
                          .sort('timestamp', 1)
                          .limit(limit))
            
            # u5904u7406u7ed3u679c
            for result in results:
                result['_id'] = str(result['_id'])  # u8f6cu6362ObjectIdu4e3au5b57u7b26u4e32
            
            return {
                'success': True,
                'count': len(results),
                'data': results
            }
        except Exception as e:
            self.logger.error(f"u68c0u7d22ECGu6570u636eu5931u8d25: {str(e)}")
            return {'success': False, 'message': f'u68c0u7d22ECGu6570u636eu5931u8d25: {str(e)}'}
    
    def retrieve_physiological_data(self, data_type, patient_id=None, session_id=None, start_time=None, end_time=None, limit=1000):
        """u68c0u7d22u751fu7406u6570u636e
        
        Args:
            data_type (str): u6570u636eu7c7bu578b
            patient_id (str, optional): u60a3u8005ID
            session_id (str, optional): u4f1au8bddID
            start_time (datetime, optional): u5f00u59cbu65f6u95f4
            end_time (datetime, optional): u7ed3u675fu65f6u95f4
            limit (int, optional): u8fd4u56deu6570u636eu7684u6700u5927u6570u91cf
        
        Returns:
            dict: u67e5u8be2u7ed3u679c
        """
        try:
            # u6784u5efau67e5u8be2u6761u4ef6
            query = {'type': data_type}
            
            if patient_id:
                query['patient_id'] = patient_id
            
            if session_id:
                query['session_id'] = session_id
            
            time_query = {}
            if start_time:
                time_query['$gte'] = start_time
            
            if end_time:
                time_query['$lte'] = end_time
            
            if time_query:
                query['timestamp'] = time_query
            
            # u6267u884cu67e5u8be2
            results = list(database_manager.mongodb_db.physiological_data.find(query)
                          .sort('timestamp', 1)
                          .limit(limit))
            
            # u5904u7406u7ed3u679c
            for result in results:
                result['_id'] = str(result['_id'])  # u8f6cu6362ObjectIdu4e3au5b57u7b26u4e32
            
            return {
                'success': True,
                'count': len(results),
                'data': results
            }
        except Exception as e:
            self.logger.error(f"u68c0u7d22{data_type}u6570u636eu5931u8d25: {str(e)}")
            return {'success': False, 'message': f'u68c0u7d22{data_type}u6570u636eu5931u8d25: {str(e)}'}
    
    def retrieve_analysis_results(self, analysis_type=None, patient_id=None, session_id=None, limit=100):
        """u68c0u7d22u5206u6790u7ed3u679c
        
        Args:
            analysis_type (str, optional): u5206u6790u7c7bu578b
            patient_id (str, optional): u60a3u8005ID
            session_id (str, optional): u4f1au8bddID
            limit (int, optional): u8fd4u56deu7ed3u679cu7684u6700u5927u6570u91cf
        
        Returns:
            dict: u67e5u8be2u7ed3u679c
        """
        try:
            # u6784u5efau67e5u8be2u6761u4ef6
            query = {}
            
            if analysis_type:
                query['type'] = analysis_type
            
            if patient_id:
                query['patient_id'] = patient_id
            
            if session_id:
                query['session_id'] = session_id
            
            # u6267u884cu67e5u8be2
            results = list(database_manager.mongodb_db.analysis_results.find(query)
                          .sort('created_at', -1)
                          .limit(limit))
            
            # u5904u7406u7ed3u679c
            for result in results:
                result['_id'] = str(result['_id'])  # u8f6cu6362ObjectIdu4e3au5b57u7b26u4e32
            
            return {
                'success': True,
                'count': len(results),
                'results': results
            }
        except Exception as e:
            self.logger.error(f"\u68c0\u7d22\u5206\u6790\u7ed3\u679c\u5931\u8d25: {str(e)}")
            return {'success': False, 'message': f'\u68c0\u7d22\u5206\u6790\u7ed3\u679c\u5931\u8d25: {str(e)}'}
    
    def create_backup(self, backup_type='all'):
        """\u521b\u5efa\u6570\u636e\u5907\u4efd
        
        Args:
            backup_type (str, optional): \u5907\u4efd\u7c7b\u578b\uff0c'all'\uff0c'patient'\uff0c'ecg'\uff0c'analysis'\u7b49
        
        Returns:
            dict: \u5907\u4efd\u7ed3\u679c
        """
        if self.backup_in_progress:
            return {'success': False, 'message': '\u5df2\u6709\u5907\u4efd\u4efb\u52a1\u6b63\u5728\u8fdb\u884c'}
        
        try:
            # \u6807\u8bb0\u5907\u4efd\u72b6\u6001
            self.backup_in_progress = True
            
            # \u542f\u52a8\u5907\u4efd\u7ebf\u7a0b
            self.backup_thread = threading.Thread(
                target=self._backup_process,
                args=(backup_type,)
            )
            self.backup_thread.daemon = True
            self.backup_thread.start()
            
            return {
                'success': True,
                'message': f'\u5907\u4efd\u4efb\u52a1\u5df2\u542f\u52a8\uff0c\u7c7b\u578b: {backup_type}',
                'backup_type': backup_type,
                'started_at': datetime.now().isoformat()
            }
        except Exception as e:
            self.backup_in_progress = False
            self.logger.error(f"\u542f\u52a8\u5907\u4efd\u4efb\u52a1\u5931\u8d25: {str(e)}")
            return {'success': False, 'message': f'\u542f\u52a8\u5907\u4efd\u4efb\u52a1\u5931\u8d25: {str(e)}'}
    
    def create_archive(self, days_to_archive=30, archive_type='all'):
        """\u521b\u5efa\u6570\u636e\u5f52\u6863\uff08\u5c06\u65e7\u6570\u636e\u5f52\u6863\u5e76\u4ece\u6d3b\u52a8\u6570\u636e\u5e93\u4e2d\u79fb\u9664\uff09
        
        Args:
            days_to_archive (int, optional): \u5f52\u6863\u591a\u5c11\u5929\u524d\u7684\u6570\u636e
            archive_type (str, optional): \u5f52\u6863\u7c7b\u578b\uff0c'all'\uff0c'ecg'\uff0c'physiological'\uff0c'analysis'\u7b49
        
        Returns:
            dict: \u5f52\u6863\u7ed3\u679c
        """
        if self.archive_in_progress:
            return {'success': False, 'message': '\u5df2\u6709\u5f52\u6863\u4efb\u52a1\u6b63\u5728\u8fdb\u884c'}
        
        try:
            # \u6807\u8bb0\u5f52\u6863\u72b6\u6001
            self.archive_in_progress = True
            
            # \u542f\u52a8\u5f52\u6863\u7ebf\u7a0b
            self.archive_thread = threading.Thread(
                target=self._archive_process,
                args=(days_to_archive, archive_type)
            )
            self.archive_thread.daemon = True
            self.archive_thread.start()
            
            return {
                'success': True,
                'message': f'\u5f52\u6863\u4efb\u52a1\u5df2\u542f\u52a8\uff0c\u5f52\u6863{days_to_archive}\u5929\u524d\u7684{archive_type}\u6570\u636e',
                'archive_type': archive_type,
                'days_to_archive': days_to_archive,
                'started_at': datetime.now().isoformat()
            }
        except Exception as e:
            self.archive_in_progress = False
            self.logger.error(f"\u542f\u52a8\u5f52\u6863\u4efb\u52a1\u5931\u8d25: {str(e)}")
            return {'success': False, 'message': f'\u542f\u52a8\u5f52\u6863\u4efb\u52a1\u5931\u8d25: {str(e)}'}
    
    def get_backup_status(self):
        """\u83b7\u53d6\u5907\u4efd\u72b6\u6001
        
        Returns:
            dict: \u5907\u4efd\u72b6\u6001
        """
        status = {
            'backup_in_progress': self.backup_in_progress,
        }
        
        # \u83b7\u53d6\u5df2\u5b8c\u6210\u7684\u5907\u4efd\u5217\u8868
        try:
            backups = []
            for filename in os.listdir(self.backup_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.backup_dir, filename)
                    backups.append({
                        'filename': filename,
                        'size': os.path.getsize(file_path),
                        'created_at': datetime.fromtimestamp(os.path.getctime(file_path)).isoformat()
                    })
            
            status['backups'] = sorted(backups, key=lambda x: x['created_at'], reverse=True)
        except Exception as e:
            self.logger.error(f"\u83b7\u53d6\u5907\u4efd\u5217\u8868\u5931\u8d25: {str(e)}")
            status['backup_error'] = str(e)
        
        return {'success': True, 'status': status}
    
    def get_archive_status(self):
        """\u83b7\u53d6\u5f52\u6863\u72b6\u6001
        
        Returns:
            dict: \u5f52\u6863\u72b6\u6001
        """
        status = {
            'archive_in_progress': self.archive_in_progress,
        }
        
        # \u83b7\u53d6\u5df2\u5b8c\u6210\u7684\u5f52\u6863\u5217\u8868
        try:
            archives = []
            for filename in os.listdir(self.archive_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.archive_dir, filename)
                    archives.append({
                        'filename': filename,
                        'size': os.path.getsize(file_path),
                        'created_at': datetime.fromtimestamp(os.path.getctime(file_path)).isoformat()
                    })
            
            status['archives'] = sorted(archives, key=lambda x: x['created_at'], reverse=True)
        except Exception as e:
            self.logger.error(f"\u83b7\u53d6\u5f52\u6863\u5217\u8868\u5931\u8d25: {str(e)}")
            status['archive_error'] = str(e)
        
        return {'success': True, 'status': status}
    
    def _backup_process(self, backup_type):
        """\u5907\u4efd\u8fc7\u7a0b\u7684\u5b9e\u9645\u6267\u884c\u51fd\u6570
        
        Args:
            backup_type (str): \u5907\u4efd\u7c7b\u578b
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"{backup_type}_backup_{timestamp}.json"
            backup_filepath = os.path.join(self.backup_dir, backup_filename)
            
            # \u6839\u636e\u5907\u4efd\u7c7b\u578b\u83b7\u53d6\u6570\u636e
            data_to_backup = {}
            
            if backup_type == 'all' or backup_type == 'patient':
                patients = list(database_manager.mongodb_db.patients.find())
                for patient in patients:
                    patient['_id'] = str(patient['_id'])
                data_to_backup['patients'] = patients
            
            if backup_type == 'all' or backup_type == 'ecg':
                # \u53ea\u5907\u4efd\u6700\u8fd1\u7684\u6570\u636e\uff0c\u4ee5\u9632\u6587\u4ef6\u8fc7\u5927
                ecg_data = list(database_manager.mongodb_db.physiological_data.find({'type': 'ecg'}).sort('timestamp', -1).limit(1000))
                for item in ecg_data:
                    item['_id'] = str(item['_id'])
                    if isinstance(item.get('timestamp'), datetime):
                        item['timestamp'] = item['timestamp'].isoformat()
                    if isinstance(item.get('created_at'), datetime):
                        item['created_at'] = item['created_at'].isoformat()
                data_to_backup['ecg_data'] = ecg_data
            
            if backup_type == 'all' or backup_type == 'physiological':
                physio_data = list(database_manager.mongodb_db.physiological_data.find({'type': {'$ne': 'ecg'}}).sort('timestamp', -1).limit(1000))
                for item in physio_data:
                    item['_id'] = str(item['_id'])
                    if isinstance(item.get('timestamp'), datetime):
                        item['timestamp'] = item['timestamp'].isoformat()
                    if isinstance(item.get('created_at'), datetime):
                        item['created_at'] = item['created_at'].isoformat()
                data_to_backup['physiological_data'] = physio_data
            
            if backup_type == 'all' or backup_type == 'analysis':
                analysis_results = list(database_manager.mongodb_db.analysis_results.find().sort('created_at', -1).limit(1000))
                for item in analysis_results:
                    item['_id'] = str(item['_id'])
                    if isinstance(item.get('created_at'), datetime):
                        item['created_at'] = item['created_at'].isoformat()
                data_to_backup['analysis_results'] = analysis_results
            
            # \u5b58\u50a8\u4e3aJSON\u6587\u4ef6
            with open(backup_filepath, 'w', encoding='utf-8') as f:
                json.dump(data_to_backup, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"\u5907\u4efd\u6210\u529f: {backup_filename}")
        except Exception as e:
            self.logger.error(f"\u5907\u4efd\u8fc7\u7a0b\u5931\u8d25: {str(e)}")
        finally:
            self.backup_in_progress = False
    
    def _archive_process(self, days_to_archive, archive_type):
        """\u5f52\u6863\u8fc7\u7a0b\u7684\u5b9e\u9645\u6267\u884c\u51fd\u6570
        
        Args:
            days_to_archive (int): \u5f52\u6863\u591a\u5c11\u5929\u524d\u7684\u6570\u636e
            archive_type (str): \u5f52\u6863\u7c7b\u578b
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_archive)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_filename = f"{archive_type}_archive_{timestamp}.json"
            archive_filepath = os.path.join(self.archive_dir, archive_filename)
            
            data_to_archive = {}
            archived_counts = {}
            
            # \u5f52\u6863\u751f\u7406\u6570\u636e
            if archive_type == 'all' or archive_type == 'physiological' or archive_type == 'ecg':
                query = {'timestamp': {'$lt': cutoff_date}}
                
                if archive_type == 'ecg':
                    query['type'] = 'ecg'
                
                # \u67e5\u8be2\u9700\u8981\u5f52\u6863\u7684\u6570\u636e
                physio_data = list(database_manager.mongodb_db.physiological_data.find(query))
                
                # \u5904\u7406\u65f6\u95f4\u5b57\u6bb5\u4ee5\u4fbfJSON\u5e8f\u5217\u5316
                for item in physio_data:
                    item['_id'] = str(item['_id'])
                    if isinstance(item.get('timestamp'), datetime):
                        item['timestamp'] = item['timestamp'].isoformat()
                    if isinstance(item.get('created_at'), datetime):
                        item['created_at'] = item['created_at'].isoformat()
                
                data_to_archive['physiological_data'] = physio_data
                archived_counts['physiological_data'] = len(physio_data)
                
                # \u4ece\u6570\u636e\u5e93\u4e2d\u5220\u9664\u5df2\u5f52\u6863\u7684\u6570\u636e
                if physio_data:
                    result = database_manager.mongodb_db.physiological_data.delete_many(query)
                    self.logger.info(f"\u5220\u9664\u4e86{result.deleted_count}\u6761\u751f\u7406\u6570\u636e")
            
            # \u5f52\u6863\u5206\u6790\u7ed3\u679c
            if archive_type == 'all' or archive_type == 'analysis':
                query = {'created_at': {'$lt': cutoff_date}}
                
                # \u67e5\u8be2\u9700\u8981\u5f52\u6863\u7684\u5206\u6790\u7ed3\u679c
                analysis_results = list(database_manager.mongodb_db.analysis_results.find(query))
                
                # \u5904\u7406\u65f6\u95f4\u5b57\u6bb5\u4ee5\u4fbfJSON\u5e8f\u5217\u5316
                for item in analysis_results:
                    item['_id'] = str(item['_id'])
                    if isinstance(item.get('created_at'), datetime):
                        item['created_at'] = item['created_at'].isoformat()
                
                data_to_archive['analysis_results'] = analysis_results
                archived_counts['analysis_results'] = len(analysis_results)
                
                # \u4ece\u6570\u636e\u5e93\u4e2d\u5220\u9664\u5df2\u5f52\u6863\u7684\u6570\u636e
                if analysis_results:
                    result = database_manager.mongodb_db.analysis_results.delete_many(query)
                    self.logger.info(f"\u5220\u9664\u4e86{result.deleted_count}\u6761\u5206\u6790\u7ed3\u679c")
            
            # \u5b58\u50a8\u5f52\u6863\u6587\u4ef6
            with open(archive_filepath, 'w', encoding='utf-8') as f:
                json.dump(data_to_archive, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"\u5f52\u6863\u6210\u529f: {archive_filename}, \u5171\u5f52\u6863{sum(archived_counts.values())}\u6761\u6570\u636e")
        except Exception as e:
            self.logger.error(f"\u5f52\u6863\u8fc7\u7a0b\u5931\u8d25: {str(e)}")
        finally:
            self.archive_in_progress = False

# \u521d\u59cb\u5316\u5b58\u50a8\u670d\u52a1
storage_service = StorageService()
