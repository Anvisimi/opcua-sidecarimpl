# OPC UA Server for IoT Sensor Simulation

This project implements an OPC UA (Open Platform Communications Unified Architecture) server that simulates industrial IoT sensor data. The server reads sensor measurements from a CSV file and exposes them as OPC UA variables, continuously cycling through the data to simulate real-time sensor readings.

## Features

- Reads sensor data (temperature, vibration, pressure) for multiple machines from a CSV file
- Exposes each sensor as an OPC UA variable through a standardized industrial protocol
- Updates sensor values at regular intervals to simulate real-time data
- Containerized for easy deployment using Docker
- Configurable OPC UA server endpoint

## Prerequisites

- Python 3.9+
- Docker and Docker Compose (optional, for containerized deployment)

## Installation

### Option 1: Using Python directly

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd opcua-server
   ```

2. Create and activate a virtual environment (optional but recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   # or
   .venv\Scripts\activate  # On Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Option 2: Using Docker

1. Clone the repository:
   ```bash
   git clone git@github.com:yathu25/opcua-server.git
   cd opcua-server
   ```

2. Build and run using Docker Compose:
   ```bash
   docker-compose up --build
   ```

## Usage

### Running the Server

#### With Python:
```bash
python server.py
```

#### With Docker:
```bash
docker-compose up
```

The OPC UA server will start and listen on port 4840. You should see output similar to:
```
Created variable: Machine1_Temperature
Created variable: Machine1_Vibration
...
Server started at opc.tcp://0.0.0.0:4840/freeopcua/server/
2024-XX-XX XX:XX:XX - Published row 1/XXXX
```

### Connecting to the Server

You can connect to the server using any OPC UA client. The server endpoint is:
```
opc.tcp://localhost:4840/freeopcua/server/
```

For testing purposes, you can use tools like:
- UaExpert (https://www.unified-automation.com/products/development-tools/uaexpert.html)
- Python-based clients using the asyncua library

## Data Format

The server reads data from `sensor_data.csv` with the following structure:
- First column: Timestamp in YYYY-MM-DD HH:MM:SS format
- Subsequent columns: Sensor readings for different machines following the pattern:
  - Machine[N]_Temperature
  - Machine[N]_Vibration
  - Machine[N]_Pressure
  - Where N ranges from 1 to 10

## Project Structure

- `server.py`: Main Python script implementing the OPC UA server
- `sensor_data.csv`: CSV file containing simulated sensor data
- `Dockerfile`: Configuration for building the Docker image
- `docker-compose.yml`: Configuration for running the Docker container
- `requirements.txt`: Python dependencies

## Configuration

The server is configured with these default settings:
- OPC UA endpoint: opc.tcp://0.0.0.0:4840/freeopcua/server/
- Data update interval: 1 second