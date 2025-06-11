# alert_service.py

import time
from datetime import datetime
from ..data.database_manager import database_manager
import threading
import json

class AlertService:
    """
    u62a5u8b66u670du52a1u7c7buff0cu8d1fu8d23u7ed9u4e0du540cu7c7bu578bu7684u5f02u5e38u751fu6210u62a5u8b66u5e76u53d1u9001u901au77e5
    """
    
    def __init__(self, socketio=None):
        """
        u521du59cbu5316u62a5u8b66u670du52a1
        
        Args:
            socketio: SocketIOu5b9eu4f8buff0cu7528u4e8eu5411u524du7aefu53d1u9001u5b9eu65f6u901au77e5
        """
        self.socketio = socketio
        self.alert_thresholds = {
            'heart_rate_high': 100,  # u5fc3u7387u8fc7u9ad8u9608u503c
            'heart_rate_low': 50,    # u5fc3u7387u8fc7u4f4eu9608u503c
            'qrs_interval_high': 0.45,  # QRSu95f4u9694u8fc7u957fu9608u503c (u79d2)
            'qrs_interval_low': 0.10,   # QRSu95f4u9694u8fc7u77edu9608u503c (u79d2)
            'st_elevation': 0.2,        # STu6bb5u62acu9ad8u9608u503c (mV)
            'st_depression': -0.1,       # STu6bb5u538bu4f4eu9608u503c (mV)
            'arrhythmia_threshold': 3    # u5fc3u5f8bu5931u5e38u68c0u6d4bu9608u503c (u6bcfu520630u79d2u5fc3u5f8bu5931u5e38u6b21u6570)
        }
        self.alert_history = {}  # u6bcfu4e2au60a3u8005u7684u62a5u8b66u5386u53f2
        self.alert_cooldown = 60  # u540cu7c7bu578bu62a5u8b66u7684u51b7u5374u65f6u95f4 (u79d2)
        self.monitoring_thread = None
        self.monitoring_active = False
    
    def set_threshold(self, threshold_name, value):
        """
        u8bbeu7f6eu62a5u8b66u9608u503c
        
        Args:
            threshold_name (str): u9608u503cu540du79f0
            value (float): u9608u503cu6570u503c
        """
        if threshold_name in self.alert_thresholds:
            self.alert_thresholds[threshold_name] = value
            return {'success': True, 'message': f'u5df2u8bbeu7f6e{threshold_name}u9608u503cu4e3a{value}'}
        else:
            return {'success': False, 'message': f'u672au627eu5230u9608u503c{threshold_name}'}
    
    def get_thresholds(self):
        """
        u83b7u53d6u6240u6709u62a5u8b66u9608u503c
        
        Returns:
            dict: u5f53u524du62a5u8b66u9608u503c
        """
        return {'success': True, 'thresholds': self.alert_thresholds}
    
    def check_heart_rate(self, patient_id, heart_rate):
        """
        u68c0u67e5u5fc3u7387u662fu5426u8d85u51fau8303u56f4
        
        Args:
            patient_id (str): u60a3u8005ID
            heart_rate (float): u5fc3u7387u503c
            
        Returns:
            dict: u62a5u8b66u4fe1u606fuff08u5982u679cu89e6u53d1u62a5u8b66uff09
        """
        alerts = []
        
        # u5fc3u7387u8fc7u9ad8u68c0u6d4b
        if heart_rate > self.alert_thresholds['heart_rate_high']:
            alert_key = f'{patient_id}_heart_rate_high'
            if self._can_send_alert(alert_key):
                alert_info = {
                    'type': 'heart_rate_high',
                    'severity': 'medium',
                    'message': f'u5fc3u7387u8fc7u9ad8 ({heart_rate} bpm)',
                    'value': heart_rate,
                    'threshold': self.alert_thresholds['heart_rate_high'],
                    'timestamp': datetime.now().isoformat()
                }
                alerts.append(alert_info)
                self._record_alert(alert_key)
        
        # u5fc3u7387u8fc7u4f4eu68c0u6d4b
        elif heart_rate < self.alert_thresholds['heart_rate_low'] and heart_rate > 0:  # u786eu4fddu975eu96f6u5fc3u7387
            alert_key = f'{patient_id}_heart_rate_low'
            if self._can_send_alert(alert_key):
                alert_info = {
                    'type': 'heart_rate_low',
                    'severity': 'high',  # u5fc3u7387u8fc7u4f4eu901au5e38u66f4u4e25u91cd
                    'message': f'u5fc3u7387u8fc7u4f4e ({heart_rate} bpm)',
                    'value': heart_rate,
                    'threshold': self.alert_thresholds['heart_rate_low'],
                    'timestamp': datetime.now().isoformat()
                }
                alerts.append(alert_info)
                self._record_alert(alert_key)
        
        return alerts
    
    def check_arrhythmia(self, patient_id, arrhythmia_data):
        """
        u68c0u67e5u5fc3u5f8bu5931u5e38
        
        Args:
            patient_id (str): u60a3u8005ID
            arrhythmia_data (dict): u5fc3u5f8bu5931u5e38u6570u636e
            
        Returns:
            dict: u62a5u8b66u4fe1u606fuff08u5982u679cu89e6u53d1u62a5u8b66uff09
        """
        alerts = []
        
        if not arrhythmia_data:
            return alerts
            
        if arrhythmia_data.get('detected', False) and arrhythmia_data.get('severity') == 'high':
            alert_key = f'{patient_id}_arrhythmia'
            if self._can_send_alert(alert_key):
                arrhythmia_types = arrhythmia_data.get('arrhythmia_types', [])
                alert_info = {
                    'type': 'arrhythmia',
                    'severity': 'high',
                    'message': f'u68c0u6d4bu5230u4e25u91cdu5fc3u5f8bu5931u5e38: {", ".join(arrhythmia_types)}',
                    'details': arrhythmia_data,
                    'timestamp': datetime.now().isoformat()
                }
                alerts.append(alert_info)
                self._record_alert(alert_key)
        
        return alerts
    
    def check_st_deviation(self, patient_id, st_deviation):
        """
        u68c0u67e5STu6bb5u504fu5dee
        
        Args:
            patient_id (str): u60a3u8005ID
            st_deviation (float): STu6bb5u504fu5deeu503c (mV)
            
        Returns:
            dict: u62a5u8b66u4fe1u606fuff08u5982u679cu89e6u53d1u62a5u8b66uff09
        """
        alerts = []
        
        # STu6bb5u62acu9ad8u68c0u6d4b
        if st_deviation > self.alert_thresholds['st_elevation']:
            alert_key = f'{patient_id}_st_elevation'
            if self._can_send_alert(alert_key):
                alert_info = {
                    'type': 'st_elevation',
                    'severity': 'high',
                    'message': f'u68c0u6d4bu5230STu6bb5u62acu9ad8 ({st_deviation:.2f} mV)',
                    'value': st_deviation,
                    'threshold': self.alert_thresholds['st_elevation'],
                    'timestamp': datetime.now().isoformat()
                }
                alerts.append(alert_info)
                self._record_alert(alert_key)
        
        # STu6bb5u538bu4f4eu68c0u6d4b
        elif st_deviation < self.alert_thresholds['st_depression']:
            alert_key = f'{patient_id}_st_depression'
            if self._can_send_alert(alert_key):
                alert_info = {
                    'type': 'st_depression',
                    'severity': 'medium',
                    'message': f'u68c0u6d4bu5230STu6bb5u538bu4f4e ({st_deviation:.2f} mV)',
                    'value': st_deviation,
                    'threshold': self.alert_thresholds['st_depression'],
                    'timestamp': datetime.now().isoformat()
                }
                alerts.append(alert_info)
                self._record_alert(alert_key)
        
        return alerts
    
    def process_ecg_analysis(self, patient_id, analysis_result):
        """
        u5904u7406ECGu5206u6790u7ed3u679cuff0cu68c0u67e5u662fu5426u9700u8981u89e6u53d1u62a5u8b66
        
        Args:
            patient_id (str): u60a3u8005ID
            analysis_result (dict): ECGu5206u6790u7ed3u679c
            
        Returns:
            list: u62a5u8b66u5217u8868
        """
        alerts = []
        
        # u5fc3u7387u68c0u67e5
        if 'heart_rate' in analysis_result:
            heart_rate_alerts = self.check_heart_rate(patient_id, analysis_result['heart_rate'])
            alerts.extend(heart_rate_alerts)
        
        # u5fc3u5f8bu5931u5e38u68c0u67e5
        if 'arrhythmia' in analysis_result and analysis_result['arrhythmia']:
            arrhythmia_alerts = self.check_arrhythmia(patient_id, analysis_result['arrhythmia'])
            alerts.extend(arrhythmia_alerts)
        
        # STu6bb5u68c0u67e5uff08u5982u679cu6709u5206u6790u6570u636euff09
        if 'st_deviations' in analysis_result:
            for lead, st_value in analysis_result['st_deviations'].items():
                st_alerts = self.check_st_deviation(patient_id, st_value)
                for alert in st_alerts:
                    alert['lead'] = lead  # u6dfbu52a0u5bfcu8054u4fe1u606f
                alerts.extend(st_alerts)
        
        # u5982u679cu6709u62a5u8b66uff0cu5b58u50a8u5230u6570u636eu5e93u5e76u53d1u9001u901au77e5
        if alerts:
            self._store_alerts(patient_id, alerts)
            self._send_alerts(patient_id, alerts)
        
        return alerts
    
    def _can_send_alert(self, alert_key):
        """
        u68c0u67e5u662fu5426u53efu4ee5u53d1u9001u62a5u8b66uff08u67e5u770bu51b7u5374u65f6u95f4uff09
        
        Args:
            alert_key (str): u62a5u8b66u952eu503c
            
        Returns:
            bool: u662fu5426u53efu4ee5u53d1u9001u62a5u8b66
        """
        current_time = time.time()
        last_alert_time = self.alert_history.get(alert_key, 0)
        
        # u5982u679cu4e0au6b21u62a5u8b66u6bd4u51b7u5374u65f6u95f4u66f4u65e9uff0cu5219u53efu4ee5u53d1u9001u65b0u62a5u8b66
        return (current_time - last_alert_time) > self.alert_cooldown
    
    def _record_alert(self, alert_key):
        """
        u8bb0u5f55u62a5u8b66u65f6u95f4
        
        Args:
            alert_key (str): u62a5u8b66u952eu503c
        """
        self.alert_history[alert_key] = time.time()
    
    def _store_alerts(self, patient_id, alerts):
        """
        u5c06u62a5u8b66u5b58u50a8u5230u6570u636eu5e93
        
        Args:
            patient_id (str): u60a3u8005ID
            alerts (list): u62a5u8b66u5217u8868
        """
        try:
            for alert in alerts:
                alert_doc = alert.copy()
                alert_doc['patient_id'] = patient_id
                database_manager.mongodb_db.alerts.insert_one(alert_doc)
        except Exception as e:
            print(f"u5b58u50a8u62a5u8b66u5230u6570u636eu5e93u5931u8d25: {str(e)}")
    
    def _send_alerts(self, patient_id, alerts):
        """
        u53d1u9001u62a5u8b66u901au77e5
        
        Args:
            patient_id (str): u60a3u8005ID
            alerts (list): u62a5u8b66u5217u8868
        """
        if self.socketio:
            for alert in alerts:
                # u53d1u9001u5230u524du7aef
                self.socketio.emit('alert', {
                    'patient_id': patient_id,
                    'alert': alert
                })
                
                # u5bf9u4e25u91cdu7684u62a5u8b66u53d1u9001u6d88u606fu901au77e5
                if alert.get('severity') == 'high':
                    self.socketio.emit('notification', {
                        'message': f"u7d27u6025u60c5u51b5: {alert.get('message')}",
                        'type': 'error'
                    })
                else:
                    self.socketio.emit('notification', {
                        'message': alert.get('message'),
                        'type': 'warning'
                    })
    
    def start_monitoring(self):
        """
        u542fu52a8u62a5u8b66u76d1u63a7u7ebfu7a0b
        """
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_worker)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
            return {'success': True, 'message': 'u62a5u8b66u76d1u63a7u5df2u542fu52a8'}
        return {'success': False, 'message': 'u62a5u8b66u76d1u63a7u5df2u5728u8fd0u884c'}
    
    def stop_monitoring(self):
        """
        u505cu6b62u62a5u8b66u76d1u63a7u7ebfu7a0b
        """
        if self.monitoring_active:
            self.monitoring_active = False
            if self.monitoring_thread:
                self.monitoring_thread.join(timeout=2.0)
            return {'success': True, 'message': 'u62a5u8b66u76d1u63a7u5df2u505cu6b62'}
        return {'success': False, 'message': 'u62a5u8b66u76d1u63a7u5df2u7ecfu505cu6b62'}
    
    def _monitoring_worker(self):
        """
        u62a5u8b66u76d1u63a7u5de5u4f5cu7ebfu7a0b
        """
        while self.monitoring_active:
            try:
                # u67e5u8be2u6700u65b0u7684ECGu5206u6790u7ed3u679c
                latest_analyses = database_manager.mongodb_db.ecg_analysis.find(
                    {'processed_for_alerts': {'$ne': True}}
                ).limit(10)
                
                for analysis in latest_analyses:
                    patient_id = analysis.get('patient_id', 'unknown')
                    self.process_ecg_analysis(patient_id, analysis)
                    
                    # u6807u8bb0u4e3au5df2u5904u7406
                    database_manager.mongodb_db.ecg_analysis.update_one(
                        {'_id': analysis['_id']},
                        {'$set': {'processed_for_alerts': True}}
                    )
            except Exception as e:
                print(f"u62a5u8b66u76d1u63a7u7ebfu7a0bu9519u8bef: {str(e)}")
            
            # u7b49u5f85u4e00u6bb5u65f6u95f4u518du68c0u67e5
            time.sleep(5)
    
    def get_patient_alerts(self, patient_id, limit=50, offset=0, severity=None):
        """
        u83b7u53d6u6307u5b9au60a3u8005u7684u62a5u8b66u5386u53f2
        
        Args:
            patient_id (str): u60a3u8005ID
            limit (int): u8fd4u56deu6570u91cfu9650u5236
            offset (int): u504fu79fbu91cf
            severity (str, optional): u4e25u91cdu7a0bu5ea6u8fc7u6ee4
            
        Returns:
            dict: u62a5u8b66u5217u8868
        """
        try:
            query = {'patient_id': patient_id}
            if severity:
                query['severity'] = severity
                
            # u6309u65f6u95f4u964du5e8fu6392u5e8fuff0cu8fd4u56deu6700u8fd1u7684u62a5u8b66
            alerts = list(database_manager.mongodb_db.alerts.find(
                query,
                {'_id': 0}
            ).sort('timestamp', -1).skip(offset).limit(limit))
            
            # u8f6cu6362u6570u636eu4e3aJSONu53efu5e8fu5217u5316u683cu5f0f
            for alert in alerts:
                for key, value in alert.items():
                    if isinstance(value, datetime):
                        alert[key] = value.isoformat()
            
            total_count = database_manager.mongodb_db.alerts.count_documents(query)
            
            return {
                'success': True,
                'alerts': alerts,
                'total': total_count,
                'limit': limit,
                'offset': offset
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'u83b7u53d6u62a5u8b66u5931u8d25: {str(e)}'
            }

# u521du59cbu5316u62a5u8b66u670du52a1
alert_service = None

def init_alert_service(socketio):
    """
    u521du59cbu5316u62a5u8b66u670du52a1
    """
    global alert_service
    alert_service = AlertService(socketio)
    return alert_service

def get_alert_service():
    """
    u83b7u53d6u62a5u8b66u670du52a1u5b9eu4f8b
    """
    global alert_service
    return alert_service
