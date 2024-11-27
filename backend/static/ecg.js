// ecg.js

// 全局变量，存储监测开始时的初始时间
var initialTime = null;

// 连接WebSocket
var socket = io({
    transports: ['websocket']
});

socket.on('connect', function() {
    console.log('WebSocket connected');
});

socket.on('ecg_data', function(data) {
    console.log('Received ecg_data:', data);
    var leads = data.leads;  // leads是一个二维数组，形状为 [12][N]
    var timeStamps = data.time_stamps;  // 时间戳数组，长度为 N
    var numPoints = timeStamps.length;  // 数据点数量

    // 在第一次接收到数据时，设置 initialTime
    if (initialTime === null) {
        initialTime = timeStamps[0];  // 记录初始时间戳
    }

    // 将时间戳转换为相对于 initialTime 的相对时间（秒）
    var relativeTimeStamps = timeStamps.map(function(ts) {
        return ts - initialTime;
    });

    // 更新每个导联的波形数据
    for (var i = 0; i < 12; i++) {
        var leadData = leads[i];  // 当前导联的数据数组
        for (var j = 0; j < numPoints; j++) {
            traces[i].x.push(relativeTimeStamps[j]);
            traces[i].y.push(leadData[j]);
        }
    }

    // 只保留最近5秒的数据
    var latestTime = relativeTimeStamps[relativeTimeStamps.length - 1];
    var maxTime = latestTime - 5;  // 显示最近5秒的数据
    for (var i = 0; i < 12; i++) {
        while (traces[i].x.length > 0 && traces[i].x[0] < maxTime) {
            traces[i].x.shift();
            traces[i].y.shift();
        }
    }

    // 更新图表范围，动态滚动
    var updatedLayout = {
        xaxis: { range: [maxTime, latestTime] }
    };

    // 更新图表
    Plotly.update('ecg_plots', traces, updatedLayout);
});

// 初始化绘图
var leadNames = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6'];
var traces = [];
for (var i = 0; i < 12; i++) {
    traces.push({
        x: [],
        y: [],
        mode: 'lines',
        name: leadNames[i]
    });
}
var layout = {
    title: '实时ECG波形',
    xaxis: { title: '时间 (s)' },
    yaxis: { title: '电压 (mV)' },
    autosize: true
};
Plotly.newPlot('ecg_plots', traces, layout);

// 控制函数
function startECG() {
    console.log('startECG() called');
    initialTime = null;  // 重置 initialTime
    fetch('/start', { method: 'POST' })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Start response:', data);
        })
        .catch(error => {
            console.error('Error in startECG:', error);
        });
}

function stopECG() {
    console.log('stopECG() called');
    fetch('/stop', { method: 'POST' })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Stop response:', data);
        })
        .catch(error => {
            console.error('Error in stopECG:', error);
        });
}

function analyzeECG(action) {
    console.log('analyzeECG() called with action:', action);
    fetch('/analyze', {
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
    fetch('/get_files')
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



    fetch('/process_ecg', {
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



    fetch('/process_hrv', {
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



    fetch('/process_edr', {
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