# 生理信号实时监测与分析系统

## 项目概述
一个现代化的生理信号实时监测与分析平台，支持多参数生理信号采集、实时显示、数据分析和报告生成。系统采用模块化设计，支持多种数据源接入，提供完善的用户管理和数据分析功能。

## 功能特性

### 1. 实时监测
- 12导联ECG波形实时显示
- 呼吸波形实时显示
- 多设备同时连接与监控
- 实时参数显示（心率、呼吸频率等）

### 2. 信号分析
- **ECG分析**:
  - 心率变异性(HRV)分析
  - ST段分析
  - 心律失常检测
  - 12导联同步分析

- **呼吸分析**:
  - 呼吸频率计算
  - 呼吸变异性分析
  - 呼吸模式识别

### 3. 数据源支持
- 串口设备接入
- 蓝牙设备连接
- UDP数据流接收
- 文件回放（支持历史数据回放）
- 支持的数据格式：rawdata, firewater, justfloat

### 4. 用户管理
- 多角色系统（医生、患者、管理员）
- 患者信息管理
- 权限控制

### 5. 数据管理
- 历史数据存储
- 数据导出（支持多种格式）
- 自动/手动数据清理

### 6. 报告功能
- PDF报告生成
- 打印功能
- 原始数据导出

## 技术栈

### 前端
- **框架**: React.js 18+
- **UI组件库**: Material-UI (MUI) + 自定义主题
- **图表库**: Chart.js / ECharts
- **状态管理**: Redux Toolkit
- **样式**: CSS-in-JS (styled-components)
- **构建工具**: Vite

### 后端
- **框架**: FastAPI
- **数据库**: 
  - 主数据库: PostgreSQL (用户数据、元数据)
  - 时序数据库: InfluxDB (生理信号数据)
- **认证**: JWT
- **WebSocket**: 实时数据传输
- **任务队列**: Celery (用于后台处理任务)

## 项目结构

```
physio-monitoring-system/
├── backend/                    # 后端代码
│   ├── app/                    # 应用主目录
│   │   ├── api/                # API路由
│   │   ├── core/               # 核心功能
│   │   │   ├── config.py       # 配置文件
│   │   │   ├── security.py     # 认证相关
│   │   │   └── database.py     # 数据库连接
│   │   ├── db/                 # 数据库模型和迁移
│   │   ├── models/             # Pydantic模型
│   │   ├── schemas/            # 数据库模型
│   │   ├── services/           # 业务逻辑
│   │   │   ├── auth.py         # 认证服务
│   │   │   ├── ecg.py          # ECG处理服务
│   │   │   ├── respiration.py  # 呼吸处理服务
│   │   │   └── users.py        # 用户管理服务
│   │   └── utils/              # 工具函数
│   ├── tests/                  # 测试
│   ├── requirements.txt         # Python依赖
│   └── main.py                 # 应用入口
│
└── frontend/                   # 前端代码
    ├── public/                 # 静态资源
    └── src/                    # 源代码
        ├── assets/             # 图片等资源
        ├── components/         # 公共组件
        ├── features/           # 功能模块
        │   ├── auth/           # 认证相关
        │   ├── dashboard/      # 仪表盘
        │   ├── ecg/            # ECG监测
        │   ├── respiration/    # 呼吸监测
        │   └── settings/       # 设置
        ├── store/              # 状态管理
        ├── styles/             # 全局样式
        └── App.jsx             # 主组件
```

## 安装指南（本地开发环境）

### 后端设置

1. **克隆仓库**
   ```bash
   git clone https://github.com/yourusername/physio-monitoring-system.git
   cd physio-monitoring-system/backend
   ```

2. **创建并激活虚拟环境**
   ```bash
   # Linux/Mac
   python -m venv venv
   source venv/bin/activate
   
   # Windows
   python -m venv venv
   venv\Scripts\activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **配置环境变量**
   创建 `.env` 文件：
   ```env
   # 应用配置
   APP_ENV=development
   SECRET_KEY=your-secret-key
   
   # 数据库配置
   DATABASE_URL=postgresql://user:password@localhost/physio_monitoring
   
   # JWT配置
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   JWT_ALGORITHM=HS256
   ```

5. **初始化数据库**
   ```bash
   # 创建数据库
   createdb physio_monitoring
   
   # 运行迁移
   alembic upgrade head
   
   # 创建初始管理员账户
   python -m app.commands.create_admin
   ```

6. **启动开发服务器**
   ```bash
   uvicorn app.main:app --reload
   ```

### 前端设置

1. **安装Node.js**
   确保已安装Node.js (v16+)


2. **安装依赖**
   ```bash
   cd ../frontend
   npm install
   ```

3. **启动开发服务器**
   ```bash
   npm run dev
   ```

4. **访问应用**
   打开浏览器访问 `http://localhost:3000`

## 开发流程

### 阶段一：基础架构搭建 (1-2周)
1. 项目初始化
   - 设置Git仓库
   - 配置开发环境
   - 搭建基础项目结构

2. 后端基础架构
   - 设置FastAPI应用
   - 配置数据库连接
   - 实现基本API结构

3. 前端基础架构
   - 初始化React项目
   - 配置路由
   - 设置状态管理

### 阶段二：核心功能开发 (3-6周)
1. 用户认证系统
   - 用户注册/登录
   - 角色管理
   - 权限控制

2. 数据采集模块
   - 串口数据采集
   - 蓝牙设备连接
   - UDP数据接收
   - 文件回放功能

3. 数据处理与存储
   - 数据解析
   - 实时数据处理
   - 数据存储设计

### 阶段三：分析与显示 (4-8周)
1. 实时监测界面
   - ECG波形显示
   - 呼吸波形显示
   - 实时参数展示

2. 分析功能
   - HRV分析
   - ST段分析
   - 心律失常检测
   - 呼吸分析

3. 报告生成
   - PDF报告
   - 数据导出

### 阶段四：测试与优化 (2-4周)
1. 单元测试
2. 集成测试
3. 性能优化
4. 用户体验优化

### 阶段五：部署与维护 (持续进行)
1. 生产环境部署
2. 监控与日志
3. 定期维护

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

MIT License

## 联系方式

- 项目维护者: [Your Name]
- 邮箱: your.email@example.com
