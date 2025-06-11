// monitor.js - ECG监控系统前端控制脚本

// 初始化Socket.IO连接
const socket = io('http://localhost:5001');

// 连接状态
let connectionStatus = {
    connected: false,
    type: null,
    details: {}
};

// 监测状态
let monitoringStatus = {
    active: false,
    speed: 1.0,
    patientId: null
};

// DOM元素缓存
const elements = {
    // 连接控制
    connectBtn: document.getElementById('connect-btn'),
    disconnectBtn: document.getElementById('disconnect-btn'),
    connectionStatus: document.getElementById('connection-status'),
    
    // 监测控制
    startBtn: document.getElementById('start-btn'),
    stopBtn: document.getElementById('stop-btn'),
    monitoringStatus: document.getElementById('monitoring-status'),
    
    // 数据源选择
    sourceTypeSelect: document.getElementById('source-type'),
    sourceSettings: document.getElementById('source-settings'),
    serialSettings: document.getElementById('serial-settings'),
    udpSettings: document.getElementById('udp-settings'),
    bluetoothSettings: document.getElementById('bluetooth-settings'),
    fileSettings: document.getElementById('file-settings'),
    
    // 串口设置
    serialPortSelect: document.getElementById('serial-port'),
    serialBaudrateSelect: document.getElementById('serial-baudrate'),
    scanPortsBtn: document.getElementById('scan-ports-btn'),
    
    // UDP设置
    localIpInput: document.getElementById('local-ip'),
    localPortInput: document.getElementById('local-port'),
    remoteIpInput: document.getElementById('remote-ip'),
    remotePortInput: document.getElementById('remote-port'),
    
    // 蓝牙设置
    bluetoothDeviceSelect: document.getElementById('bluetooth-device'),
    bluetoothBaudrateSelect: document.getElementById('bluetooth-baudrate'),
    scanBluetoothBtn: document.getElementById('scan-bluetooth-btn'),
    
    // 文件设置
    fileNameInput: document.getElementById('file-name'),
    browseFileBtn: document.getElementById('browse-file-btn'),
    
    // 速度控制
    speedInput: document.getElementById('playback-speed'),
    
    // 患者选择
    patientSelect: document.getElementById('patient-select'),
    
    // 通知区域
    notificationArea: document.getElementById('notification-area')
};

// 初始化页面
function initPage() {
    // 显示/隐藏相关设置
    updateSourceSettings();
    
    // 更新按钮状态
    updateButtonStates();
    
    // 加载患者列表
    loadPatientList();
    
    // 设置事件监听器
    setupEventListeners();
    
    // 监听Socket.IO事件
    setupSocketListeners();
}

// 根据数据源类型显示/隐藏相关设置
function updateSourceSettings() {
    const sourceType = elements.sourceTypeSelect.value;
    
    // 隐藏所有设置
    elements.serialSettings.style.display = 'none';
    elements.udpSettings.style.display = 'none';
    elements.bluetoothSettings.style.display = 'none';
    elements.fileSettings.style.display = 'none';
    
    // 显示选中的设置
    switch (sourceType) {
        case 'serial':
            elements.serialSettings.style.display = 'block';
            // 自动扫描串口
            scanSerialPorts();
            break;
        case 'udp':
            elements.udpSettings.style.display = 'block';
            break;
        case 'bluetooth':
            elements.bluetoothSettings.style.display = 'block';
            // 自动扫描蓝牙设备
            scanBluetoothDevices();
            break;
        case 'file':
            elements.fileSettings.style.display = 'block';
            break;
    }
}

// 更新按钮状态
function updateButtonStates() {
    // 连接/断开按钮
    elements.connectBtn.disabled = connectionStatus.connected;
    elements.disconnectBtn.disabled = !connectionStatus.connected;
    
    // 开始/停止按钮
    elements.startBtn.disabled = !connectionStatus.connected || monitoringStatus.active;
    elements.stopBtn.disabled = !monitoringStatus.active;
    
    // 数据源设置
    elements.sourceTypeSelect.disabled = connectionStatus.connected;
    
    // 更新连接状态显示
    updateConnectionStatusDisplay();
    
    // 更新监测状态显示
    updateMonitoringStatusDisplay();
}

