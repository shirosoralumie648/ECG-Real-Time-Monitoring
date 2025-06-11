// respiration.js - 呼吸监测系统的前端JavaScript代码

// 初始化Socket.IO连接
const socket = io();

// 全局变量
let respirationPlot = null;
let isMonitoring = false;
let respirationData = {
    time: [],
    signal: []
};

// DOM加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化呼吸信号图表
    initRespirationPlot();
    
    // 获取历史文件列表
    fetchRespirationFiles();
    
    // 监听Socket.IO事件
    setupSocketListeners();
});

// 初始化呼吸信号图表
function initRespirationPlot() {
    const plotDiv = document.getElementById('respiration_plots');
    
    const data = [{
        x: [],
        y: [],
        type: 'scatter',
        mode: 'lines',
        line: {
            color: '#17BECF',
            width: 2
        },
        name: '呼吸信号'
    }];
    
    const layout = {
        title: '实时呼吸信号监测',
        xaxis: {
            title: '时间 (秒)',
            showgrid: true,
            zeroline: false
        },
        yaxis: {
            title: '振幅',
            showline: false
        },
        margin: {
            l: 50,
            r: 50,
            b: 50,
            t: 50,
            pad: 4
        },
        autosize: true,
        plot_bgcolor: '#f8f9fa',
        paper_bgcolor: '#f8f9fa'
    };
    
    const config = {
        responsive: true,
        displayModeBar: true,
        scrollZoom: true
    };
    
    respirationPlot = Plotly.newPlot(plotDiv, data, layout, config);
}

// 获取历史文件列表
function fetchRespirationFiles() {
    fetch('/get_respiration_files')
        .then(response => response.json())
        .then(files => {
            const select = document.getElementById('respirationFiles');
            select.innerHTML = '<option selected>选择一个历史文件...</option>';
            
            files.forEach(file => {
                const option = document.createElement('option');
                option.value = file;
                option.textContent = file;
                select.appendChild(option);
            });
        })
        .catch(error => console.error('获取文件列表失败:', error));
}

// 设置Socket.IO事件监听器
function setupSocketListeners() {
    // 监听呼吸数据
    socket.on('respiration_data', function(data) {
        updateRespirationPlot(data);
    });
}

// 更新呼吸信号图表
function updateRespirationPlot(data) {
    if (!isMonitoring) return;
    
    // 添加新数据
    const plotDiv = document.getElementById('respiration_plots');
    
    // 更新数据
    const update = {
        x: [data.time],
        y: [data.signal]
    };
    
    // 保存数据以便后续分析
    respirationData.time.push(data.time);
    respirationData.signal.push(data.signal);
    
    // 限制数据点数量，防止浏览器卡顿
    if (respirationData.time.length > 500) {
        respirationData.time.shift();
        respirationData.signal.shift();
    }
    
    // 更新图表
    Plotly.extendTraces(plotDiv, update, [0]);
    
    // 自动滚动x轴
    const xrange = respirationData.time[respirationData.time.length - 1] - respirationData.time[0];
    if (xrange > 20) {
        const newRange = {
            xaxis: {
                range: [
                    respirationData.time[respirationData.time.length - 1] - 20,
                    respirationData.time[respirationData.time.length - 1]
                ]
            }
        };
        Plotly.relayout(plotDiv, newRange);
    }
}

// 开始呼吸监测
function startRespiration() {
    if (isMonitoring) return;
    
    fetch('/start_respiration', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'started') {
            isMonitoring = true;
            console.log('呼吸监测已启动');
            
            // 清空现有数据
            respirationData = {
                time: [],
                signal: []
            };
            
            // 重置图表
            const plotDiv = document.getElementById('respiration_plots');
            Plotly.deleteTraces(plotDiv, 0);
            Plotly.addTraces(plotDiv, [{
                x: [],
                y: [],
                type: 'scatter',
                mode: 'lines',
                line: {
                    color: '#17BECF',
                    width: 2
                },
                name: '呼吸信号'
            }]);
        }
    })
    .catch(error => console.error('启动呼吸监测失败:', error));
}

// 停止呼吸监测
function stopRespiration() {
    if (!isMonitoring) return;
    
    fetch('/stop_respiration', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'stopped') {
            isMonitoring = false;
            console.log('呼吸监测已停止');
            
            // 刷新文件列表
            fetchRespirationFiles();
        }
    })
    .catch(error => console.error('停止呼吸监测失败:', error));
}

// 呼吸频率分析
function respirationAnalysis() {
    const select = document.getElementById('respirationFiles');
    const fileName = select.value;
    
    if (fileName === '选择一个历史文件...') {
        alert('请先选择一个历史文件');
        return;
    }
    
    fetch('/process_respiration', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ file_name: fileName })
    })
    .then(response => response.blob())
    .then(blob => {
        const url = URL.createObjectURL(blob);
        const img = document.getElementById('respirationImage');
        img.src = url;
        img.style.display = 'block';
        
        document.getElementById('analysis_results').innerHTML = '呼吸频率分析结果';
    })
    .catch(error => console.error('呼吸分析失败:', error));
}

// 呼吸变异性分析
function respirationVariabilityAnalysis() {
    const select = document.getElementById('respirationFiles');
    const fileName = select.value;
    
    if (fileName === '选择一个历史文件...') {
        alert('请先选择一个历史文件');
        return;
    }
    
    fetch('/process_respiration_variability', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ file_name: fileName })
    })
    .then(response => response.blob())
    .then(blob => {
        const url = URL.createObjectURL(blob);
        const img = document.getElementById('respirationImage');
        img.src = url;
        img.style.display = 'block';
        
        document.getElementById('analysis_results').innerHTML = '呼吸变异性分析结果';
    })
    .catch(error => console.error('呼吸变异性分析失败:', error));
}

// 呼吸模式分析
function respirationPatternAnalysis() {
    const select = document.getElementById('respirationFiles');
    const fileName = select.value;
    
    if (fileName === '选择一个历史文件...') {
        alert('请先选择一个历史文件');
        return;
    }
    
    fetch('/process_respiration_pattern', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ file_name: fileName })
    })
    .then(response => response.blob())
    .then(blob => {
        const url = URL.createObjectURL(blob);
        const img = document.getElementById('respirationImage');
        img.src = url;
        img.style.display = 'block';
        
        document.getElementById('analysis_results').innerHTML = '呼吸模式分析结果';
    })
    .catch(error => console.error('呼吸模式分析失败:', error));
}
