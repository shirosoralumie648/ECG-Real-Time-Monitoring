// ecg.js

// 全局变量
// 存储监测开始时的初始时间
var initialTime = null;
// 当前数据来源类型
var currentDataSource = 'serial';
// 是否正在监测
var isMonitoring = false;

// 连接WebSocket
var socket = io('http://localhost:5001', {
    transports: ['websocket']
});

socket.on('connect', function() {
    console.log('WebSocket connected');
});

// 接收连接状态更新
socket.on('connection_status', function(data) {
    console.log('Connection status update:', data);
    
    if (data.status === 'connected') {
        // 更新UI状态
        document.getElementById('connectBtn').disabled = true;
        document.getElementById('connectBtn').innerHTML = '<i class="fas fa-check me-1"></i> 已连接';
        document.getElementById('disconnectBtn').disabled = false;
        document.getElementById('startBtn').disabled = false;
        
        // 显示连接信息
        let connectionInfo = '';
        
        switch (data.type) {
            case 'serial':
                connectionInfo = `串口: ${data.port}, 波特率: ${data.baudrate}`;
                break;
                
            case 'udp':
                connectionInfo = `本地: ${data.local_ip}:${data.local_port}`;
                if (data.remote_ip && data.remote_port) {
                    connectionInfo += `, 远程: ${data.remote_ip}:${data.remote_port}`;
                }
                break;
                
            case 'bluetooth':
                connectionInfo = `设备: ${data.port}, 波特率: ${data.baudrate}`;
                break;
                
            case 'file':
                connectionInfo = `文件: ${data.fileName}`;
                break;
        }
        
        if (connectionInfo) {
            document.getElementById('connectionInfo').innerHTML = connectionInfo;
            document.getElementById('connectionInfoContainer').style.display = 'block';
        }
        
    } else if (data.status === 'disconnected') {
        // 重置按钮状态
        resetConnectButton();
        document.getElementById('startBtn').disabled = true;
        document.getElementById('stopBtn').disabled = true;
        
        // 隐藏连接信息
        document.getElementById('connectionInfoContainer').style.display = 'none';
        document.getElementById('connectionInfo').innerHTML = '';
        
        // 如果正在监测，停止监测
        if (isMonitoring) {
            isMonitoring = false;
            updateUIForMonitoring(false);
        }
    }
});