// 更新连接状态显示
function updateConnectionStatusDisplay() {
    if (connectionStatus.connected) {
        let statusText = `已连接到: ${getSourceTypeText(connectionStatus.type)}`;
        
        // 添加详细信息
        switch (connectionStatus.type) {
            case 'serial':
                statusText += ` (端口: ${connectionStatus.details.port}, 波特率: ${connectionStatus.details.baudrate})`;
                break;
            case 'udp':
                statusText += ` (本地: ${connectionStatus.details.local_ip}:${connectionStatus.details.local_port})`;
                if (connectionStatus.details.remote_ip) {
                    statusText += `, 远程: ${connectionStatus.details.remote_ip}:${connectionStatus.details.remote_port}`;
                }
                break;
            case 'bluetooth':
                statusText += ` (设备: ${connectionStatus.details.port}, 波特率: ${connectionStatus.details.baudrate})`;
                break;
            case 'file':
                statusText += ` (文件: ${connectionStatus.details.file_name})`;
                break;
        }
        
        elements.connectionStatus.textContent = statusText;
        elements.connectionStatus.className = 'status-connected';
    } else {
        elements.connectionStatus.textContent = '未连接';
        elements.connectionStatus.className = 'status-disconnected';
    }
}

// 更新监测状态显示
function updateMonitoringStatusDisplay() {
    if (monitoringStatus.active) {
        let statusText = `正在监测`;
        
        if (monitoringStatus.speed !== 1.0) {
            statusText += ` (速度: ${monitoringStatus.speed}x)`;
        }
        
        if (monitoringStatus.patientId) {
            const patientName = getPatientNameById(monitoringStatus.patientId);
            statusText += ` - 患者: ${patientName || monitoringStatus.patientId}`;
        }
        
        elements.monitoringStatus.textContent = statusText;
        elements.monitoringStatus.className = 'status-active';
    } else {
        elements.monitoringStatus.textContent = '未监测';
        elements.monitoringStatus.className = 'status-inactive';
    }
}

// 获取数据源类型的中文名称
function getSourceTypeText(type) {
    const typeMap = {
        'serial': '串口',
        'udp': 'UDP',
        'bluetooth': '蓝牙',
        'file': '文件'
    };
    return typeMap[type] || type;
}

// 根据ID获取患者名称
function getPatientNameById(patientId) {
    const patientSelect = elements.patientSelect;
    for (let i = 0; i < patientSelect.options.length; i++) {
        if (patientSelect.options[i].value === patientId) {
            return patientSelect.options[i].text;
        }
    }
    return null;
}

// 加载患者列表
function loadPatientList() {
    fetch('/api/patients')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const patientSelect = elements.patientSelect;
                
                // 清空现有选项
                patientSelect.innerHTML = '<option value="">-- 选择患者 --</option>';
                
                // 添加患者选项
                data.patients.forEach(patient => {
                    const option = document.createElement('option');
                    option.value = patient._id;
                    option.textContent = `${patient.name} (${patient.gender}, ${getAge(patient.birth_date)}岁)`;
                    patientSelect.appendChild(option);
                });
            } else {
                showNotification('加载患者列表失败: ' + data.message, 'error');
            }
        })
        .catch(error => {
            showNotification('加载患者列表出错: ' + error, 'error');
        });
}

// 计算年龄
function getAge(birthDate) {
    if (!birthDate) return '?';
    
    const birth = new Date(birthDate);
    const now = new Date();
    let age = now.getFullYear() - birth.getFullYear();
    
    // 检查是否已过生日
    if (now.getMonth() < birth.getMonth() || 
        (now.getMonth() === birth.getMonth() && now.getDate() < birth.getDate())) {
        age--;
    }
    
    return age;
}

