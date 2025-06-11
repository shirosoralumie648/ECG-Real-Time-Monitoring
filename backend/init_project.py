# init_project.py

import os
import sys

def ensure_directory_exists(directory):
    """确保目录存在，如果不存在则创建
    
    Args:
        directory (str): 目录路径
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"创建目录: {directory}")
    else:
        print(f"目录已存在: {directory}")

def init_project_structure():
    """初始化项目目录结构"""
    # 获取项目根目录
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 定义需要创建的目录
    directories = [
        # 后端目录
        os.path.join(root_dir, 'backend', 'api'),
        os.path.join(root_dir, 'backend', 'services'),
        os.path.join(root_dir, 'backend', 'data', 'models'),
        os.path.join(root_dir, 'backend', 'devices'),
        os.path.join(root_dir, 'backend', 'processing'),
        os.path.join(root_dir, 'backend', 'utils'),
        
        # 前端目录
        os.path.join(root_dir, 'frontend', 'static', 'css'),
        os.path.join(root_dir, 'frontend', 'static', 'js'),
        os.path.join(root_dir, 'frontend', 'static', 'images'),
        os.path.join(root_dir, 'frontend', 'templates'),
        
        # 数据目录
        os.path.join(root_dir, 'backend', 'data', 'raw'),
        os.path.join(root_dir, 'backend', 'data', 'processed'),
        os.path.join(root_dir, 'backend', 'data', 'logs'),
        
        # 文档目录
        os.path.join(root_dir, 'docs'),
        
        # 测试目录
        os.path.join(root_dir, 'tests', 'unit'),
        os.path.join(root_dir, 'tests', 'integration'),
    ]
    
    # 创建目录
    for directory in directories:
        ensure_directory_exists(directory)
    
    print("项目目录结构初始化完成！")

# 创建必要的初始化文件
def create_init_files():
    """创建必要的__init__.py文件"""
    # 获取项目根目录
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 定义需要创建__init__.py的目录
    init_directories = [
        os.path.join(root_dir, 'backend'),
        os.path.join(root_dir, 'backend', 'api'),
        os.path.join(root_dir, 'backend', 'services'),
        os.path.join(root_dir, 'backend', 'data'),
        os.path.join(root_dir, 'backend', 'data', 'models'),
        os.path.join(root_dir, 'backend', 'devices'),
        os.path.join(root_dir, 'backend', 'processing'),
        os.path.join(root_dir, 'backend', 'utils'),
        os.path.join(root_dir, 'tests'),
        os.path.join(root_dir, 'tests', 'unit'),
        os.path.join(root_dir, 'tests', 'integration'),
    ]
    
    # 创建__init__.py文件
    for directory in init_directories:
        init_file = os.path.join(directory, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write('# 自动生成的初始化文件\n')
            print(f"创建初始化文件: {init_file}")
        else:
            print(f"初始化文件已存在: {init_file}")
    
    print("初始化文件创建完成！")

if __name__ == '__main__':
    print("开始初始化ECG实时监控系统项目结构...")
    init_project_structure()
    create_init_files()
    print("项目结构初始化完成！")