// 显示通知函数
function showNotification(message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.role = 'alert';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="关闭"></button>
    `;
    
    // 添加到通知容器
    const container = document.getElementById('notificationContainer');
    if (container) {
        container.appendChild(notification);
        
        // 5秒后自动关闭
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 150);
        }, 5000);
    } else {
        console.error('通知容器不存在');
        alert(message);
    }
}

// 接收通知事件
socket.on('notification', function(data) {
    showNotification(data.message, data.type || 'info');
});

// 数据来源设置相关函数
function updateDataSourceFields() {
    // 获取选择的数据来源类型
    const sourceType = document.getElementById('dataSourceType').value;
    currentDataSource = sourceType;
    
    // 隐藏所有设置区域
    const settingsDivs = document.querySelectorAll('.data-source-settings');
    settingsDivs.forEach(div => div.style.display = 'none');
    
    // 显示对应的设置区域
    const activeDiv = document.getElementById(sourceType + 'Settings');
    if (activeDiv) {
        activeDiv.style.display = 'block';
    }
    
    // 根据选择的数据来源类型加载相应设置
    if (sourceType === 'file') {
        loadReplayFiles();
    } else if (sourceType === 'serial') {
        // 自动扫描串口
        scanSerialPorts();
    }
}

// 扫描可用串口
function scanSerialPorts() {
    // 显示加载状态
    const serialPortSelect = document.getElementById('serialPort');
    serialPortSelect.innerHTML = '<option value="" selected>正在扫描串口...</option>';
    
    // 调用后端 API 获取可用串口列表
    fetch('/api/devices/serial-ports')
        .then(response => response.json())
        .then(ports => {
            // 清空现有选项
            serialPortSelect.innerHTML = '';
            
            if (ports.length === 0) {
                // 如果没有可用串口，显示提示
                serialPortSelect.innerHTML = '<option value="" selected>未发现串口</option>';
            } else {
                // 添加所有可用串口
                ports.forEach((port, index) => {
                    const option = document.createElement('option');
                    option.value = port;
                    option.text = port;
                    // 选中第一个串口
                    if (index === 0) {
                        option.selected = true;
                    }
                    serialPortSelect.appendChild(option);
                });
            }
        })
        .catch(error => {
            console.error('扫描串口错误:', error);
            serialPortSelect.innerHTML = '<option value="" selected>扫描失败</option>';
        });
}

// 加载回放文件列表
function loadReplayFiles() {
    fetch('/api/files')
        .then(response => response.json())
        .then(files => {
            const select = document.getElementById('replayFile');
            // 清空现有选项
            select.innerHTML = '<option value="" selected>选择文件...</option>';
            
            // 添加文件选项
            files.forEach(file => {
                let option = document.createElement('option');
                option.value = file;
                option.text = file;
                select.appendChild(option);
            });
        })
        .catch(error => console.error('加载文件列表错误:', error));
}

// 扫描蓝牙设备
function scanBluetoothDevices() {
    // 更新UI状态
    const scanBtn = document.getElementById('scanBluetoothBtn');
    const statusText = document.getElementById('bluetoothStatus');
    const deviceSelect = document.getElementById('bluetoothDevice');
    
    // 禁用扫描按钮
    scanBtn.disabled = true;
    scanBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 扫描中...';
    statusText.textContent = '正在初始化蓝牙模块...';
    
    // 清空设备列表
    deviceSelect.innerHTML = '<option value="" selected>选择设备...</option>';
    
    // 初始化蓝牙模块
    fetch('/api/devices/init-bluetooth')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                statusText.textContent = '正在扫描蓝牙设备...';
                
                // 开始扫描
                return fetch('/api/devices/scan-bluetooth', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
            } else {
                throw new Error('蓝牙模块初始化失败');
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 等待5秒后获取扫描结果
                setTimeout(() => {
                    fetch('/api/devices/bluetooth-devices')
                        .then(response => response.json())
                        .then(devices => {
                            // 停止扫描
                            fetch('/api/devices/stop-bluetooth-scan', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                }
                            });
                            
                            // 更新设备列表
                            if (devices && devices.length > 0) {
                                devices.forEach(device => {
                                    const option = document.createElement('option');
                                    option.value = device.address;
                                    option.textContent = `${device.name} (${device.address})`;
                                    deviceSelect.appendChild(option);
                                });
                                statusText.textContent = `找到 ${devices.length} 个蓝牙设备`;
                            } else {
                                statusText.textContent = '未找到蓝牙设备';
                            }
                            
                            // 恢复扫描按钮
                            scanBtn.disabled = false;
                            scanBtn.innerHTML = '<i class="fas fa-sync-alt"></i> 扫描';
                        })
                        .catch(error => {
                            console.error('获取蓝牙设备列表失败:', error);
                            statusText.textContent = '获取设备列表失败: ' + error.message;
                            scanBtn.disabled = false;
                            scanBtn.innerHTML = '<i class="fas fa-sync-alt"></i> 扫描';
                        });
                }, 5000);
            } else {
                throw new Error('开始扫描失败');
            }
        })
        .catch(error => {
            console.error('蓝牙扫描错误:', error);
            statusText.textContent = '扫描失败: ' + error.message;
            scanBtn.disabled = false;
            scanBtn.innerHTML = '<i class="fas fa-sync-alt"></i> 扫描';
        });
}

// 连接蓝牙设备
function connectBluetoothDevice(address) {
    const statusText = document.getElementById('bluetoothStatus');
    const portSection = document.getElementById('bluetoothPortSection');
    const portInput = document.getElementById('bluetoothPort');
    
    statusText.textContent = '正在连接蓝牙设备...';
    
    fetch('/api/devices/connect-bluetooth', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ address: address })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            statusText.textContent = '蓝牙设备连接成功';
            portSection.style.display = 'block';
            portInput.value = data.port;
        } else {
            statusText.textContent = '连接失败: ' + data.message;
        }
    })
    .catch(error => {
        console.error('蓝牙连接错误:', error);
        statusText.textContent = '连接错误: ' + error.message;
    });
}

// 监听蓝牙设备选择变化
document.getElementById('bluetoothDevice').addEventListener('change', function() {
    const selectedDevice = this.value;
    if (selectedDevice) {
        connectBluetoothDevice(selectedDevice);
    }
});

// 回放速度滑块事件
document.addEventListener('DOMContentLoaded', function() {
    const replaySpeed = document.getElementById('replaySpeed');
    const replaySpeedValue = document.getElementById('replaySpeedValue');
    
    if (replaySpeed && replaySpeedValue) {
        replaySpeed.addEventListener('input', function() {
            replaySpeedValue.textContent = replaySpeed.value + 'x';
        });
    }
});

socket.on('ecg_data', function(data) {
    // 改进的数据接收和处理逻辑
    console.log('Received ecg_data:', data);
    var leads = data.leads;  // leads是一个二维数组，形状为 [12][N]
    var timeStamps = data.time_stamps;  // 时间戳数组，长度为 N
    
    // 如果没有数据或数据为空，直接返回
    if (!timeStamps || timeStamps.length === 0 || !leads || leads.length === 0) {
        console.log('接收到空数据，忽略');
        return;
    }
    
    var numPoints = timeStamps.length;  // 数据点数量

    // 在第一次接收到数据时，设置 initialTime
    if (initialTime === null) {
        initialTime = timeStamps[0];  // 记录初始时间戳
        console.log('设置初始时间戳: ' + initialTime);
    }

    // 将时间戳转换为相对于 initialTime 的相对时间（秒）
    var relativeTimeStamps = timeStamps.map(function(ts) {
        return ts - initialTime;
    });
    
    // 如果启用了数据缓冲，将数据添加到缓冲区
    if (dataBuffer.enabled) {
        // 将新数据添加到缓冲区
        for (var j = 0; j < numPoints; j++) {
            var bufferItem = {
                time: relativeTimeStamps[j],
                values: []
            };
            
            // 收集所有导联的数据
            for (var i = 0; i < 12; i++) {
                if (leads[i] && j < leads[i].length) {
                    bufferItem.values.push(leads[i][j]);
                } else {
                    bufferItem.values.push(0); // 如果数据缺失，使用零填充
                }
            }
            
            dataBuffer.data.push(bufferItem);
        }
        
        // 如果缓冲区数据足够多，或者检测到数据不连续，则更新图表
        var shouldUpdate = dataBuffer.data.length >= dataBuffer.size;
        
        // 检查数据连续性
        if (traces[0].x.length > 0 && dataBuffer.data.length > 0) {
            var lastTime = traces[0].x[traces[0].x.length - 1];
            var firstNewTime = dataBuffer.data[0].time;
            
            // 如果时间间隔超过阈值，说明数据不连续
            if (firstNewTime - lastTime > dataBuffer.timeThreshold) {
                console.log('检测到数据间隔: ' + (firstNewTime - lastTime).toFixed(4) + ' 秒，重置图表');
                // 清除所有导联的数据
                for (var i = 0; i < 12; i++) {
                    traces[i].x = [];
                    traces[i].y = [];
                }
                shouldUpdate = true;
            }
        }
        
        // 如果应该更新图表，将缓冲区数据添加到图表中
        if (shouldUpdate) {
            // 将缓冲区数据添加到图表中
            for (var i = 0; i < 12; i++) {
                for (var j = 0; j < dataBuffer.data.length; j++) {
                    traces[i].x.push(dataBuffer.data[j].time);
                    traces[i].y.push(dataBuffer.data[j].values[i]);
                }
            }
            
            // 清空缓冲区
            dataBuffer.data = [];
            
            // 只保留最近5秒的数据
            updatePlotWithLatestData();
        }
    } else {
        // 如果没有启用缓冲，直接更新图表
        
        // 检查是否需要清除当前数据并重新开始
        var shouldReset = false;
        
        // 如果已经有数据，检查时间间隔
        if (traces[0].x.length > 0) {
            var lastTime = traces[0].x[traces[0].x.length - 1];
            var firstNewTime = relativeTimeStamps[0];
            
            // 如果时间间隔超过阈值，说明数据不连续
            if (firstNewTime - lastTime > dataBuffer.timeThreshold) {
                console.log('检测到数据间隔: ' + (firstNewTime - lastTime).toFixed(4) + ' 秒，重置图表');
                shouldReset = true;
            }
        }
        
        // 如果需要重置，清除所有导联的数据
        if (shouldReset) {
            for (var i = 0; i < 12; i++) {
                traces[i].x = [];
                traces[i].y = [];
            }
        }
        
        // 更新每个导联的波形数据
        for (var i = 0; i < 12; i++) {
            var leadData = leads[i];  // 当前导联的数据数组
            if (leadData) {
                for (var j = 0; j < numPoints; j++) {
                    if (j < leadData.length) {
                        traces[i].x.push(relativeTimeStamps[j]);
                        traces[i].y.push(leadData[j]);
                    }
                }
            }
        }
        
        // 更新图表，只保留最近5秒的数据
        updatePlotWithLatestData();
    }
});

// 更新图表，只保留最近5秒的数据
function updatePlotWithLatestData() {
    // 确保有数据
    if (traces[0].x.length === 0) return;
    
    // 获取最新时间
    var latestTime = traces[0].x[traces[0].x.length - 1];
    var maxTime = latestTime - 5;  // 显示最近5秒的数据
    
    // 为每个导联删除过时的数据
    for (var i = 0; i < 12; i++) {
        while (traces[i].x.length > 0 && traces[i].x[0] < maxTime) {
            traces[i].x.shift();
            traces[i].y.shift();
        }
    }

    // 更新图表范围，动态滚动
    var updatedLayout = {
        xaxis: { 
            range: [maxTime, latestTime],
            // 添加平滑过渡效果
            transition: {
                duration: 50,  // 增加过渡时间以使滑动更平滑
                easing: 'cubic-in-out'
            }
        }
    };
    
    // 平滑连接数据点
    var plotOptions = {
        transition: {
            duration: 50,  // 增加过渡时间以使数据更新更平滑
            easing: 'cubic-in-out'
        }
    };

    // 更新图表
    Plotly.update('ecg_plots', traces, updatedLayout, plotOptions);
}

// 初始化绘图 - 改进版
var leadNames = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6'];
var traces = [];

// 数据缓冲参数
var dataBuffer = {
    enabled: true,     // 是否启用数据缓冲
    size: 50,         // 缓冲区大小
    data: [],         // 缓冲区数据
    timeThreshold: 0.02 // 数据间隔检测阈值，降低到20毫秒
};

// 为每个导联创建跟踪对象，使用改进的绘图模式
for (var i = 0; i < 12; i++) {
    traces.push({
        x: [],
        y: [],
        mode: 'lines+markers',  // 添加标记点以增强可视性
        line: {
            shape: 'spline',     // 使用样条曲线而非直线连接
            smoothing: 1.3,      // 增加平滑度
            width: 1.5           // 线条宽度
        },
        marker: {
            size: 2,             // 小标记点
            opacity: 0.6         // 半透明以减少视觉干扰
        },
        name: leadNames[i]
    });
}

// 改进的图表布局
var layout = {
    title: '实时ECG波形',
    xaxis: { 
        title: '时间 (s)',
        showgrid: true,
        gridcolor: '#e6e6e6',
        zeroline: false
    },
    yaxis: { 
        title: '电压 (mV)',
        showgrid: true,
        gridcolor: '#e6e6e6',
        zeroline: true,
        zerolinecolor: '#969696',
        zerolinewidth: 1
    },
    autosize: true,
    margin: {l: 50, r: 20, t: 40, b: 40},
    paper_bgcolor: 'rgba(255,255,255,0.9)',
    plot_bgcolor: 'rgba(255,255,255,0.9)',
    hovermode: false,  // 禁用悬停效果以提高性能
    showlegend: true,
    legend: {
        x: 1,
        y: 1,
        xanchor: 'right',
        yanchor: 'top',
        bgcolor: 'rgba(255,255,255,0.7)',
        bordercolor: '#e6e6e6',
        borderwidth: 1
    },
    // 添加全局过渡效果
    transition: {
        duration: 0,
        easing: 'cubic-in-out'
    }
};

// 初始化图表
var config = {
    responsive: true,
    displayModeBar: false,  // 隐藏模式栏以提高性能
    staticPlot: false      // 非静态图表，允许交互
};

Plotly.newPlot('ecg_plots', traces, layout, config);

// 连接数据源
function connectDataSource() {
    console.log('connectDataSource() called with data source:', currentDataSource);
    
    // 禁用连接按钮，显示加载状态
    document.getElementById('connectBtn').disabled = true;
    document.getElementById('connectBtn').innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> 连接中...';
    
    // 收集当前数据来源的配置
    let sourceConfig = {};
    
    switch (currentDataSource) {
        case 'serial':
            sourceConfig = {
                type: 'serial',
                port: document.getElementById('serialPort').value,
                baudrate: parseInt(document.getElementById('serialBaudrate').value)
            };
            break;
            
        case 'udp':
            sourceConfig = {
                type: 'udp',
                local_ip: document.getElementById('udpLocalIp').value,
                local_port: parseInt(document.getElementById('udpLocalPort').value)
            };
            
            // 添加远程IP和端口（如果提供）
            const remoteIp = document.getElementById('udpRemoteIp').value;
            const remotePort = document.getElementById('udpRemotePort').value;
            
            if (remoteIp && remoteIp.trim() !== '') {
                sourceConfig.remote_ip = remoteIp;
            }
            
            if (remotePort && !isNaN(parseInt(remotePort))) {
                sourceConfig.remote_port = parseInt(remotePort);
            }
            break;
            
        case 'bluetooth':
            // 蓝牙模式使用连接后的串口
            const bluetoothPort = document.getElementById('bluetoothPort').value;
            if (!bluetoothPort) {
                alert('请先扫描并选择蓝牙设备');
                resetConnectButton();
                return;
            }
            sourceConfig = {
                type: 'bluetooth',
                port: bluetoothPort,
                baudrate: parseInt(document.getElementById('bluetoothBaudrate').value)
            };
            break;
            
        case 'file':
            const selectedFile = document.getElementById('replayFile').value;
            if (!selectedFile) {
                alert('请选择回放文件');
                resetConnectButton();
                return;
            }
            sourceConfig = {
                type: 'file',
                fileName: selectedFile
            };
            break;
            
        default:
            alert('请选择数据来源');
            resetConnectButton();
            return;
    }
    
    // 发送连接请求
    fetch('/api/monitor/connect', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(sourceConfig)
    })
    .then(response => response.json())
    .then(data => {
        console.log('Connect response:', data);
        if (data.status === 'connected') {
            // 更新UI状态
            document.getElementById('connectBtn').innerHTML = '<i class="fas fa-check me-1"></i> 已连接';
            document.getElementById('disconnectBtn').disabled = false;
            document.getElementById('startBtn').disabled = false;
        } else if (data.status === 'error') {
            // 显示错误信息
            showNotification(data.message || '连接失败', 'error');
            resetConnectButton();
        }
    })
    .catch(error => {
        console.error('Error connecting to data source:', error);
        showNotification('连接请求失败: ' + error.message, 'error');
        resetConnectButton();
    });
}

// 断开数据源连接
function disconnectDataSource() {
    console.log('disconnectDataSource() called');
    
    // 禁用断开按钮，显示加载状态
    document.getElementById('disconnectBtn').disabled = true;
    document.getElementById('disconnectBtn').innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> 断开中...';
    
    // 发送断开连接请求
    fetch('/api/monitor/disconnect', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log('Disconnect response:', data);
        if (data.status === 'disconnected') {
            // 重置按钮状态
            resetConnectButton();
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = true;
            
            // 如果正在监测，停止监测
            if (isMonitoring) {
                isMonitoring = false;
            }
        } else if (data.status === 'error') {
            // 显示错误信息
            showNotification(data.message || '断开连接失败', 'error');
            document.getElementById('disconnectBtn').disabled = false;
            document.getElementById('disconnectBtn').innerHTML = '<i class="fas fa-unlink me-1"></i> 断开连接';
        }
    })
    .catch(error => {
        console.error('Error disconnecting from data source:', error);
        showNotification('断开连接请求失败: ' + error.message, 'error');
        document.getElementById('disconnectBtn').disabled = false;
        document.getElementById('disconnectBtn').innerHTML = '<i class="fas fa-unlink me-1"></i> 断开连接';
    });
}

// 重置连接按钮状态
function resetConnectButton() {
    document.getElementById('connectBtn').disabled = false;
    document.getElementById('connectBtn').innerHTML = '<i class="fas fa-plug me-1"></i> 连接数据源';
    document.getElementById('disconnectBtn').disabled = true;
    document.getElementById('disconnectBtn').innerHTML = '<i class="fas fa-unlink me-1"></i> 断开连接';
}

// 控制函数
function startECG() {
    if (isMonitoring) {
        alert('监测已在进行中');
        return;
    }
    
    console.log('startECG() called');
    initialTime = null;  // 重置 initialTime
    
    // 禁用开始按钮，显示加载状态
    document.getElementById('startBtn').disabled = true;
    document.getElementById('startBtn').innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> 启动中...';
    
    // 获取回放速度（如果是文件模式）
    let sourceConfig = {};
    if (currentDataSource === 'file') {
        sourceConfig.speed = parseFloat(document.getElementById('replaySpeed').value);
    }
    
    // 发送请求到后端
    fetch('/api/monitor/start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(sourceConfig)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        console.log('Start response:', data);
        if (data.status === 'started') {
            isMonitoring = true;
            
            // 更新按钮状态
            document.getElementById('startBtn').disabled = true;
            document.getElementById('startBtn').innerHTML = '<i class="fas fa-play me-1"></i> 开始实时监测';
            document.getElementById('stopBtn').disabled = false;
            document.getElementById('connectBtn').disabled = true;
            document.getElementById('disconnectBtn').disabled = true;
            
            // 清空现有数据
            for (var i = 0; i < 12; i++) {
                traces[i].x = [];
                traces[i].y = [];
            }
            Plotly.update('ecg_plots', traces);
            
            // 更新UI状态
            updateUIForMonitoring(true);
        } else {
            alert('启动失败: ' + (data.message || '未知错误'));
        }
    })
    .catch(error => {
        console.error('Error in startECG:', error);
        alert('启动失败: ' + error.message);
    });
}

function stopECG() {
    if (!isMonitoring) {
        alert('监测尚未开始');
        return;
    }
    
    console.log('stopECG() called');
    
    // 禁用停止按钮，显示加载状态
    document.getElementById('stopBtn').disabled = true;
    document.getElementById('stopBtn').innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> 停止中...';
    
    fetch('/api/monitor/stop', { method: 'POST' })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Stop response:', data);
            isMonitoring = false;
            
            // 恢复按钮状态
            document.getElementById('stopBtn').disabled = true;
            document.getElementById('stopBtn').innerHTML = '<i class="fas fa-stop me-1"></i> 停止实时监测';
            document.getElementById('startBtn').disabled = false;
            document.getElementById('disconnectBtn').disabled = false;
            
            // 更新UI状态
            updateUIForMonitoring(false);
            
            // 如果是文件回放模式，重新加载文件列表
            if (currentDataSource === 'file') {
                loadReplayFiles();
            }
            
            // 如果是文件模式，也重新加载分析文件列表
            fetch('/api/files')
                .then(response => response.json())
                .then(files => {
                    const select = document.getElementById("ecgFiles");
                    select.innerHTML = '<option selected>选择一个历史文件...</option>';
                    files.forEach(file => {
                        let option = document.createElement("option");
                        option.value = file;
                        option.text = file;
                        select.appendChild(option);
                    });
                })
                .catch(error => console.error('Error:', error));
        })
        .catch(error => {
            console.error('Error in stopECG:', error);
            alert('停止失败: ' + error.message);
        });
}

// 更新UI状态
function updateUIForMonitoring(isActive) {
    // 禁用/启用数据来源选择
    document.getElementById('dataSourceType').disabled = isActive;
    
    // 禁用/启用所有设置输入字段
    const inputs = document.querySelectorAll('.data-source-settings input, .data-source-settings select');
    inputs.forEach(input => input.disabled = isActive);
    
    // 禁用/启用扫描按钮
    const scanButton = document.querySelector('button[onclick="scanBluetoothDevices()"]');
    if (scanButton) scanButton.disabled = isActive;
}

function analyzeECG(action) {
    console.log('analyzeECG() called with action:', action);
    fetch('/api/analysis/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: action })
    })
        .then(response => response.json())
        .then(data => {
            // 显示分析结果
            document.getElementById('analysis_results').innerHTML = data.result;
        });
}

// 获取文件列表
document.addEventListener("DOMContentLoaded", function() {
    fetch('/api/files')
        .then(response => response.json())
        .then(files => {
            const select = document.getElementById("ecgFiles");
            files.forEach(file => {
                let option = document.createElement("option");
                option.value = file;
                option.text = file;
                select.appendChild(option);
            });
        })
        .catch(error => console.error('Error:', error));

    document.getElementById("analyzeButton").addEventListener("click", triggerAnalysis);

});

function triggerAnalysis() {
    const select = document.getElementById("ecgFiles");
    const fileName = select.value;

    if (!select) {
        console.error('Element with id \'ecgFiles\' not found');
        return;
    }

    if (!fileName) {
        console.error('No file selected');
        return;
    }



    fetch('/api/analysis/process-ecg', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ file_name: fileName }),
    })
        .then(response => response.blob())
        .then(blob => {
            const url = URL.createObjectURL(blob);
            const imgElement = document.getElementById("ecgImage");
            imgElement.src = url;
            imgElement.style.display = 'block';
        })
        .catch(error => console.error('Error:', error));
}

function HRVAnalysis() {
    const select = document.getElementById("ecgFiles");
    const fileName = select.value;

    if (!select) {
        console.error('Element with id \'ecgFiles\' not found');
        return;
    }

    if (!fileName) {
        console.error('No file selected');
        return;
    }



    fetch('/api/analysis/process-hrv', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ file_name: fileName }),
    })
        .then(response => response.blob())
        .then(blob => {
            const url = URL.createObjectURL(blob);
            const imgElement = document.getElementById("ecgImage");
            imgElement.src = url;
            imgElement.style.display = 'block';
        })
        .catch(error => console.error('Error:', error));
}

function EDRAnalysis() {
    const select = document.getElementById("ecgFiles");
    const fileName = select.value;

    if (!select) {
        console.error('Element with id \'ecgFiles\' not found');
        return;
    }

    if (!fileName) {
        console.error('No file selected');
        return;
    }



    fetch('/api/analysis/process-edr', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ file_name: fileName }),
    })
        .then(response => response.blob())
        .then(blob => {
            const url = URL.createObjectURL(blob);
            const imgElement = document.getElementById("ecgImage");
            imgElement.src = url;
            imgElement.style.display = 'block';
        })
        .catch(error => console.error('Error:', error));
}