// 扫描串口
function scanSerialPorts() {
    showNotification('正在扫描串口...', 'info');
    
    fetch('/api/devices/serial-ports')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const portSelect = elements.serialPortSelect;
                
                // 保存当前选择的值
                const currentValue = portSelect.value;
                
                // 清空现有选项
                portSelect.innerHTML = '';
                
                // 添加端口选项
                data.ports.forEach(port => {
                    const option = document.createElement('option');
                    option.value = port.device;
                    option.textContent = `${port.device} - ${port.description || '未知设备'}`;
                    portSelect.appendChild(option);
                });
                
                // 如果之前有选择，尝试恢复
                if (currentValue && Array.from(portSelect.options).some(opt => opt.value === currentValue)) {
                    portSelect.value = currentValue;
                }
                
                // 如果没有端口，显示提示
                if (data.ports.length === 0) {
                    showNotification('未找到可用串口设备', 'warning');
                } else {
                    showNotification(`找到 ${data.ports.length} 个串口设备`, 'success');
                }
            } else {
                showNotification('扫描串口失败: ' + data.message, 'error');
            }
        })
        .catch(error => {
            showNotification('扫描串口出错: ' + error, 'error');
        });
}

// 扫描蓝牙设备
function scanBluetoothDevices() {
    showNotification('正在扫描蓝牙设备...', 'info');
    
    fetch('/api/devices/bluetooth-devices')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const deviceSelect = elements.bluetoothDeviceSelect;
                
                // 保存当前选择的值
                const currentValue = deviceSelect.value;
                
                // 清空现有选项
                deviceSelect.innerHTML = '';
                
                // 添加设备选项
                data.devices.forEach(device => {
                    const option = document.createElement('option');
                    option.value = device.address;
                    option.textContent = `${device.name || device.address} - ${device.type || '未知类型'}`;
                    deviceSelect.appendChild(option);
                });
                
                // 如果之前有选择，尝试恢复
                if (currentValue && Array.from(deviceSelect.options).some(opt => opt.value === currentValue)) {
                    deviceSelect.value = currentValue;
                }
                
                // 如果没有设备，显示提示
                if (data.devices.length === 0) {
                    showNotification('未找到可用蓝牙设备', 'warning');
                } else {
                    showNotification(`找到 ${data.devices.length} 个蓝牙设备`, 'success');
                }
            } else {
                showNotification('扫描蓝牙设备失败: ' + data.message, 'error');
            }
        })
        .catch(error => {
            showNotification('扫描蓝牙设备出错: ' + error, 'error');
        });
}

// 连接到数据源
function connectToSource() {
    const sourceType = elements.sourceTypeSelect.value;
    let data = { source_type: sourceType };
    
    // 根据数据源类型获取参数
    switch (sourceType) {
        case 'serial':
            data.port = elements.serialPortSelect.value;
            data.baudrate = elements.serialBaudrateSelect.value;
            break;
        case 'udp':
            data.local_ip = elements.localIpInput.value;
            data.local_port = elements.localPortInput.value;
            data.remote_ip = elements.remoteIpInput.value || null;
            data.remote_port = elements.remotePortInput.value || null;
            break;
        case 'bluetooth':
            data.port = elements.bluetoothDeviceSelect.value;
            data.baudrate = elements.bluetoothBaudrateSelect.value;
            break;
        case 'file':
            data.file_name = elements.fileNameInput.value;
            break;
    }
    
    // 发送连接请求
    fetch('/api/monitor/connect', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 更新连接状态
            connectionStatus.connected = true;
            connectionStatus.type = sourceType;
            connectionStatus.details = data;
            
            // 更新UI
            updateButtonStates();
            showNotification(data.message, 'success');
        } else {
            showNotification('连接失败: ' + data.message, 'error');
        }
    })
    .catch(error => {
        showNotification('连接请求出错: ' + error, 'error');
    });
}

// 断开连接
function disconnectFromSource() {
    fetch('/api/monitor/disconnect', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 更新连接状态
            connectionStatus.connected = false;
            connectionStatus.type = null;
            connectionStatus.details = {};
            
            // 如果正在监测，也停止监测
            if (monitoringStatus.active) {
                monitoringStatus.active = false;
            }
            
            // 更新UI
            updateButtonStates();
            showNotification(data.message, 'success');
        } else {
            showNotification('断开连接失败: ' + data.message, 'error');
        }
    })
    .catch(error => {
        showNotification('断开连接请求出错: ' + error, 'error');
    });
}

