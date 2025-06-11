// ecg-chart.js - ECG实时图表控制脚本

// 初始化Socket.IO连接
const chartSocket = io();

// 图表配置
let chartConfig = {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'ECG数据',
            data: [],
            borderColor: 'rgb(75, 192, 192)',
            tension: 0.1,
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        scales: {
            x: {
                type: 'linear',
                position: 'bottom',
                title: {
                    display: true,
                    text: '时间 (秒)'
                },
                ticks: {
                    maxTicksLimit: 10
                }
            },
            y: {
                title: {
                    display: true,
                    text: '振幅 (mV)'
                },
                suggestedMin: -2,
                suggestedMax: 2
            }
        },
        plugins: {
            legend: {
                display: false
            },
            tooltip: {
                enabled: false
            }
        }
    }
};

// 图表实例
let ecgChart;

// 当前选中的导联
let currentLead = 0;

// 数据缓冲区
let dataBuffer = {
    leads: Array(12).fill().map(() => []),
    timeStamps: []
};

// 最大缓冲区大小
const MAX_BUFFER_SIZE = 5000;

// 初始化图表
function initChart() {
    const ctx = document.getElementById('ecg-chart').getContext('2d');
    ecgChart = new Chart(ctx, chartConfig);
    
    // 设置导联按钮事件监听器
    setupLeadButtons();
    
    // 监听ECG数据
    chartSocket.on('ecg_data', handleEcgData);
}

// 设置导联按钮事件监听器
function setupLeadButtons() {
    const leadButtons = document.querySelectorAll('.lead-btn');
    
    leadButtons.forEach(button => {
        button.addEventListener('click', () => {
            // 移除所有按钮的active类
            leadButtons.forEach(btn => btn.classList.remove('active'));
            
            // 添加当前按钮的active类
            button.classList.add('active');
            
            // 更新当前导联
            currentLead = parseInt(button.getAttribute('data-lead'));
            
            // 更新图表
            updateChart();
        });
    });
}

// 处理接收到的ECG数据
function handleEcgData(data) {
    // 检查数据格式
    if (!data || !data.leads || !data.time_stamps) {
        console.error('接收到的ECG数据格式不正确', data);
        return;
    }
    
    // 添加数据到缓冲区
    for (let i = 0; i < data.leads.length; i++) {
        if (i < dataBuffer.leads.length) {
            dataBuffer.leads[i] = dataBuffer.leads[i].concat(data.leads[i]);
            
            // 限制缓冲区大小
            if (dataBuffer.leads[i].length > MAX_BUFFER_SIZE) {
                dataBuffer.leads[i] = dataBuffer.leads[i].slice(-MAX_BUFFER_SIZE);
            }
        }
    }
    
    // 添加时间戳
    dataBuffer.timeStamps = dataBuffer.timeStamps.concat(data.time_stamps);
    
    // 限制时间戳缓冲区大小
    if (dataBuffer.timeStamps.length > MAX_BUFFER_SIZE) {
        dataBuffer.timeStamps = dataBuffer.timeStamps.slice(-MAX_BUFFER_SIZE);
    }
    
    // 更新图表
    updateChart();
}

// 更新图表
function updateChart() {
    // 检查是否有数据
    if (!dataBuffer.leads[currentLead] || dataBuffer.leads[currentLead].length === 0) {
        return;
    }
    
    // 准备图表数据
    const chartData = [];
    const leadData = dataBuffer.leads[currentLead];
    const timeStamps = dataBuffer.timeStamps;
    
    // 确保数据和时间戳长度一致
    const dataLength = Math.min(leadData.length, timeStamps.length);
    
    // 获取基准时间（第一个时间戳）
    const baseTime = timeStamps[0];
    
    // 创建数据点
    for (let i = 0; i < dataLength; i++) {
        // 转换时间戳为相对时间（秒）
        const relativeTime = (timeStamps[i] - baseTime);
        
        chartData.push({
            x: relativeTime,
            y: leadData[i]
        });
    }
    
    // 更新图表数据
    ecgChart.data.datasets[0].data = chartData;
    
    // 更新图表标题
    const leadLabels = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6'];
    ecgChart.data.datasets[0].label = `导联 ${leadLabels[currentLead]}`;
    
    // 自动调整X轴范围，显示最近的10秒数据
    if (chartData.length > 0) {
        const lastTime = chartData[chartData.length - 1].x;
        const startTime = Math.max(0, lastTime - 10); // 显示最近10秒
        
        ecgChart.options.scales.x.min = startTime;
        ecgChart.options.scales.x.max = lastTime;
    }
    
    // 更新图表
    ecgChart.update();
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initChart);
