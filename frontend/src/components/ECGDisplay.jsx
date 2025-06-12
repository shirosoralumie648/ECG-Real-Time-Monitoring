import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Box, Typography, Paper, Grid } from '@mui/material';
import Chart from 'chart.js/auto';

// 导联颜色配置
const LEAD_COLORS = {
  'I': 'rgb(255, 99, 132)', 'II': 'rgb(54, 162, 235)', 'III': 'rgb(255, 206, 86)',
  'aVR': 'rgb(75, 192, 192)', 'aVL': 'rgb(153, 102, 255)', 'aVF': 'rgb(255, 159, 64)',
  'V1': 'rgb(199, 199, 199)', 'V2': 'rgb(83, 225, 162)', 'V3': 'rgb(223, 83, 83)',
  'V4': 'rgb(63, 127, 191)', 'V5': 'rgb(191, 63, 191)', 'V6': 'rgb(127, 191, 63)'
};

const ALL_LEADS = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6'];
const MAX_DATA_POINTS = 500; // 滑动窗口大小

// 辅助函数：计算Y轴动态范围
const calculateYAxisRange = (dataBuffer) => {
  if (!dataBuffer || dataBuffer.length < 2) {
    return { min: -200, max: 200 }; // 数据不足时的默认范围
  }

  const yValues = dataBuffer.map(p => p.y);
  let dataMin = Math.min(...yValues);
  let dataMax = Math.max(...yValues);

  if (isNaN(dataMin) || isNaN(dataMax) || !isFinite(dataMin) || !isFinite(dataMax)) {
      return { min: -200, max: 200 }; // 处理无效数值情况
  }

  if (dataMin === dataMax) { // 平线情况
    const delta = Math.max(Math.abs(dataMin * 0.15), 50); // 15% 或至少50单位
    dataMin -= delta;
    dataMax += delta;
  } else {
    const range = dataMax - dataMin;
    const padding = range * 0.15; // 15% padding
    dataMin -= padding;
    dataMax += padding;
  }
  return { min: dataMin, max: dataMax };
};