// 开始监测
function startMonitoring() {
    // 获取速度设置
    const speed = parseFloat(elements.speedInput.value) || 1.0;
    
    // 获取患者ID
    const patientId = elements.patientSelect.value;
    
    // 如果选择了患者，先设置患者
    let patientPromise = Promise.resolve();
    if (patientId) {
        patientPromise = fetch('/api/monitor/set-patient', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ patient_id: patientId })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                throw new Error('设置患者失败: ' + data.message);
            }
            monitoringStatus.patientId = patientId;
            return data;
        });
    }
    
    // 设置患者后开始监测
    patientPromise.then(() => {
        return fetch('/api/monitor/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ speed: speed })
        });
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 更新监测状态
            monitoringStatus.active = true;
            monitoringStatus.speed = speed;
            
            // 更新UI
            updateButtonStates();
            showNotification(data.message, 'success');
        } else {
            showNotification('开始监测失败: ' + data.message, 'error');
        }
    })
    .catch(error => {
        showNotification('开始监测请求出错: ' + error, 'error');
    });
}

// 停止监测
function stopMonitoring() {
    fetch('/api/monitor/stop', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 更新监测状态
            monitoringStatus.active = false;
            
            // 更新UI
            updateButtonStates();
            showNotification(data.message, 'success');
        } else {
            showNotification('停止监测失败: ' + data.message, 'error');
        }
    })
    .catch(error => {
        showNotification('停止监测请求出错: ' + error, 'error');
    });
}

// 显示通知
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // 添加关闭按钮
    const closeBtn = document.createElement('span');
    closeBtn.className = 'notification-close';
    closeBtn.innerHTML = '&times;';
    closeBtn.onclick = function() {
        elements.notificationArea.removeChild(notification);
    };
    notification.appendChild(closeBtn);
    
    // 添加到通知区域
    elements.notificationArea.appendChild(notification);
    
    // 自动关闭（除了错误通知）
    if (type !== 'error') {
        setTimeout(() => {
            if (notification.parentNode === elements.notificationArea) {
                elements.notificationArea.removeChild(notification);
            }
        }, 5000);
    }
}

// 设置事件监听器
function setupEventListeners() {
    // 数据源类型变更
    elements.sourceTypeSelect.addEventListener('change', updateSourceSettings);
    
    // 连接/断开按钮
    elements.connectBtn.addEventListener('click', connectToSource);
    elements.disconnectBtn.addEventListener('click', disconnectFromSource);
    
    // 开始/停止按钮
    elements.startBtn.addEventListener('click', startMonitoring);
    elements.stopBtn.addEventListener('click', stopMonitoring);
    
    // 扫描按钮
    if (elements.scanPortsBtn) {
        elements.scanPortsBtn.addEventListener('click', scanSerialPorts);
    }
    
    if (elements.scanBluetoothBtn) {
        elements.scanBluetoothBtn.addEventListener('click', scanBluetoothDevices);
    }
    
    // 文件浏览按钮
    if (elements.browseFileBtn) {
        elements.browseFileBtn.addEventListener('click', () => {
            // 这里需要实现文件浏览功能
            // 由于浏览器安全限制，可能需要使用隐藏的file input元素
            alert('文件浏览功能尚未实现');
        });
    }
}

// 设置Socket.IO事件监听器
function setupSocketListeners() {
    // 连接状态更新
    socket.on('connection_status', (data) => {
        if (data.status === 'connected') {
            connectionStatus.connected = true;
            connectionStatus.type = data.type;
            connectionStatus.details = data;
        } else if (data.status === 'disconnected') {
            connectionStatus.connected = false;
            connectionStatus.type = null;
            connectionStatus.details = {};
            
            // 如果正在监测，也停止监测
            if (monitoringStatus.active) {
                monitoringStatus.active = false;
            }
        }
        
        // 更新UI
        updateButtonStates();
    });
    
    // 监测状态更新
    socket.on('monitoring_status', (data) => {
        monitoringStatus.active = data.active;
        if (data.speed) monitoringStatus.speed = data.speed;
        if (data.patient_id) monitoringStatus.patientId = data.patient_id;
        
        // 更新UI
        updateButtonStates();
    });
    
    // 通知消息
    socket.on('notification', (data) => {
        showNotification(data.message, data.type || 'info');
    });
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initPage);
