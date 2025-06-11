# report_service.py

import os
import time
from datetime import datetime
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 非交互式后端
from ..data.database_manager import database_manager
import base64
import io
from fpdf import FPDF
import threading
import uuid
from dateutil import parser as date_parser

class ReportService:
    """
    报告生成服务，负责生成ECG分析报告
    """
    
    def __init__(self):
        """
        初始化报告生成服务
        """
        self.reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'reports')
        os.makedirs(self.reports_dir, exist_ok=True)
    
    def generate_ecg_report(self, patient_id, session_id, time_range=None):
        """
        生成ECG分析报告
        
        Args:
            patient_id (str): 患者ID
            session_id (str): 会话ID
            time_range (tuple, optional): 时间范围 (开始时间, 结束时间)
            
        Returns:
            dict: 报告生成结果
        """
        try:
            # 获取患者信息
            patient_info = self._get_patient_info(patient_id)
            if not patient_info:
                return {'success': False, 'message': '未找到患者信息'}
            
            # 查询ECG数据
            ecg_data, timestamps = self._query_ecg_data(patient_id, session_id, time_range)
            if not ecg_data or not timestamps:
                return {'success': False, 'message': '未找到ECG数据'}
            
            # 查询分析结果
            analysis_results = self._query_analysis_results(patient_id, session_id, time_range)
            
            # 获取报警信息
            alerts = self._query_alerts(patient_id, session_id, time_range)
            
            # 生成报告内容
            report_data = self._prepare_report_data(patient_info, ecg_data, timestamps, analysis_results, alerts)
            
            # 生成PDF报告
            report_file = self._generate_pdf_report(report_data)
            
            # 保存报告元数据到MongoDB
            report_id = self._save_report_metadata(patient_id, session_id, report_file)
            
            return {
                'success': True,
                'message': '报告生成成功',
                'report_id': report_id,
                'report_file': report_file
            }
        except Exception as e:
            return {'success': False, 'message': f'报告生成失败: {str(e)}'}
    
    def _get_patient_info(self, patient_id):
        """
        获取患者信息
        
        Args:
            patient_id (str): 患者ID
            
        Returns:
            dict: 患者信息
        """
        try:
            # 从MongoDB查询患者信息
            patient_data = database_manager.mongodb_db.patients.find_one({'_id': patient_id})
            if patient_data:
                # 去除MongoDB的_id字段，因为它不是JSON可序列化的
                if '_id' in patient_data:
                    patient_data['patient_id'] = str(patient_data['_id'])
                    del patient_data['_id']
                return patient_data
            return None
        except Exception as e:
            print(f"获取患者信息失败: {str(e)}")
            return None
            
    def _query_ecg_data(self, patient_id, session_id, time_range=None):
        """
        查询ECG数据
        
        Args:
            patient_id (str): 患者ID
            session_id (str): 会话ID
            time_range (tuple, optional): 时间范围 (开始时间, 结束时间)
            
        Returns:
            tuple: (ecg_data, timestamps) - ECG数据和时间戳
        """
        try:
            # 构建查询条件
            query = f'from(bucket: "{database_manager.influxdb_bucket}") '
            query += f'|> range(start: -7d) '
            
            # 如果指定了时间范围，则使用指定的范围
            if time_range and len(time_range) == 2:
                start_time, end_time = time_range
                if isinstance(start_time, str):
                    start_time = date_parser.parse(start_time)
                if isinstance(end_time, str):
                    end_time = date_parser.parse(end_time)
                
                query = f'from(bucket: "{database_manager.influxdb_bucket}") '
                query += f'|> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()}) '
            
            # 添加过滤条件
            query += f'|> filter(fn: (r) => r["patient_id"] == "{patient_id}") '
            if session_id:
                query += f'|> filter(fn: (r) => r["session_id"] == "{session_id}") '
            
            # 按时间排序并限制数量以防数据过大
            query += f'|> sort(columns: ["_time"]) '
            query += f'|> limit(n: 5000) '
            
            # 执行查询
            tables = database_manager.influxdb_client.query_api().query(query, org=database_manager.influxdb_org)
            
            # 处理结果
            ecg_data = {i: [] for i in range(12)}  # 12个导联
            timestamps = []
            
            for table in tables:
                for record in table.records:
                    # 记录时间戳
                    if not timestamps or record.get_time() not in timestamps:
                        timestamps.append(record.get_time())
                    
                    # 根据导联索引存储数据
                    lead_index = record.values.get('lead_index', 0)
                    if lead_index < 12:
                        ecg_data[lead_index].append(record.values.get('_value', 0))
            
            # 转换为列表格式
            result_data = [ecg_data[i] for i in range(12)]
            
            return result_data, timestamps
        except Exception as e:
            print(f"查询ECG数据失败: {str(e)}")
            return None, None
    
    def _query_analysis_results(self, patient_id, session_id, time_range=None):
        """
        查询分析结果
        
        Args:
            patient_id (str): 患者ID
            session_id (str): 会话ID
            time_range (tuple, optional): 时间范围 (开始时间, 结束时间)
            
        Returns:
            list: 分析结果列表
        """
        try:
            # 构建查询条件
            query = {'patient_id': patient_id}
            
            if session_id:
                query['session_id'] = session_id
                
            # 如果指定了时间范围
            if time_range and len(time_range) == 2:
                start_time, end_time = time_range
                if isinstance(start_time, str):
                    start_time = date_parser.parse(start_time)
                if isinstance(end_time, str):
                    end_time = date_parser.parse(end_time)
                    
                query['timestamp'] = {
                    '$gte': start_time,
                    '$lte': end_time
                }
            
            # 执行查询，按时间排序
            results = list(database_manager.mongodb_db.ecg_analysis.find(
                query,
                {'_id': 0}
            ).sort('timestamp', -1).limit(100))
            
            return results
        except Exception as e:
            print(f"查询分析结果失败: {str(e)}")
            return []
    
    def _query_alerts(self, patient_id, session_id, time_range=None):
        """
        查询报警信息
        
        Args:
            patient_id (str): 患者ID
            session_id (str): 会话ID
            time_range (tuple, optional): 时间范围 (开始时间, 结束时间)
            
        Returns:
            list: 报警信息列表
        """
        try:
            # 构建查询条件
            query = {'patient_id': patient_id}
            
            if session_id:
                query['session_id'] = session_id
                
            # 如果指定了时间范围
            if time_range and len(time_range) == 2:
                start_time, end_time = time_range
                if isinstance(start_time, str):
                    start_time = date_parser.parse(start_time)
                if isinstance(end_time, str):
                    end_time = date_parser.parse(end_time)
                    
                query['timestamp'] = {
                    '$gte': start_time,
                    '$lte': end_time
                }
            
            # 执行查询，按时间排序，按严重程度过滤
            alerts = list(database_manager.mongodb_db.alerts.find(
                query,
                {'_id': 0}
            ).sort('timestamp', -1).sort('severity', -1).limit(50))
            
            return alerts
        except Exception as e:
            print(f"查询报警信息失败: {str(e)}")
            return []
    
    def _prepare_report_data(self, patient_info, ecg_data, timestamps, analysis_results, alerts):
        """
        准备报告数据
        
        Args:
            patient_info (dict): 患者信息
            ecg_data (list): ECG数据
            timestamps (list): 时间戳
            analysis_results (list): 分析结果
            alerts (list): 报警信息
            
        Returns:
            dict: 报告数据
        """
        # 生成报告数据
        report_data = {
            'patient_info': patient_info,
            'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'report_id': str(uuid.uuid4()),
            'ecg_data': {
                'leads': ecg_data,
                'timestamps': [t.isoformat() if hasattr(t, 'isoformat') else str(t) for t in timestamps],
                'duration': len(timestamps) / 500 if timestamps else 0  # 假设采样率为500Hz
            },
            'analysis_summary': self._generate_analysis_summary(analysis_results),
            'alerts_summary': self._generate_alerts_summary(alerts),
            'charts': self._generate_charts(ecg_data, timestamps)
        }
        
        return report_data
    
    def _generate_analysis_summary(self, analysis_results):
        """
        生成分析摘要
        
        Args:
            analysis_results (list): 分析结果
            
        Returns:
            dict: 分析摘要
        """
        if not analysis_results:
            return {
                'heart_rate': {
                    'avg': 0,
                    'min': 0,
                    'max': 0
                },
                'hrv': {
                    'sdnn': 0,
                    'rmssd': 0,
                    'pnn50': 0
                },
                'arrhythmia': {
                    'detected': False,
                    'types': [],
                    'count': 0
                }
            }
        
        # 心率统计
        heart_rates = [r.get('heart_rate', 0) for r in analysis_results if r.get('heart_rate', 0) > 0]
        avg_hr = sum(heart_rates) / len(heart_rates) if heart_rates else 0
        min_hr = min(heart_rates) if heart_rates else 0
        max_hr = max(heart_rates) if heart_rates else 0
        
        # 心率变异性指标
        hrv_metrics = {}
        for r in analysis_results:
            if r.get('hrv_metrics') and r['hrv_metrics'].get('success', False):
                metrics = r['hrv_metrics']
                for key in ['sdnn', 'rmssd', 'pnn50']:
                    if key in metrics:
                        hrv_metrics[key] = hrv_metrics.get(key, []) + [metrics[key]]
        
        avg_sdnn = sum(hrv_metrics.get('sdnn', [0])) / len(hrv_metrics.get('sdnn', [1])) if hrv_metrics.get('sdnn') else 0
        avg_rmssd = sum(hrv_metrics.get('rmssd', [0])) / len(hrv_metrics.get('rmssd', [1])) if hrv_metrics.get('rmssd') else 0
        avg_pnn50 = sum(hrv_metrics.get('pnn50', [0])) / len(hrv_metrics.get('pnn50', [1])) if hrv_metrics.get('pnn50') else 0
        
        # 心律失常
        arrhythmia_types = set()
        arrhythmia_count = 0
        for r in analysis_results:
            if r.get('arrhythmia') and r['arrhythmia'].get('detected', False):
                arrhythmia_count += 1
                types = r['arrhythmia'].get('arrhythmia_types', [])
                for t in types:
                    arrhythmia_types.add(t)
        
        return {
            'heart_rate': {
                'avg': round(avg_hr, 1),
                'min': round(min_hr, 1),
                'max': round(max_hr, 1)
            },
            'hrv': {
                'sdnn': round(avg_sdnn, 2),
                'rmssd': round(avg_rmssd, 2),
                'pnn50': round(avg_pnn50, 2)
            },
            'arrhythmia': {
                'detected': len(arrhythmia_types) > 0,
                'types': list(arrhythmia_types),
                'count': arrhythmia_count
            }
        }
    
    def _generate_alerts_summary(self, alerts):
        """
        生成报警摘要
        
        Args:
            alerts (list): 报警信息
            
        Returns:
            dict: 报警摘要
        """
        if not alerts:
            return {
                'count': 0,
                'severity': {
                    'high': 0,
                    'medium': 0,
                    'low': 0
                },
                'types': {}
            }
        
        # 统计不同严重程度的报警数量
        severity_count = {
            'high': 0,
            'medium': 0,
            'low': 0
        }
        
        # 统计不同类型的报警数量
        type_count = {}
        
        for alert in alerts:
            severity = alert.get('severity', 'low')
            severity_count[severity] = severity_count.get(severity, 0) + 1
            
            alert_type = alert.get('type', 'unknown')
            type_count[alert_type] = type_count.get(alert_type, 0) + 1
        
        return {
            'count': len(alerts),
            'severity': severity_count,
            'types': type_count
        }
    
    def _generate_charts(self, ecg_data, timestamps):
        """
        生成ECG图表
        
        Args:
            ecg_data (list): ECG数据
            timestamps (list): 时间戳
            
        Returns:
            dict: 图表数据字典
        """
        charts = {}
        
        try:
            # 确保有数据可用
            if not ecg_data or not any(ecg_data) or not timestamps:
                return charts
            
            # 选择有效导联并限制数据点
            valid_leads = []
            for i, lead_data in enumerate(ecg_data):
                if lead_data and len(lead_data) > 10:  # 至少10个点才绘图
                    valid_leads.append((i, lead_data))
            
            if not valid_leads:
                return charts
            
            # 如果数据点过多，进行采样
            max_points = 1000
            
            for lead_index, lead_data in valid_leads:
                # 采样以减少点数
                if len(lead_data) > max_points:
                    step = len(lead_data) // max_points
                    lead_data = lead_data[::step][:max_points]
                    
                # 创建图表
                fig = plt.figure(figsize=(10, 4))
                plt.plot(lead_data, 'b-')
                plt.title(f'ECG Lead {lead_index+1}')
                plt.xlabel('Samples')
                plt.ylabel('Amplitude (mV)')
                plt.grid(True)
                
                # 转换为base64图片
                buf = io.BytesIO()
                fig.savefig(buf, format='png', dpi=100)
                buf.seek(0)
                img_str = base64.b64encode(buf.read()).decode('utf-8')
                plt.close(fig)
                
                # 保存到图表字典
                charts[f'lead_{lead_index}'] = img_str
                
                # 限制图表数量
                if len(charts) >= 4:  # 最多生抄4个导联的图表
                    break
                    
            return charts
        except Exception as e:
            print(f"生成ECG图表失败: {str(e)}")
            return {}
    
    def _generate_pdf_report(self, report_data):
        """
        生成PDF报告
        
        Args:
            report_data (dict): 报告数据
            
        Returns:
            str: 报告文件路径
        """
        try:
            # 创建PDF文档
            pdf = FPDF()
            pdf.add_page()
            
            # 设置字体
            pdf.add_font('simhei', '', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'fonts', 'simhei.ttf'), uni=True)
            pdf.set_font('simhei', '', 12)
            
            # 报告标题
            pdf.set_font('simhei', '', 18)
            pdf.cell(0, 10, 'ECG心电图分析报告', 0, 1, 'C')
            pdf.ln(5)
            
            # 报告信息
            pdf.set_font('simhei', '', 12)
            pdf.cell(0, 8, f"报告编号: {report_data.get('report_id', 'Unknown')}", 0, 1)
            pdf.cell(0, 8, f"生成时间: {report_data.get('report_date', 'Unknown')}", 0, 1)
            pdf.ln(5)
            
            # 患者信息
            patient_info = report_data.get('patient_info', {})
            pdf.set_font('simhei', '', 14)
            pdf.cell(0, 10, '患者信息', 0, 1, 'L')
            pdf.set_font('simhei', '', 12)
            pdf.cell(0, 8, f"姓名: {patient_info.get('name', 'Unknown')}", 0, 1)
            pdf.cell(0, 8, f"性别: {patient_info.get('gender', 'Unknown')}", 0, 1)
            pdf.cell(0, 8, f"年龄: {patient_info.get('age', 'Unknown')}", 0, 1)
            pdf.cell(0, 8, f"ID: {patient_info.get('patient_id', 'Unknown')}", 0, 1)
            pdf.ln(5)
            
            # 分析结果摘要
            analysis = report_data.get('analysis_summary', {})
            pdf.set_font('simhei', '', 14)
            pdf.cell(0, 10, '分析结果摘要', 0, 1, 'L')
            pdf.set_font('simhei', '', 12)
            
            # 心率信息
            heart_rate = analysis.get('heart_rate', {})
            pdf.cell(0, 8, f"平均心率: {heart_rate.get('avg', 0)} bpm", 0, 1)
            pdf.cell(0, 8, f"最小心率: {heart_rate.get('min', 0)} bpm", 0, 1)
            pdf.cell(0, 8, f"最大心率: {heart_rate.get('max', 0)} bpm", 0, 1)
            
            # 心率变异性
            hrv = analysis.get('hrv', {})
            pdf.cell(0, 8, f"SDNN: {hrv.get('sdnn', 0)} ms", 0, 1)
            pdf.cell(0, 8, f"RMSSD: {hrv.get('rmssd', 0)} ms", 0, 1)
            pdf.cell(0, 8, f"pNN50: {hrv.get('pnn50', 0)}%", 0, 1)
            
            # 心律失常
            arrhythmia = analysis.get('arrhythmia', {})
            arrhythmia_types = ", ".join(arrhythmia.get('types', []))
            pdf.cell(0, 8, f"心律失常: {'检测到' if arrhythmia.get('detected', False) else '未检测到'}", 0, 1)
            if arrhythmia.get('detected', False):
                pdf.cell(0, 8, f"心律失常类型: {arrhythmia_types}", 0, 1)
                pdf.cell(0, 8, f"心律失常次数: {arrhythmia.get('count', 0)}", 0, 1)
            pdf.ln(5)
            
            # 报警摘要
            alerts = report_data.get('alerts_summary', {})
            pdf.set_font('simhei', '', 14)
            pdf.cell(0, 10, '报警信息摘要', 0, 1, 'L')
            pdf.set_font('simhei', '', 12)
            pdf.cell(0, 8, f"报警总数: {alerts.get('count', 0)}", 0, 1)
            
            severity = alerts.get('severity', {})
            pdf.cell(0, 8, f"高严重度报警: {severity.get('high', 0)}", 0, 1)
            pdf.cell(0, 8, f"中严重度报警: {severity.get('medium', 0)}", 0, 1)
            pdf.cell(0, 8, f"低严重度报警: {severity.get('low', 0)}", 0, 1)
            pdf.ln(5)
            
            # 添加ECG图表
            charts = report_data.get('charts', {})
            if charts:
                pdf.set_font('simhei', '', 14)
                pdf.cell(0, 10, 'ECG波形图', 0, 1, 'L')
                pdf.ln(2)
                
                for lead_name, img_str in charts.items():
                    lead_num = lead_name.split('_')[-1]
                    img_file = os.path.join(self.reports_dir, f"{report_data['report_id']}_{lead_name}.png")
                    
                    # 保存图片到文件
                    with open(img_file, 'wb') as f:
                        f.write(base64.b64decode(img_str))
                    
                    # 添加到PDF
                    pdf.cell(0, 8, f"导联 {int(lead_num)+1}", 0, 1, 'L')
                    pdf.image(img_file, x=10, w=180)
                    pdf.ln(5)
            
            # 保存PDF
            report_file = os.path.join(self.reports_dir, f"{report_data['report_id']}.pdf")
            pdf.output(report_file)
            
            return report_file
            
        except Exception as e:
            print(f"生成PDF报告失败: {str(e)}")
            return None
    
    def _save_report_metadata(self, patient_id, session_id, report_file):
        """
        保存报告元数据到MongoDB
        
        Args:
            patient_id (str): 患者ID
            session_id (str): 会话ID
            report_file (str): 报告文件路径
            
        Returns:
            str: 报告ID
        """
        try:
            # 准备元数据
            report_id = os.path.basename(report_file).split('.')[0]
            metadata = {
                'report_id': report_id,
                'patient_id': patient_id,
                'session_id': session_id,
                'created_at': datetime.now(),
                'file_path': report_file,
                'file_name': os.path.basename(report_file)
            }
            
            # 保存到MongoDB
            result = database_manager.mongodb_db.reports.insert_one(metadata)
            return report_id
        except Exception as e:
            print(f"保存报告元数据失败: {str(e)}")
            return None
    
    def get_report(self, report_id):
        """
        获取报告信息
        
        Args:
            report_id (str): 报告ID
            
        Returns:
            dict: 报告信息
        """
        try:
            # 从MongoDB查询报告元数据
            report_data = database_manager.mongodb_db.reports.find_one({'report_id': report_id})
            if not report_data:
                return {'success': False, 'message': '未找到报告'}
            
            # 检查文件是否存在
            file_path = report_data.get('file_path')
            if not file_path or not os.path.exists(file_path):
                return {'success': False, 'message': '报告文件不存在'}
            
            # 去除MongoDB的_id字段
            if '_id' in report_data:
                report_data['id'] = str(report_data['_id'])
                del report_data['_id']
            
            return {
                'success': True,
                'report': report_data
            }
        except Exception as e:
            return {'success': False, 'message': f'获取报告失败: {str(e)}'}

# 初始化报告服务
report_service = ReportService()
