#!/bin/bash

# 启动ECG实时监控系统

# 显示彩色输出
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
NC="\033[0m" # No Color

echo -e "${GREEN}ECG实时监控系统启动脚本${NC}"
echo -e "${YELLOW}正在检查环境...${NC}"

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到Python3，请安装Python 3.8或更高版本${NC}"
    exit 1
fi

# 检查Python版本
PYTHON_VERSION=$(python3 -c 'import sys; print("{}.{}".format(sys.version_info.major, sys.version_info.minor))')
echo -e "${GREEN}检测到Python版本: ${PYTHON_VERSION}${NC}"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}未找到虚拟环境，正在创建...${NC}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}创建虚拟环境失败，请检查Python venv模块是否安装${NC}"
        exit 1
    fi
    echo -e "${GREEN}虚拟环境创建成功${NC}"
fi

# 激活虚拟环境
echo -e "${YELLOW}激活虚拟环境...${NC}"
source venv/bin/activate

# 安装依赖
echo -e "${YELLOW}检查并安装依赖...${NC}"
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}安装依赖失败，请检查网络连接和requirements.txt文件${NC}"
    exit 1
fi

# 初始化项目结构
echo -e "${YELLOW}初始化项目结构...${NC}"
python -m backend.init_project

# 创建必要的目录
echo -e "${YELLOW}创建必要的目录...${NC}"
mkdir -p backend/data/reports
mkdir -p backend/data/fonts

# 检查字体文件
if [ ! -f "backend/data/fonts/simhei.ttf" ]; then
    echo -e "${YELLOW}下载中文字体文件...${NC}"
    wget -O backend/data/fonts/simhei.ttf https://github.com/adobe-fonts/source-han-sans/raw/release/OTF/SimplifiedChinese/SourceHanSansSC-Normal.otf
    if [ $? -ne 0 ]; then
        echo -e "${RED}下载字体文件失败，报告生成功能可能受影响${NC}"
    else
        echo -e "${GREEN}字体文件下载成功${NC}"
    fi
fi

# 设置环境变量
export FLASK_APP=backend.app
export FLASK_ENV=development

# 检查数据库服务
echo -e "${YELLOW}检查数据库服务...${NC}"
# 如果数据库服务不可用，请打印警告信息
echo -e "${YELLOW}提示: 如果需要完整功能，请确保MongoDB、InfluxDB和Redis服务已启动${NC}"

# 启动应用
echo -e "${GREEN}启动ECG实时监控系统...${NC}"
echo -e "${YELLOW}服务器将在 http://localhost:5000 上运行${NC}"
python -m backend.main
