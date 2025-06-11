import React, { useRef, useEffect, useState } from 'react';
import { Box, Button, Container, Typography, Paper, Select, MenuItem, FormControl, InputLabel, TextField, CircularProgress, Alert } from '@mui/material';
import Chart from 'chart.js/auto';

const HomePage = () => {
  const chartRef = useRef(null);
  const chartInstance = useRef(null); // Use a ref for the chart instance
  const ws = useRef(null);
  const [dataSource, setDataSource] = useState('serial');
  const [connectionStatus, setConnectionStatus] = useState('Disconnected');
  const [serialPorts, setSerialPorts] = useState([]);
  const [selectedPort, setSelectedPort] = useState('');
  const [udpHost, setUdpHost] = useState('127.0.0.1');
  const [udpPort, setUdpPort] = useState(5005);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isScanning, setIsScanning] = useState(false);

  const handleConnect = async () => {
    setIsConnecting(true);
    setConnectionStatus('Connecting...');
    setError(null);

    try {
      let fetchOptions = {
        method: 'POST',
      };
      let statusMessage = 'Connected';

      if (dataSource === 'file') {
        if (!selectedFile) {
          throw new Error('No file selected');
        }
        const formData = new FormData();
        formData.append('file', selectedFile);
        fetchOptions.body = formData;
        statusMessage = `Playing back from ${selectedFile.name}`;
      } else { // serial or udp
        const formData = new FormData();
        formData.append('type', dataSource);
        if (dataSource === 'serial') {
          if (!selectedPort) throw new Error('No serial port selected');
          formData.append('port', selectedPort);
          statusMessage = `Connected to ${selectedPort}`;
        } else if (dataSource === 'udp') {
          formData.append('host', udpHost);
          formData.append('port', udpPort);
          statusMessage = `Connected to UDP ${udpHost}:${udpPort}`;
        }
        fetchOptions.body = formData;
        // For FormData, browser sets Content-Type automatically
      }

      const response = await fetch('/api/v1/ports/connect', fetchOptions);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to connect (non-JSON response)' }));
        let errorMessage = 'Failed to connect';
        if (errorData && errorData.detail) {
          if (typeof errorData.detail === 'string') {
            errorMessage = errorData.detail;
          } else if (Array.isArray(errorData.detail)) {
            // FastAPI validation errors
            errorMessage = errorData.detail.map(err => `${err.loc.join(' -> ')}: ${err.msg}`).join(', ');
          } else if (typeof errorData.detail === 'object') {
            errorMessage = JSON.stringify(errorData.detail);
          } else {
            errorMessage = String(errorData.detail);
          }
        } else if (response.statusText) {
            errorMessage = response.statusText;
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      setConnectionStatus(statusMessage);
      setIsConnected(true);
      console.log(data.message);
    } catch (error) {
      console.error('Connection error details:', error); // Log the full error object
      setConnectionStatus(`Connection Failed`);
      setError(error.message || 'An unknown error occurred during connection.');
      setIsConnected(false);
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
    if (dataSource === 'serial') {
      handleScanPorts();
      fetchSerialPorts();
    }
  }, [dataSource]);

  useEffect(() => {
    if (chartRef.current) {
      chartInstance.current = new Chart(chartRef.current, {
        type: 'line',
        data: {
          labels: [], // Timestamps
          datasets: [
            {
              label: 'ECG Signal',
              data: [], // Signal values
              borderColor: 'rgb(75, 192, 192)',
              tension: 0.1,
              pointRadius: 0,
            },
          ],
        },
        options: {
          scales: {
            x: {
              title: {
                display: true,
                text: 'Time',
              },
            },
            y: {
              title: {
                display: true,
                text: 'Amplitude',
              },
            },
          },
          animation: {
            duration: 0, // No animation for real-time data
          },
        },
      });
    }

    // Cleanup function to destroy the chart on component unmount
    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy();
        chartInstance.current = null;
      }
    };
  }, []); // Empty dependency array ensures this runs only once on mount/unmount

  const handleStartMonitoring = () => {
    if (ws.current) {
      ws.current.close();
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    ws.current = new WebSocket(`${protocol}//${host}/ws`);

    ws.current.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.current.onmessage = (event) => {
      const chart = chartInstance.current; // Get chart from ref
      if (chart) {
        const dataPoint = JSON.parse(event.data);
        const { timestamp, value } = dataPoint;

        chart.data.labels.push(new Date(timestamp * 1000).toLocaleTimeString());
        chart.data.datasets[0].data.push(value);

        // Limit the number of data points to display
        const maxDataPoints = 100;
        if (chart.data.labels.length > maxDataPoints) {
          chart.data.labels.shift();
          chart.data.datasets[0].data.shift();
        }

        chart.update();
      }
    };

    ws.current.onclose = () => {
      console.log('WebSocket disconnected');
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  };

  const handleStopMonitoring = () => {
    if (ws.current) {
      ws.current.close();
      ws.current = null;
      console.log('WebSocket connection closed');
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
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 2, mb: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Serial Port</InputLabel>
              <Select
                value={selectedPort}
                label="Serial Port"
                onChange={(e) => setSelectedPort(e.target.value)}
                disabled={isConnecting || isConnected || !serialPorts.length}
              >
                {serialPorts.map((port) => (
                  <MenuItem key={port} value={port}>{port}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button onClick={handleScanPorts} disabled={isConnecting || isConnected || isScanning}>
              {isScanning ? <CircularProgress size={24} /> : 'Scan'}
            </Button>
          </Box>
        )}

        <Typography variant="body1">Status: <span style={{ fontWeight: 'bold' }}>{connectionStatus}</span></Typography>
        {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
      </Paper>

      <Paper elevation={3} sx={{ p: 2, mb: 4 }}>
        <canvas ref={chartRef} />
      </Paper>
      <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2 }}>
        <Button variant="contained" color="primary" onClick={handleStartMonitoring}>
          Start Monitoring
        </Button>
        <Button variant="contained" color="secondary" onClick={handleStopMonitoring}>
          Stop Monitoring
        </Button>
      </Box>
    </Container>
  );
};

export default HomePage;
