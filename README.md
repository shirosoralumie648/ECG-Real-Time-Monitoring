# ECG-Real-Time-Monitoring
A real-time ECG monitoring system using Python, Flask, and Socket.IO. This project includes functionalities for ECG signal processing, feature extraction, and visualization.


## Features

- Real-time ECG data acquisition and visualization
- ECG signal preprocessing and cleaning
- Feature extraction and analysis of ECG signals
- Heart rate variability (HRV) analysis
- ECG-derived respiration (EDR) analysis

## Technologies Used

- Python
- Flask
- Socket.IO
- NeuroKit2
- Plotly.js

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/vtuberfan/ECG-Real-Time-Monitoring.git
    cd ECG-Real-Time-Monitoring
    ```

2. Create a virtual environment and activate it:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. Start the web server:
    ```bash
    python backend/main.py
    ```

2. Open your web browser and navigate to `http://localhost:5000`.

3. Use the web interface to start and stop ECG monitoring, and to perform various analyses.

## File Structure

- `backend/`: Contains the backend code for the project.
  - `main.py`: Entry point for the web server.
  - `web_server.py`: Defines the Flask web server and routes.
  - `ecg_monitoring_system.py`: Manages the ECG monitoring system.
  - `ecg_data_processor.py`: Processes ECG data.
  - `ecg_signal_analyzer.py`: Analyzes ECG signals.
  - `serial_reader.py`: Reads data from the serial port.
  - `data_storage.py`: Handles data storage.
  - `templates/`: Contains HTML templates.
  - `static/`: Contains static files like JavaScript and CSS.
- `requirements.txt`: Lists the required Python packages.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the GPL-3.0 license. See the `LICENSE` file for details.
