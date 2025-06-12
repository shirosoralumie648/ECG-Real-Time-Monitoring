import React, { useRef, useEffect, useState } from 'react';
import { Box, Button, Container, Typography, Paper, Select, MenuItem, FormControl, InputLabel, TextField, CircularProgress, Alert } from '@mui/material';
import ECGDisplay from '../components/ECGDisplay';

const HomePage = () => {
  const ws = useRef(null);
  const [dataSource, setDataSource] = useState('serial');
  const [connectionStatus, setConnectionStatus] = useState('未连接');
  const [serialPorts, setSerialPorts] = useState([]);
  const [selectedPort, setSelectedPort] = useState('');
  const [baudRate, setBaudRate] = useState(115200); // 添加波特率状态变量，默认115200
  const [udpHost, setUdpHost] = useState('127.0.0.1');
  const [udpPort, setUdpPort] = useState(5005);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isScanning, setIsScanning] = useState(false);
  const [dataFormat, setDataFormat] = useState('justfloat'); 
  const [isMonitoring, setIsMonitoring] = useState(false); 
  const [ecgData, setEcgData] = useState(null); 

  const handleConnect = async () => {
    setIsConnecting(true);
    setError(null);

    try {
      let endpoint = '/api/v1/ports/connect'; 
      let requestBody = new FormData();
      let statusMessage = '已连接';

      requestBody.append('dataFormat', dataFormat);

      // 根据数据源类型设置不同的参数
      if (dataSource === 'serial') {
        if (!selectedPort) {
          throw new Error('请选择一个串口');
        }
        requestBody.append('type', 'serial');
        requestBody.append('port', selectedPort);
        requestBody.append('baudrate', baudRate.toString()); // 添加波特率参数
        statusMessage = `已连接到串口 ${selectedPort} (波特率: ${baudRate})`;
        
        console.log(`尝试连接串口 ${selectedPort}，波特率: ${baudRate}，数据格式: ${dataFormat}`);
      } else if (dataSource === 'udp') {
        requestBody.append('type', 'udp');
        requestBody.append('host', udpHost);
        requestBody.append('port_number', udpPort); // 修改为port_number避免混淆
        statusMessage = `已连接到UDP ${udpHost}:${udpPort}`;
        
        console.log(`尝试连接UDP ${udpHost}:${udpPort}，数据格式: ${dataFormat}`);
      } else if (dataSource === 'file' && selectedFile) {
        requestBody.append('type', 'file');
        requestBody.append('file', selectedFile);
        statusMessage = `已加载文件 ${selectedFile.name}`;
        
        console.log(`尝试加载文件 ${selectedFile.name}，数据格式: ${dataFormat}`);
      } else {
        throw new Error('无效的数据源');
      }

      console.log('发送连接请求:', endpoint, '，请求内容:', {
        dataSource: dataSource,
        dataFormat: dataFormat,
        ...(dataSource === 'serial' && { port: selectedPort, baudrate: baudRate }),
        ...(dataSource === 'udp' && { host: udpHost, port_number: udpPort }),
        ...(dataSource === 'file' && { filename: selectedFile?.name })
      });
      
      // 增加请求头部信息
      const requestOptions = {
        method: 'POST',
        body: requestBody,
        // 不需要为FormData添加Content-Type，浏览器会自动设置正确的头部和边界
        headers: {
          // 添加CORS相关头部
          'Accept': 'application/json',
        },
        // 增加凡是浏览器支持的跨域函数属性
        mode: 'cors',
        credentials: 'same-origin',
      };
      
      console.log('请求选项:', requestOptions);
      
      try {
        const response = await fetch(`http://localhost:8000${endpoint}`, requestOptions);
        console.log('收到响应:', response.status, response.statusText);
        
        // 如果响应不是成功的
        if (!response.ok) {
          // 尝试解析错误响应体
          let errorMessage;
          try {
            const errorData = await response.json();
            errorMessage = errorData.detail || '连接失败';
          } catch (e) {
            // 如果无法解析JSON，使用状态文本
            errorMessage = response.statusText || `服务器错误 (状态码: ${response.status})`;
          }
          
          // 增强常见错误的错误信息
          if (errorMessage.includes('Permission denied')) {
            errorMessage += ' (权限问题，请以管理员权限运行或检查设备权限)';
          } else if (errorMessage.includes('device not found')) {
            errorMessage += ' (未找到设备，请检查连接)';
          } else if (errorMessage.includes('busy')) {
            errorMessage += ' (端口被占用，请关闭其他可能使用该端口的程序)';
          }
          
          throw new Error(errorMessage);
        }
        
        // 获取响应数据
        const responseData = await response.json();
        console.log('连接成功响应：', responseData);
        
        // 成功连接后立即更新状态
        setConnectionStatus(statusMessage || '已连接');
        setIsConnected(true);
        return responseData;
      } catch (fetchError) {
        console.error('请求出错:', fetchError);
        throw new Error(`请求错误: ${fetchError.message || '无法连接到服务器'}`);
      }
    } catch (err) {
      console.error('连接错误:', err);
      setError(err.message || '连接失败');
      setConnectionStatus('错误');
    } finally {
      setIsConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    setIsConnecting(true);
    setError(null);
    try {
      const response = await fetch('/api/v1/ports/disconnect', {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to disconnect');
      }
      const data = await response.json();
      setConnectionStatus('Disconnected');
      setIsConnected(false);
      console.log(data.message);
    } catch (error) {
      console.error(error);
      setConnectionStatus('Disconnect Failed');
      setError('Failed to disconnect. Please try again.');
    } finally {
      setIsConnecting(false);
    }
  };


  const handleScanPorts = async () => {
    setIsScanning(true);
    setError(null);
    try {
      const response = await fetch('/api/v1/ports/scan');
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Failed to fetch serial ports');
      }
      const data = await response.json();
      setSerialPorts(data.ports || []);
      if (data.ports && data.ports.length > 0) {
        setSelectedPort(data.ports[0]);
      } else {
        console.log('No serial ports found.');
        setSelectedPort(''); // Reset selection if no ports are found
      }
    } catch (error) {
      console.error('Scan error:', error);
      setError(`Scan failed: ${error.message}`);
      setSerialPorts([]); // Clear ports on error
    } finally {
      setIsScanning(false);
    }
  };

  useEffect(() => {
    // Automatically scan for serial ports when the component mounts and 'serial' is the data source
    if (dataSource === 'serial') {
      handleScanPorts();
    }
  }, [dataSource]);

  // WebSocket连接的清理函数
  useEffect(() => {
    return () => {
      if (ws.current) {
        ws.current.close();
        ws.current = null;
      }
    };
  }, []);

  const handleStartMonitoring = async () => {
    // 如果未连接到数据源，先尝试连接
    if (!isConnected) {
      console.log("数据源未连接，先进行连接");
      try {
        await handleConnect();
      } catch (error) {
        console.error("连接失败，无法启动监测:", error);
        return;
      }
    }
    
    // 如果WebSocket已经打开，则不需要重新连接
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      console.log("WebSocket已经连接");
      setIsMonitoring(true);
      return;
    }

    // 关闭之前的连接
    if (ws.current) {
      console.log("关闭现有WebSocket连接");
      ws.current.close();
    }

    // 创建新的WebSocket连接
    console.log("创建新的WebSocket连接...");
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const backendHost = 'localhost:8000'; // 后端WebSocket主机和端口
    ws.current = new WebSocket(`${protocol}//${backendHost}/api/v1/ws`);
    
    ws.current.onopen = () => {
      console.log('WebSocket已连接');
      setConnectionStatus('正在监测');
      setIsMonitoring(true);
      
      // 发送客户端标识消息
      try {
        console.log('发送客户端标识消息');
        ws.current.send(JSON.stringify({ type: 'client' }));
      } catch (err) {
        console.error('发送客户端标识消息失败:', err);
      }
    };
    
    ws.current.onmessage = (event) => {
      try {
        // 添加调试日志
        console.log('收到WebSocket消息:', event.data);
        
        const data = JSON.parse(event.data);
        console.log('解析后的数据:', data);  // 添加数据解析日志
        
        // 处理实时ECG数据
        if (data && data.leads) {
          // 单帧数据
          setEcgData(data);
        } else if (Array.isArray(data.batch)) {
          // 批量数据，直接传递给ECGDisplay，由其内部解包
          setEcgData(data);
        } else {
          console.warn('数据格式不符合ECG数据结构:', data);
        }
      } catch (error) {
        console.error("处理WebSocket消息错误:", error);
      }
    };
    
    ws.current.onclose = () => {
      console.log('WebSocket已断开');
      setConnectionStatus(isConnected ? '已连接' : '已断开连接');
      setIsMonitoring(false);
    };
    
    ws.current.onerror = (error) => {
      console.error("WebSocket错误:", error);
      setError("WebSocket连接失败");
      setIsMonitoring(false);
    };
  };

  const handleStopMonitoring = () => {
    if (ws.current) {
      ws.current.close();
      ws.current = null;
      setIsMonitoring(false);
      setConnectionStatus(isConnected ? '已连接' : '已断开连接');
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        ECG Real-Time Monitoring
      </Typography>

      {/* Data Source Configuration Panel */}
      <Paper elevation={3} sx={{ p: 2, mb: 4 }}>
        <Typography variant="h6">Data Source Configuration</Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 2, mb: 2 }}>
          <FormControl fullWidth sx={{ minWidth: 150 }}>
            <InputLabel>Source Type</InputLabel>
            <Select
              value={dataSource}
              label="Source Type"
              onChange={(e) => setDataSource(e.target.value)}
              disabled={isConnecting || isConnected}
            >
              <MenuItem value="serial">Serial</MenuItem>
              <MenuItem value="udp">UDP</MenuItem>
              <MenuItem value="bluetooth">Bluetooth</MenuItem>
              <MenuItem value="file">File Playback</MenuItem>
            </Select>
          </FormControl>
          <Button variant="contained" color="success" onClick={handleConnect} disabled={isConnecting || isConnected}>
            {isConnecting && connectionStatus === 'Connecting...' ? <CircularProgress size={24} /> : 'Connect'}
          </Button>
          <Button variant="outlined" color="error" onClick={handleDisconnect} disabled={isConnecting || !isConnected}>
            {isConnecting && connectionStatus !== 'Connecting...' ? <CircularProgress size={24} /> : 'Disconnect'}
          </Button>
        </Box>
        
        {dataSource === 'udp' && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 2, mb: 2 }}>
            <TextField
              label="Host"
              value={udpHost}
              onChange={(e) => setUdpHost(e.target.value)}
              variant="outlined"
              size="small"
              disabled={isConnecting || isConnected}
            />
            <TextField
              label="Port"
              value={udpPort}
              onChange={(e) => setUdpPort(e.target.value)}
              variant="outlined"
              size="small"
              type="number"
              disabled={isConnecting || isConnected}
            />
          </Box>
        )}

        {dataSource === 'file' && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 2, mb: 2 }}>
            <Button
              variant="contained"
              component="label"
              disabled={isConnecting || isConnected}
            >
              Choose File
              <input
                type="file"
                hidden
                onChange={(e) => setSelectedFile(e.target.files[0])}
              />
            </Button>
            {selectedFile && <Typography>{selectedFile.name}</Typography>}
          </Box>
        )}

        {dataSource === 'serial' && (
          <>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 2, mb: 2 }}>
              <FormControl fullWidth>
                <InputLabel>串口选择</InputLabel>
                <Select
                  value={selectedPort}
                  label="串口选择"
                  onChange={(e) => setSelectedPort(e.target.value)}
                  disabled={isConnecting || isConnected || !serialPorts.length}
                >
                  {serialPorts.map((port) => (
                    <MenuItem key={port} value={port}>{port}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Button onClick={handleScanPorts} disabled={isConnecting || isConnected || isScanning}>
                {isScanning ? <CircularProgress size={24} /> : '扫描'}
              </Button>
            </Box>
            
            {/* 添加波特率设置 */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 2, mb: 2 }}>
              <FormControl fullWidth>
                <InputLabel>波特率</InputLabel>
                <Select
                  value={baudRate}
                  label="波特率"
                  onChange={(e) => setBaudRate(e.target.value)}
                  disabled={isConnecting || isConnected}
                >
                  <MenuItem value={9600}>9600</MenuItem>
                  <MenuItem value={19200}>19200</MenuItem>
                  <MenuItem value={38400}>38400</MenuItem>
                  <MenuItem value={57600}>57600</MenuItem>
                  <MenuItem value={115200}>115200</MenuItem>
                  <MenuItem value={230400}>230400</MenuItem>
                  <MenuItem value={460800}>460800</MenuItem>
                  <MenuItem value={921600}>921600</MenuItem>
                </Select>
              </FormControl>
            </Box>
          </>
        )}

        {/* Data Format Selection - Common for Serial, UDP, File */}
        {(dataSource === 'serial' || dataSource === 'udp' || dataSource === 'file') && (
          <Box sx={{ mt: 2, mb: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Data Format</InputLabel>
              <Select
                value={dataFormat}
                label="Data Format"
                onChange={(e) => setDataFormat(e.target.value)}
                disabled={isConnecting || isConnected}
              >
                <MenuItem value="rawdata">Raw Data</MenuItem>
                <MenuItem value="justfloat">Just Float</MenuItem>
                <MenuItem value="firewater">Firewater</MenuItem>
              </Select>
            </FormControl>
          </Box>
        )}

        <Typography variant="body1">Status: <span style={{ fontWeight: 'bold' }}>{connectionStatus}</span></Typography>
        {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
      </Paper>

      {/* ECG显示组件 */}
      {isMonitoring ? (
        <ECGDisplay data={ecgData} />
      ) : (
        <Paper elevation={3} sx={{ p: 2, mb: 4, height: '600px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Typography variant="h5" color="text.secondary">
            请点击"开始监测"按钮查看心电图
          </Typography>
        </Paper>
      )}
      <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2 }}>
        <Button 
          variant="contained" 
          color="primary" 
          onClick={handleStartMonitoring}
          disabled={!isConnected || isMonitoring}
        >
          开始监测
        </Button>
        <Button 
          variant="contained" 
          color="secondary" 
          onClick={handleStopMonitoring}
          disabled={!isMonitoring}
        >
          停止监测
        </Button>
      </Box>
    </Container>
  );
};

export default HomePage;
