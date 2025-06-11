import React, { useRef, useEffect, useState } from 'react';
import { Box, Button, Container, Typography, Paper } from '@mui/material';
import Chart from 'chart.js/auto';

const HomePage = () => {
  const chartRef = useRef(null);
  const [chart, setChart] = useState(null);

  useEffect(() => {
    if (chartRef.current) {
      const newChart = new Chart(chartRef.current, {
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
      setChart(newChart);
    }

    return () => {
      if (chart) {
        chart.destroy();
      }
    };
  }, [chartRef]);

  const ws = useRef(null);

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