const ECGDisplay = ({ data }) => {
  const chartCanvasRefs = useRef(ALL_LEADS.reduce((acc, lead) => {
    acc[lead] = React.createRef();
    return acc;
  }, {}));
  const chartInstances = useRef(ALL_LEADS.reduce((acc, lead) => {
    acc[lead] = null;
    return acc;
  }, {}));

  const [leadDataBuffers, setLeadDataBuffers] = useState(
    ALL_LEADS.reduce((acc, lead) => ({ ...acc, [lead]: [] }), {})
  );
  const [yAxisRanges, setYAxisRanges] = useState(
    ALL_LEADS.reduce((acc, lead) => ({ ...acc, [lead]: { min: -200, max: 200 } }), {})
  );

  // 初始化图表
  useEffect(() => {
    console.log('Initializing charts for all 12 leads...');
    ALL_LEADS.forEach(leadName => {
      if (chartCanvasRefs.current[leadName]?.current && !chartInstances.current[leadName]) {
        const initialRange = yAxisRanges[leadName];
        try {
          const chart = new Chart(chartCanvasRefs.current[leadName].current, {
            type: 'line',
            data: {
              datasets: [{
                label: leadName,
                data: [],
                borderColor: LEAD_COLORS[leadName] || 'rgb(75, 192, 192)',
                borderWidth: 1.5,
                pointRadius: 0,
                tension: 0.1, // 较小的张力以显示更清晰的ECG波形细节
                fill: false,
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              scales: {
                x: { display: false, type: 'linear', min: 0, max: MAX_DATA_POINTS - 1 },
                y: {
                  display: true,
                  min: initialRange.min,
                  max: initialRange.max,
                  ticks: { 
                    font: { size: 8 }, // 减小刻度字体
                    maxTicksLimit: 6 // 限制Y轴刻度数量
                  }
                }
              },
              plugins: { legend: { display: false }, tooltip: { enabled: false } },
              animation: false, // 禁用动画以提高性能
            }
          });
          chartInstances.current[leadName] = chart;
        } catch (error) {
          console.error(`Error creating chart for lead ${leadName}:`, error);
        }
      }
    });

    return () => { // 清理函数
      console.log('Destroying all 12 chart instances...');
      ALL_LEADS.forEach(leadName => {
        if (chartInstances.current[leadName]) {
          chartInstances.current[leadName].destroy();
          chartInstances.current[leadName] = null;
        }
      });
    };
  }, []); // 空依赖数组，仅在挂载和卸载时运行

  // 处理传入数据以更新 leadDataBuffers
  useEffect(() => {
    if (!data || !data.batch || !Array.isArray(data.batch)) return;

    setLeadDataBuffers(prevBuffers => {
      const newBuffers = ALL_LEADS.reduce((acc, lead) => {
        acc[lead] = prevBuffers[lead] ? [...prevBuffers[lead]] : [];
        return acc;
      }, {});

      data.batch.forEach(sample => {
        if (!sample || !sample.leads) return;
        Object.keys(sample.leads).forEach(leadName => {
          if (ALL_LEADS.includes(leadName) && newBuffers[leadName]) {
            const rawValue = sample.leads[leadName];
            let currentLeadBuffer = newBuffers[leadName];
            
            const newDataPoint = { x: 0, y: rawValue }; // x 稍后重新索引

            if (currentLeadBuffer.length >= MAX_DATA_POINTS) {
              currentLeadBuffer.shift(); // 移除最旧的数据点
            }
            currentLeadBuffer.push(newDataPoint);
            
            newBuffers[leadName] = currentLeadBuffer; 
          }
        });
      });
      
      // 重新索引 x 坐标
      ALL_LEADS.forEach(leadName => {
        if (newBuffers[leadName]) {
          newBuffers[leadName] = newBuffers[leadName].map((point, index) => ({
            ...point,
            x: index
          }));
        }
      });
      return newBuffers;
    });
  }, [data]);

  // 当 leadDataBuffers 更新时计算 Y 轴范围
  useEffect(() => {
    setYAxisRanges(prevRanges => {
      const newRanges = { ...prevRanges };
      let rangesChanged = false;
      ALL_LEADS.forEach(leadName => {
        if (leadDataBuffers[leadName]) {
          const calculatedRange = calculateYAxisRange(leadDataBuffers[leadName]);
          if (newRanges[leadName].min !== calculatedRange.min || newRanges[leadName].max !== calculatedRange.max) {
            newRanges[leadName] = calculatedRange;
            rangesChanged = true;
          }
        }
      });
      return rangesChanged ? newRanges : prevRanges;
    });
  }, [leadDataBuffers]);

  // 当 leadDataBuffers 或 yAxisRanges 更新时更新图表
  useEffect(() => {
    ALL_LEADS.forEach(leadName => {
      const chart = chartInstances.current[leadName];
      const buffer = leadDataBuffers[leadName];
      const range = yAxisRanges[leadName];

      if (chart && buffer && range) {
        chart.data.datasets[0].data = [...buffer]; // 使用新数据副本
        chart.options.scales.y.min = range.min;
        chart.options.scales.y.max = range.max;
        chart.update('none'); // 'none' 表示无动画更新
      }
    });
  }, [leadDataBuffers, yAxisRanges]);

  return (
    <Paper elevation={3} sx={{ p: 1, mb: 2, height: 'calc(100vh - 120px)', overflowY: 'auto' }}> {/* 调整父容器高度并允许滚动 */}
      <Grid container spacing={1}>
        {ALL_LEADS.map(leadName => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={leadName} sx={{ height: '280px' }}> {/* 为每个图表固定高度 */}
            <Paper sx={{p: 0.5, height: '100%', display: 'flex', flexDirection: 'column', border: '1px solid #eee'}}>
              <Typography variant="caption" align="center" sx={{ fontWeight: 'bold', py: 0.5 }}>
                {leadName}
              </Typography>
              <Box sx={{flexGrow: 1, position: 'relative' }}>
                 <canvas ref={chartCanvasRefs.current[leadName]}></canvas>
              </Box>
            </Paper>
          </Grid>
        ))}
      </Grid>
    </Paper>
  );
};

export default ECGDisplay;
